"""Find SenAI branding in a PDF and strip it out.

SenAI PDFs are rendered by headless Chrome. The branding is ordinary text: a
"SenAI Maths" title on the first page and a "senai.uk" footer on every page.
Each text object (BT ... ET) on a page is decoded to Unicode through its
font's ToUnicode map, matched against the branding patterns, and the
text-showing operators that draw the match are removed. Everything else in
the content stream (answers, diagrams, page numbers) is left untouched.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence, Union

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    NumberObject,
)

PathLike = Union[str, Path]

# Matched case-insensitively against decoded text, so it doesn't matter how
# the generator splits glyphs or which fonts it embeds. The domain comes first
# so "senai.uk" is taken whole rather than as "senai" + ".uk", and known
# endings are tried first so it isn't run on into text that follows it.
DEFAULT_PATTERNS: tuple[str, ...] = (
    r"(?:https?://)?(?:www\.)?senai\.(?:co\.uk|uk|com|ai|app|io|[a-z]{2,})(?:/\S*)?",
    r"\bsen\s?ai\b(?:\s+maths?)?",
)

SHOW_OPS = {b"Tj", b"TJ", b"'", b'"'}
# Operators that set the text position absolutely (relative to the line
# start), so glyphs after them don't depend on the width of earlier glyphs.
POSITION_OPS = {b"Td", b"TD", b"Tm", b"T*"}


@dataclass
class CleanResult:
    source: Path
    output: Optional[Path]
    pages: int = 0
    # (page number, text) for every piece of branding removed.
    removed: list[tuple[int, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.removed)


def compile_patterns(patterns: Iterable[str]) -> re.Pattern[str]:
    patterns = list(patterns)
    if not patterns:
        raise ValueError("at least one pattern is required")
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)


def clean_pdf(
    source: PathLike,
    output: PathLike,
    patterns: Sequence[str] = DEFAULT_PATTERNS,
) -> CleanResult:
    """Write a copy of ``source`` to ``output`` with the branding removed.

    ``output`` may be the same path as ``source``; the input is read fully
    into memory before anything is written.
    """
    source, output = Path(source), Path(output)
    regex = compile_patterns(patterns)
    reader = PdfReader(io.BytesIO(source.read_bytes()))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError(f"{source.name} is password protected")

    writer = PdfWriter(clone_from=reader)
    result = CleanResult(source=source, output=output, pages=len(writer.pages))
    decoders: dict[object, _FontDecoder] = {}

    for number, page in enumerate(writer.pages, start=1):
        content = page.get_contents()
        if content is not None:
            fonts = _page_fonts(page)
            ops, removed, warnings = _strip_operations(content.operations, fonts, decoders, regex)
            result.removed += [(number, text) for text in removed]
            result.warnings += [f"page {number}: {w}" for w in warnings]
            if removed:
                content.operations = ops
                page.replace_contents(content)
                page.compress_content_streams()
        result.removed += [(number, text) for text in _strip_links(page, regex)]

    result.removed += [(0, text) for text in _strip_metadata(writer, regex)]
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as fh:
        writer.write(fh)
    return result


def default_output_path(
    source: PathLike, output_dir: Optional[PathLike] = None, suffix: Optional[str] = None
) -> Path:
    """Where the cleaned copy of ``source`` goes.

    Next to the original as ``name_clean.pdf`` by default, or under the same
    name inside ``output_dir`` when one is given.
    """
    source = Path(source)
    if suffix is None:
        suffix = "" if output_dir else "_clean"
    folder = Path(output_dir) if output_dir else source.parent
    return folder / f"{source.stem}{suffix}{source.suffix or '.pdf'}"


def _page_fonts(page: DictionaryObject) -> DictionaryObject:
    # /Resources may be inherited from an ancestor /Pages node.
    node = page
    while node is not None:
        if "/Resources" in node:
            resources = node["/Resources"].get_object()
            return resources.get("/Font", DictionaryObject()).get_object()
        parent = node.get("/Parent")
        node = parent.get_object() if parent is not None else None
    return DictionaryObject()


def _strip_operations(ops, fonts, decoders, regex):
    """Return (new_ops, removed_texts, warnings) for one content stream."""
    # Pass 1: decode every text object and decide which show-ops to drop.
    drop: set[int] = set()
    removed: list[str] = []
    warnings: list[str] = []
    stack: list[tuple[object, int]] = []
    font, render_mode = None, 0
    render_modes: dict[int, int] = {}  # op index -> Tr in effect at that op
    # (op index or None for a line break, decoded text) for the open BT ... ET.
    block: Optional[list[tuple[Optional[int], str]]] = None

    for i, (operands, op) in enumerate(ops):
        if op == b"q":
            stack.append((font, render_mode))
        elif op == b"Q":
            if stack:
                font, render_mode = stack.pop()
        elif op == b"Tf" and operands:
            font = _decoder_for(fonts, operands[0], decoders)
        elif op == b"Tr" and operands:
            render_mode = int(operands[0])
        elif op == b"BT":
            block = []
        elif block is not None and _starts_new_line(op, operands):
            # Keep separate lines apart so a pattern can't run across them.
            block.append((None, "\n"))
            if op in SHOW_OPS:
                block.append((i, _shown_text(operands, op, font)))
                render_modes[i] = render_mode
        elif op in SHOW_OPS and block is not None:
            block.append((i, _shown_text(operands, op, font)))
            render_modes[i] = render_mode
        elif op == b"ET" and block is not None:
            hit, texts, problems = _match_block(block, regex)
            drop |= hit
            removed += texts
            warnings += problems
            block = None

    if not drop:
        return ops, removed, warnings

    # Pass 2: rebuild. A dropped op whose glyph advance a later kept op on
    # the same line relies on is hidden (render mode 3) instead, so the kept
    # text doesn't shift left.
    hide = _shift_sensitive(ops, drop)
    new_ops = []
    for i, (operands, op) in enumerate(ops):
        if i not in drop:
            new_ops.append((operands, op))
        elif i in hide:
            new_ops += [([NumberObject(3)], b"Tr"), (operands, op),
                        ([NumberObject(render_modes[i])], b"Tr")]
        elif op == b"'":
            new_ops.append(([], b"T*"))
        elif op == b'"':
            new_ops += [([operands[0]], b"Tw"), ([operands[1]], b"Tc"), ([], b"T*")]
        # Tj / TJ: dropped outright.
    if hide:
        warnings.append(
            f"{len(hide)} branding glyph run(s) were hidden rather than deleted "
            "because other text on the same line depends on their position"
        )
    return new_ops, removed, warnings


def _match_block(block, regex):
    """Match the branding regex against one decoded text object."""
    text, spans = "", []
    for index, piece in block:
        spans.append((index, len(text), len(text) + len(piece)))
        text += piece

    spans = [(i, a, b) for i, a, b in spans if i is not None and a < b]
    hit, texts, problems = set(), [], []
    for m in regex.finditer(text):
        if not m.group().strip():
            continue
        inside = [i for i, a, b in spans if m.start() <= a and b <= m.end()]
        partial = [i for i, a, b in spans if a < m.end() and b > m.start() and i not in inside]
        if partial:
            problems.append(f"could not cleanly remove {m.group()!r} (it shares a text run with other text)")
            continue
        hit.update(inside)
        texts.append(m.group())
    return hit, texts, problems


def _starts_new_line(op, operands) -> bool:
    if op in (b"T*", b"Tm", b"'", b'"'):
        return True
    return op in (b"Td", b"TD") and len(operands) > 1 and float(operands[1]) != 0


def _shift_sensitive(ops, drop):
    """Dropped show-ops that a later kept show-op positions itself after."""
    hide: set[int] = set()
    depends = False  # does a kept glyph run further on rely on the current position?
    for i in range(len(ops) - 1, -1, -1):
        op = ops[i][1]
        if op in (b"BT", b"ET") or op in POSITION_OPS:
            depends = False
        elif op in SHOW_OPS:
            if i in drop:
                if depends:
                    hide.add(i)
                if op in (b"'", b'"'):
                    depends = False
            else:
                # ' and " move to the next line before showing anything.
                depends = op in (b"Tj", b"TJ")
    return hide


def _shown_text(operands, op, decoder):
    if op == b"TJ":
        parts = operands[0] if operands else []
        strings = [p for p in parts if isinstance(p, (str, bytes))]
    else:
        strings = operands[-1:]
    return "".join(_decode(s, decoder) for s in strings)


def _decode(string, decoder) -> str:
    data = getattr(string, "original_bytes", None) or str(string).encode("latin-1", "replace")
    if decoder is None:
        return data.decode("latin-1")
    return decoder.decode(data)


def _decoder_for(fonts, name, cache):
    ref = fonts.raw_get(name) if name in fonts else None
    if ref is None:
        return None
    key = (ref.idnum, ref.generation) if isinstance(ref, IndirectObject) else id(ref)
    if key not in cache:
        cache[key] = _FontDecoder(ref.get_object())
    return cache[key]


class _FontDecoder:
    """Maps the bytes of a PDF string to Unicode via the font's ToUnicode CMap."""

    def __init__(self, font: DictionaryObject):
        self.map: dict[int, str] = {}
        # (byte length, low, high) code ranges from the CMap's codespace.
        self.codespace: list[tuple[int, int, int]] = []
        to_unicode = font.get("/ToUnicode")
        if to_unicode is not None:
            try:
                self._parse_cmap(to_unicode.get_object().get_data().decode("latin-1"))
            except Exception:
                self.map.clear()
        if not self.codespace:
            width = 2 if font.get("/Subtype") == "/Type0" else 1
            self.codespace = [(width, 0, 256**width - 1)]

    def decode(self, data: bytes) -> str:
        out, i = [], 0
        while i < len(data):
            width = self._code_width(data, i)
            code = int.from_bytes(data[i:i + width], "big")
            out.append(self.map.get(code, chr(code) if width == 1 and not self.map else "�"))
            i += width
        return "".join(out)

    def _code_width(self, data: bytes, i: int) -> int:
        for width, low, high in self.codespace:
            if i + width <= len(data) and low <= int.from_bytes(data[i:i + width], "big") <= high:
                return width
        return self.codespace[0][0]

    def _parse_cmap(self, cmap: str) -> None:
        for section in _sections(cmap, "codespacerange"):
            hexes = re.findall(r"<([0-9A-Fa-f\s]*)>", section)
            for low, high in zip(hexes[::2], hexes[1::2]):
                low, high = _hex(low), _hex(high)
                self.codespace.append((len(low), int.from_bytes(low, "big"), int.from_bytes(high, "big")))
        self.codespace.sort()

        for section in _sections(cmap, "bfchar"):
            hexes = re.findall(r"<([0-9A-Fa-f\s]*)>", section)
            for src, dst in zip(hexes[::2], hexes[1::2]):
                self.map[int.from_bytes(_hex(src), "big")] = _utf16(_hex(dst))

        for section in _sections(cmap, "bfrange"):
            tokens = re.findall(r"<([0-9A-Fa-f\s]*)>|(\[)|(\])", section)
            i = 0
            while i + 2 < len(tokens):
                low = int.from_bytes(_hex(tokens[i][0]), "big")
                high = int.from_bytes(_hex(tokens[i + 1][0]), "big")
                if tokens[i + 2][1]:  # <low> <high> [<dst> <dst> ...]
                    j = i + 3
                    while j < len(tokens) and not tokens[j][2]:
                        self.map[low + (j - i - 3)] = _utf16(_hex(tokens[j][0]))
                        j += 1
                    i = j + 1
                else:  # <low> <high> <dst>: dst's last byte increments
                    dst = _hex(tokens[i + 2][0])
                    start = int.from_bytes(dst, "big")
                    size = len(dst) or 2
                    for offset in range(min(high - low, 0xFFFF) + 1):
                        value = (start + offset) % 256**size
                        self.map[low + offset] = _utf16(value.to_bytes(size, "big"))
                    i += 3


def _sections(cmap: str, name: str) -> list[str]:
    return re.findall(rf"begin{name}(.*?)end{name}", cmap, re.DOTALL)


def _hex(text: str) -> bytes:
    text = re.sub(r"\s", "", text)
    return bytes.fromhex(text + "0" * (len(text) % 2))


def _utf16(data: bytes) -> str:
    return data.decode("utf-16-be", errors="replace")


def _strip_links(page: DictionaryObject, regex) -> list[str]:
    annots = page.get("/Annots")
    if annots is None:
        return []
    kept, removed = ArrayObject(), []
    for ref in annots.get_object():
        annot = ref.get_object()
        action = annot.get("/A")
        uri = str(action.get_object().get("/URI", "")) if action is not None else ""
        if annot.get("/Subtype") == "/Link" and uri and regex.search(uri):
            removed.append(uri)
        else:
            kept.append(ref)
    if removed:
        page[NameObject("/Annots")] = kept
    return removed


def _strip_metadata(writer: PdfWriter, regex) -> list[str]:
    removed = []
    info = writer.metadata
    if info is not None:
        kept = {k: v for k, v in info.items() if not (isinstance(v, str) and regex.search(v))}
        if len(kept) != len(info):
            removed += [f"{k}: {v}" for k, v in info.items() if k not in kept]
            writer.metadata = kept
    root = writer.root_object
    metadata = root.get("/Metadata")
    if metadata is not None:
        xmp = metadata.get_object().get_data().decode("utf-8", errors="ignore")
        if regex.search(xmp):
            removed.append("XMP metadata")
            del root["/Metadata"]
    return removed
