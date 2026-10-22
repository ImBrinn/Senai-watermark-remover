"""Find SenAI branding in a PDF and strip it out.

SenAI PDFs are rendered by headless Chrome. The branding is ordinary text: a
"SenAI Maths" title on the first page and a "senai.uk" footer on every page.
Each text object (BT ... ET) on a page is decoded to Unicode through its
font's ToUnicode map, matched against the branding patterns, and the
text-showing operators that draw the match are removed. Everything else in
the content stream (answers, diagrams, page numbers) is left untouched.

The title is replaced rather than just removed: the new one ("Brinns
autocompleter" unless told otherwise) is drawn where the old one was, at the
same size and weight. Then repair.py fixes SenAI's typesetting faults.
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

from .pdftext import Glyph, Run, _FontDecoder, draw, encode, glyphs, page_fonts, standard_font
from .repair import repair_page

__all__ = ["_FontDecoder"]  # re-exported for the tests

PathLike = Union[str, Path]

DEFAULT_TITLE = "Brinns autocompleter"
# The title on page 1, which gets replaced; other branding is just removed.
TITLE_PATTERN = re.compile(r"\bsen\s?ai\s+maths?\b", re.IGNORECASE)
TITLE_MARK = NameObject("/BrinnsTitle")  # a no-op marker for where the title goes

# Cleaned copies are called this, with {name} standing for the original name.
DEFAULT_NAME = "{name}-clean"
# Characters Windows doesn't allow in file names.
BAD_NAME_CHARS = set('\\/:*?"<>|')

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
    # (page number, what) for each typesetting fault fixed: a symbol such as
    # "°" drawn in place of an empty box, or "spaces" for a sentence respaced.
    repaired: list[tuple[int, str]] = field(default_factory=list)
    # The title drawn in place of SenAI's, or None if there wasn't one.
    title: Optional[str] = None
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
    title: Optional[str] = DEFAULT_TITLE,
    repair: bool = True,
) -> CleanResult:
    """Write a copy of ``source`` to ``output`` with the branding removed.

    SenAI's title is replaced by ``title`` (pass None or "" to leave it off),
    and with ``repair`` its typesetting faults are fixed too. ``output`` may
    be the same path as ``source``; the input is read fully into memory
    before anything is written.
    """
    source, output = Path(source), Path(output)
    regex = compile_patterns(patterns)
    reader = PdfReader(io.BytesIO(source.read_bytes()))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError(f"{source.name} is password protected")

    writer = PdfWriter(clone_from=reader)
    result = CleanResult(source=source, output=output, pages=len(writer.pages))
    decoders: dict[object, _FontDecoder] = {}
    fonts_seen: dict = {}
    standard: dict = {}
    library: Optional[list] = None

    for number, page in enumerate(writer.pages, start=1):
        content = page.get_contents()
        if content is not None:
            fonts = _page_fonts(page)
            names = _FontNames(page, writer, standard)
            ops = list(content.operations)
            new_title = _title_run(ops, fonts, fonts_seen, title) if number == 1 and title else None
            if new_title is not None:
                # Mark where the old title was, so the new one takes its place.
                ops.insert(new_title[1].end + 1, ([TITLE_MARK], b"MP"))
            ops, removed, warnings = _strip_operations(ops, fonts, decoders, regex)
            result.removed += [(number, text) for text in removed]
            result.warnings += [f"page {number}: {w}" for w in warnings]
            # Only put a title in if the old one really came out.
            replaced = new_title is not None and any(TITLE_PATTERN.search(t) for t in removed)
            if replaced:
                result.title = title
            ops = _place_title(ops, new_title if replaced else None, names)
            fixes: list[str] = []
            if repair:
                if library is None:
                    library = _font_library(writer, fonts_seen)
                ops, fixes = repair_page(ops, fonts, fonts_seen, library, names.add, names.name)
                result.repaired += [(number, fix) for fix in fixes]
            if removed or fixes:
                content.operations = ops
                page.replace_contents(content)
                page.compress_content_streams()
        result.removed += [(number, text) for text in _strip_links(page, regex)]

    result.removed += [(0, text) for text in _strip_metadata(writer, regex)]
    _set_title(writer, source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as fh:
        writer.write(fh)
    return result


def output_name(source: PathLike, template: str = DEFAULT_NAME) -> str:
    """The cleaned copy's file name: ``template`` with {name} replaced, plus ".pdf"."""
    source = Path(source)
    return template.replace("{name}", source.stem).strip() + (source.suffix or ".pdf")


def name_problem(template: str) -> Optional[str]:
    """Why ``template`` can't be used to name cleaned copies, in plain words, or None."""
    if not template.strip():
        return "Type a name for the cleaned copies, using {name} for the original name."
    if "{name}" not in template:
        return "Put {name} where the original file name should go."
    bad = sorted({c for c in template if c in BAD_NAME_CHARS})
    if bad:
        return "File names can't contain " + " ".join(bad)
    if any(ord(c) < 32 for c in template):
        return "File names can't contain control characters."
    if template.strip().endswith("."):
        return "File names can't end with a full stop."
    if len(template) > 120:
        return "That name is too long."
    return None


def is_output_name(stem: str, template: str = DEFAULT_NAME) -> bool:
    """Whether a file called ``stem`` looks like an earlier cleaned copy."""
    if stem.endswith("_clean"):  # what versions before 2.1.1 called them
        return True
    template = template.strip()
    if template == "{name}":
        return False
    if "{name}" not in template:
        return stem == template
    before, _, after = template.partition("{name}")
    return re.fullmatch(re.escape(before) + ".+" + re.escape(after), stem) is not None


def default_output_path(
    source: PathLike, output_dir: Optional[PathLike] = None, suffix: Optional[str] = None,
    template: Optional[str] = None,
) -> Path:
    """Where the cleaned copy of ``source`` goes.

    Next to the original as ``name-clean.pdf`` by default, or under the same
    name inside ``output_dir`` when one is given. ``suffix`` (added after the
    name) or ``template`` ({name} for the original name) changes the name.
    """
    source = Path(source)
    if template is None:
        if suffix is None:
            template = "{name}" if output_dir else DEFAULT_NAME
        else:
            template = "{name}" + suffix
    folder = Path(output_dir) if output_dir else source.parent
    return folder / output_name(source, template)


def _title_run(ops, fonts, cache, title: str) -> Optional[tuple[Run, Glyph]]:
    """The new title, drawn where SenAI's title starts, in the same size and
    style, and the old title's first glyph."""
    found = [g for g in glyphs(ops, fonts, cache) if g.visible and g.upright]
    text, owners = "", []
    for i, g in enumerate(found):
        if i and (abs(g.y - found[i - 1].y) > 0.5 * g.size or g.x < found[i - 1].x):
            text += "\n"
            owners.append(None)
        text += g.text
        owners += [g] * len(g.text)
    match = TITLE_PATTERN.search(text)
    if match is None:
        return None
    first = owners[match.start()]
    serif = any(w in first.font.name.lower() for w in ("serif", "times", "roman")) \
        and "sans" not in first.font.name.lower()
    face = ("Times" if serif else "Helvetica") + ("-Bold" if first.font.bold else "")
    face = {"Times": "Times-Roman"}.get(face, face)
    data = encode(face, title)
    if data is None or first.end < 0:
        return None
    return Run(face, first.size, first.x, first.y, data, first.fill), first


def _place_title(ops, new_title: Optional[tuple[Run, Glyph]], names: "_FontNames") -> list:
    """``ops`` with the title mark replaced by the new title, or just taken out."""
    out = []
    for operands, op in ops:
        if op == b"MP" and operands and operands[0] == TITLE_MARK:
            if new_title is not None:
                run, old = new_title
                out += draw([run], old.ctm, names.name)
        else:
            out.append((operands, op))
    return out


class _FontNames:
    """Resource names for the fonts new text is drawn in, added to the page as needed."""

    def __init__(self, page, writer: PdfWriter, standard: dict):
        self.page, self.writer, self.standard = page, writer, standard

    def name(self, font: str) -> str:
        """A page font's name as it is; a standard font ("Times-Roman") gets added."""
        if font.startswith("/"):
            return font
        return self.add(standard_font(self.writer, self.standard, font))

    def add(self, ref: IndirectObject) -> str:
        return _add_font(self.page, ref)


def _font_library(writer: PdfWriter, cache: dict) -> list:
    """(reference, Font) for every font used anywhere in the document, once each."""
    seen, out = set(), []
    for page in writer.pages:
        fonts = _page_fonts(page)
        for name in fonts:
            ref = fonts.raw_get(name)
            if not isinstance(ref, IndirectObject) or ref.idnum in seen:
                continue
            seen.add(ref.idnum)
            font = page_fonts(DictionaryObject({NameObject(name): ref}), cache).get(str(name))
            if font is not None:
                out.append((ref, font))
    return out


def _add_font(page, ref: IndirectObject) -> str:
    """The page's resource name for the font ``ref``, adding it if need be."""
    fonts = _writable_fonts(page)
    for name, value in fonts.items():
        if isinstance(value, IndirectObject) and value.idnum == ref.idnum:
            return str(name)
    n = 1
    while f"/SR{n}" in fonts:
        n += 1
    fonts[NameObject(f"/SR{n}")] = ref
    return f"/SR{n}"


def _writable_fonts(page) -> DictionaryObject:
    """The page's own /Font resource dictionary, created if need be."""
    if "/Resources" not in page:
        inherited = _page_resources(page)
        page[NameObject("/Resources")] = DictionaryObject(inherited) if inherited else DictionaryObject()
    resources = page["/Resources"].get_object()
    if "/Font" not in resources:
        resources[NameObject("/Font")] = DictionaryObject()
    return resources["/Font"].get_object()


def _page_resources(page) -> Optional[DictionaryObject]:
    # /Resources may be inherited from an ancestor /Pages node.
    node = page
    while node is not None:
        if "/Resources" in node:
            return node["/Resources"].get_object()
        parent = node.get("/Parent")
        node = parent.get_object() if parent is not None else None
    return None


def _set_title(writer: PdfWriter, source: Path) -> None:
    """Give the document a proper title: SenAI's is "about:blank"."""
    info = writer.metadata or {}
    current = str(info.get("/Title", "") or "").strip()
    if not current or current.lower() in ("about:blank", "untitled") or "://" in current:
        writer.add_metadata({"/Title": source.stem})


def _page_fonts(page: DictionaryObject) -> DictionaryObject:
    resources = _page_resources(page)
    if resources is None:
        return DictionaryObject()
    return resources.get("/Font", DictionaryObject()).get_object()


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
