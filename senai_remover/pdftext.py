"""Find every glyph on a PDF page, take glyphs out, and draw new text.

``glyphs()`` follows a content stream the way a PDF viewer would. It tracks
the graphics state and the text state, and gives each glyph's character,
font, size, position and colour. ``remove_glyphs()`` rewrites text-showing
operators so chosen glyphs are no longer drawn but the pen still moves past
them, so nothing else on the line shifts, and can put new operators in at
the same time. ``draw()`` makes the operators for replacement text, placed
in page coordinates wherever in the stream they go, so a replacement sits
in the page's reading order where the text it replaces was.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from pypdf.generic import (
    ArrayObject,
    ByteStringObject,
    DictionaryObject,
    FloatObject,
    IndirectObject,
    NameObject,
    NumberObject,
)

from ._metrics import SYMBOL, WIDTHS

SHOW_OPS = {b"Tj", b"TJ", b"'", b'"'}

Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def multiply(m: Matrix, n: Matrix) -> Matrix:
    """``m`` followed by ``n`` (PDF matrices act on row vectors)."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


@dataclass(eq=False)  # compared and hashed by identity
class Glyph:
    op: int                 # index of the text-showing operator in the content stream
    index: int              # which glyph of that operator this is
    raw: bytes              # the glyph's code, as it appears in the string
    code: int
    text: str               # Unicode, from the font's ToUnicode map
    font: "Font"
    resource: str           # the font's name in the page's resources, e.g. "/F10"
    matrix: Matrix          # glyph space (at font size 1) to page space
    width: float            # advance, in page units
    adjust: float           # TJ number that moves the pen as far as this glyph does
    fill: tuple[float, float, float]
    visible: bool
    actual: Optional[str]   # /ActualText of the marked content around it
    alone: bool             # the operator shows only this glyph
    ctm: Matrix = IDENTITY  # the graphics state's transform where it's drawn
    end: int = -1           # index of the ET that closes its text object

    @property
    def x(self) -> float:
        return self.matrix[4]

    @property
    def y(self) -> float:
        return self.matrix[5]

    @property
    def size(self) -> float:
        return math.hypot(self.matrix[2], self.matrix[3])

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def upright(self) -> bool:
        a, b, c, d = self.matrix[:4]
        return a > 0 and d > 0 and abs(b) < 1e-6 * a and abs(c) < 1e-6 * d

    @property
    def missing(self) -> bool:
        """The font has no glyph for this character, so it shows as an empty box."""
        return self.font.is_missing(self.code)


class Font:
    """What we need to know about one font resource."""

    def __init__(self, font: DictionaryObject):
        self.decoder = _FontDecoder(font)
        subtype = font.get("/Subtype")
        self.composite = subtype == "/Type0"
        name = str(font.get("/BaseFont", "")).lstrip("/")
        self.name = name.split("+", 1)[-1] if re.match(r"[A-Z]{6}\+", name) else name
        lowered = self.name.lower()

        descendant = font["/DescendantFonts"][0].get_object() if self.composite else None
        holder = descendant if descendant is not None else font
        descriptor = holder.get("/FontDescriptor")
        descriptor = descriptor.get_object() if descriptor is not None else DictionaryObject()
        flags = int(descriptor.get("/Flags", 0))
        self.italic = (any(w in lowered for w in ("italic", "oblique"))
                       or bool(flags & 64) or float(descriptor.get("/ItalicAngle", 0)) != 0)
        self.bold = any(w in lowered for w in ("bold", "black", "heavy", "semibold"))
        self.family = self.name.split("-")[0].split(",")[0]
        self._codes: Optional[dict[str, bytes]] = None

        self._widths: dict[int, float] = {}
        self._missing: set[int] = set()
        if descendant is not None:
            self._default = float(descendant.get("/DW", 1000)) / 1000
            self._read_cid_widths(descendant.get("/W", ArrayObject()))
            # With Identity encoding, codes are CIDs, and with an identity (or
            # absent) CIDToGIDMap, CIDs are glyph ids. Glyph 0 is ".notdef",
            # the empty box a font shows for a character it doesn't have.
            identity = str(font.get("/Encoding", "")) in ("/Identity-H", "/Identity-V")
            mapping = descendant.get("/CIDToGIDMap")
            if identity and (mapping is None or str(mapping) == "/Identity"):
                self._missing = {0}
        else:
            scale = 0.001
            if subtype == "/Type3":
                scale = float(font.get("/FontMatrix", [0.001])[0])
            first = int(font.get("/FirstChar", 0))
            for offset, width in enumerate(font.get("/Widths", ArrayObject())):
                self._widths[first + offset] = float(width) * scale
            self._default = float(descriptor.get("/MissingWidth", 0)) * scale

    def _read_cid_widths(self, array) -> None:
        items = list(array)
        i = 0
        while i + 1 < len(items):
            first, second = items[i], items[i + 1]
            if isinstance(second, (list, ArrayObject)):
                for offset, width in enumerate(second):
                    self._widths[int(first) + offset] = float(width) / 1000
                i += 2
            else:
                if i + 2 >= len(items):
                    break
                for cid in range(int(first), int(second) + 1):
                    self._widths[cid] = float(items[i + 2]) / 1000
                i += 3

    def width(self, code: int) -> float:
        """Advance in text space at font size 1."""
        return self._widths.get(code, self._default)

    def is_missing(self, code: int) -> bool:
        return code in self._missing

    def code_for(self, char: str) -> Optional[bytes]:
        """The code that draws ``char`` in this font, if the font has it."""
        if self._codes is None:
            width = self.decoder.codespace[0][0]
            self._codes = {}
            for code, text in sorted(self.decoder.map.items(), reverse=True):
                if len(text) == 1 and not self.is_missing(code):
                    self._codes[text] = code.to_bytes(width, "big")
        return self._codes.get(char)


def glyphs(ops, fonts: DictionaryObject, cache: dict) -> list[Glyph]:
    """Every glyph drawn by a content stream's operators, in drawing order."""
    out: list[Glyph] = []
    ctm, fill = IDENTITY, (0.0, 0.0, 0.0)
    text = _TextState()
    stack: list[tuple] = []
    marked: list[Optional[str]] = []
    tm = tlm = IDENTITY
    block = 0

    for i, (operands, op) in enumerate(ops):
        if op == b"q":
            stack.append((ctm, fill, text.copy()))
        elif op == b"Q":
            if stack:
                ctm, fill, text = stack.pop()
        elif op == b"cm" and len(operands) == 6:
            ctm = multiply(tuple(float(v) for v in operands), ctm)
        elif op in (b"rg", b"g", b"k", b"sc", b"scn"):
            fill = _colour(operands, fill)
        elif op == b"BT":
            tm = tlm = IDENTITY
            block = len(out)
        elif op == b"ET":
            for g in out[block:]:
                g.end = i
        elif op == b"Tf" and len(operands) == 2:
            text.font = _font(fonts, operands[0], cache)
            text.resource = str(operands[0])
            text.size = float(operands[1])
        elif op == b"Tc" and operands:
            text.char_space = float(operands[0])
        elif op == b"Tw" and operands:
            text.word_space = float(operands[0])
        elif op == b"Tz" and operands:
            text.scale = float(operands[0]) / 100
        elif op == b"TL" and operands:
            text.leading = float(operands[0])
        elif op == b"Ts" and operands:
            text.rise = float(operands[0])
        elif op == b"Tr" and operands:
            text.render = int(operands[0])
        elif op in (b"Td", b"TD") and len(operands) == 2:
            tx, ty = float(operands[0]), float(operands[1])
            if op == b"TD":
                text.leading = -ty
            tm = tlm = multiply((1, 0, 0, 1, tx, ty), tlm)
        elif op == b"Tm" and len(operands) == 6:
            tm = tlm = tuple(float(v) for v in operands)
        elif op == b"T*":
            tm = tlm = multiply((1, 0, 0, 1, 0, -text.leading), tlm)
        elif op == b"BDC" and len(operands) == 2:
            props = operands[1]
            actual = props.get("/ActualText") if isinstance(props, DictionaryObject) else None
            marked.append(str(actual) if actual is not None else None)
        elif op == b"BMC":
            marked.append(None)
        elif op == b"EMC":
            if marked:
                marked.pop()
        elif op in SHOW_OPS:
            if op == b'"' and len(operands) == 3:
                text.word_space, text.char_space = float(operands[0]), float(operands[1])
            if op in (b"'", b'"'):
                tm = tlm = multiply((1, 0, 0, 1, 0, -text.leading), tlm)
            if text.font is None:
                continue
            parts = list(operands[0]) if op == b"TJ" and operands else operands[-1:]
            actual = next((a for a in reversed(marked) if a is not None), None)
            start = len(out)
            index = 0
            for part in parts:
                if not isinstance(part, (bytes, str)):
                    tx = -float(part) / 1000 * text.size * text.scale
                    tm = multiply((1, 0, 0, 1, tx, 0), tm)
                    continue
                data = _raw(part)
                for raw, code in text.font.decoder.codes(data):
                    w = text.font.width(code)
                    spacing = text.char_space + (text.word_space if raw == b" " else 0)
                    tx = (w * text.size + spacing) * text.scale
                    trm = multiply((text.size * text.scale, 0, 0, text.size, 0, text.rise),
                                   multiply(tm, ctm))
                    page = multiply(tm, ctm)
                    out.append(Glyph(
                        op=i, index=index, raw=raw, code=code,
                        text=text.font.decoder.char(code, len(raw)), font=text.font,
                        resource=text.resource,
                        matrix=trm, width=tx * math.hypot(page[0], page[1]),
                        adjust=-(w * 1000 + spacing * 1000 / text.size) if text.size else 0,
                        fill=fill, visible=text.render not in (3, 7), actual=actual, alone=False,
                        ctm=ctm))
                    tm = multiply((1, 0, 0, 1, tx, 0), tm)
                    index += 1
            if len(out) - start == 1:
                out[-1].alone = True
    return out


def remove_glyphs(ops, doomed: Iterable[Glyph], insert: Optional[dict[int, list]] = None) -> list:
    """``ops`` with the given glyphs no longer drawn, and ``insert[i]`` added after operator i.

    Each affected operator becomes a TJ in which a removed glyph is replaced
    by a number that moves the pen just as far, so the rest of the line stays
    exactly where it was.
    """
    by_op: dict[int, dict[int, Glyph]] = {}
    for g in doomed:
        by_op.setdefault(g.op, {})[g.index] = g
    insert = insert or {}
    if not by_op and not insert:
        return list(ops)
    new_ops = []
    for i, (operands, op) in enumerate(ops):
        new_ops += _without(operands, op, by_op.get(i))
        new_ops += insert.get(i, [])
    return new_ops


def _without(operands, op, gone: Optional[dict[int, Glyph]]) -> list:
    """One operator, rewritten so the glyphs in ``gone`` aren't drawn."""
    if not gone or op not in SHOW_OPS:
        return [(operands, op)]
    new_ops = []
    decoder = next(iter(gone.values())).font.decoder
    if op == b"'":
        new_ops.append(([], b"T*"))
    elif op == b'"':
        new_ops += [([operands[0]], b"Tw"), ([operands[1]], b"Tc"), ([], b"T*")]
    parts = list(operands[0]) if op == b"TJ" else operands[-1:]
    array = ArrayObject()
    index = 0
    pending = b""

    def flush():
        nonlocal pending
        if pending:
            array.append(ByteStringObject(pending))
            pending = b""

    def shift(amount: float):
        flush()
        if array and isinstance(array[-1], (FloatObject, NumberObject)):
            array[-1] = FloatObject(round(float(array[-1]) + amount, 4))
        else:
            array.append(FloatObject(round(amount, 4)))

    for part in parts:
        if not isinstance(part, (bytes, str)):
            shift(float(part))
            continue
        for raw, _ in decoder.codes(_raw(part)):
            if index in gone:
                shift(gone[index].adjust)
            else:
                pending += raw
            index += 1
    flush()
    new_ops.append(([array], b"TJ"))
    return new_ops


def invert(m: Matrix) -> Optional[Matrix]:
    a, b, c, d, e, f = m
    det = a * d - b * c
    if abs(det) < 1e-12:
        return None
    return (d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det)


def draw(runs: list["Run"], ctm: Matrix, name_for) -> list:
    """Operators that draw ``runs`` (in page coordinates) at a point in the
    stream where the transform is ``ctm``. ``name_for(font)`` gives the
    resource name for a run's font."""
    inverse = invert(ctm)
    if inverse is None or not runs:
        return []
    ops = [([], b"q"), ([FloatObject(round(v, 6)) for v in inverse], b"cm")]
    for run in runs:
        ops += [
            ([FloatObject(round(c, 4)) for c in run.fill], b"rg"),
            ([], b"BT"),
            ([NameObject(name_for(run.font)), FloatObject(round(run.size, 4))], b"Tf"),
            # Reset whatever text state the page left set.
            ([NumberObject(0)], b"Tc"), ([NumberObject(0)], b"Tw"), ([NumberObject(100)], b"Tz"),
            ([NumberObject(0)], b"Ts"), ([NumberObject(0)], b"Tr"),
            ([NumberObject(1), NumberObject(0), NumberObject(0), NumberObject(1),
              FloatObject(round(run.x, 4)), FloatObject(round(run.y, 4))], b"Tm"),
            ([ByteStringObject(run.data)], b"Tj"),
            ([], b"ET"),
        ]
    ops.append(([], b"Q"))
    return ops


def standard_font(writer, cache: dict, name: str) -> IndirectObject:
    """An indirect reference to one of the standard fonts, made once per file."""
    if name not in cache:
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/" + name),
        })
        if name in WIDTHS:
            font[NameObject("/Encoding")] = NameObject("/WinAnsiEncoding")
            font[NameObject("/FirstChar")] = NumberObject(32)
            font[NameObject("/LastChar")] = NumberObject(255)
            font[NameObject("/Widths")] = ArrayObject(NumberObject(w) for w in WIDTHS[name])
        cache[name] = writer._add_object(font)
    return cache[name]


@dataclass
class Run:
    """One piece of replacement text: a single font, size and position."""
    font: str               # a standard font ("Times-Roman"), or a page font ("/F10")
    size: float
    x: float
    y: float
    data: bytes             # in the font's encoding
    fill: tuple[float, float, float]


def encode(font: str, text: str) -> Optional[bytes]:
    """``text`` in ``font``'s encoding, or None if it has no glyph for a character."""
    if font == "Symbol":
        try:
            return bytes(SYMBOL[c][0] for c in text)
        except KeyError:
            return None
    try:
        data = text.encode("cp1252")
    except UnicodeEncodeError:
        return None
    widths = WIDTHS[font]
    if any(b < 32 or not widths[b - 32] for b in data):
        return None
    return data


def text_width(font: str, data: bytes) -> float:
    """Width of encoded ``data`` at font size 1."""
    if font == "Symbol":
        by_code = {code: width for code, width in SYMBOL.values()}
        return sum(by_code.get(b, 0) for b in data) / 1000
    widths = WIDTHS[font]
    return sum(widths[b - 32] for b in data if b >= 32) / 1000


@dataclass
class _TextState:
    font: Optional[Font] = None
    resource: str = ""
    size: float = 0.0
    char_space: float = 0.0
    word_space: float = 0.0
    scale: float = 1.0
    leading: float = 0.0
    rise: float = 0.0
    render: int = 0

    def copy(self) -> "_TextState":
        return _TextState(**self.__dict__)


def _colour(operands, current):
    values = []
    for v in operands:
        try:
            values.append(float(v))
        except (TypeError, ValueError):
            return current  # a pattern
    if len(values) == 1:
        return (values[0],) * 3
    if len(values) == 3:
        return tuple(values)
    if len(values) == 4:
        c, m, y, k = values
        return ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    return current


def page_fonts(fonts: DictionaryObject, cache: dict) -> dict[str, Font]:
    """Every font in a page's resources, by resource name."""
    out = {}
    for name in fonts:
        try:
            font = _font(fonts, name, cache)
        except Exception:  # a broken font dictionary: just don't reuse it
            continue
        if font is not None:
            out[str(name)] = font
    return out


def _font(fonts, name, cache) -> Optional[Font]:
    ref = fonts.raw_get(name) if name in fonts else None
    if ref is None:
        return None
    key = (ref.idnum, ref.generation) if isinstance(ref, IndirectObject) else id(ref)
    if key not in cache:
        cache[key] = Font(ref.get_object())
    return cache[key]


def _raw(string) -> bytes:
    return getattr(string, "original_bytes", None) or str(string).encode("latin-1", "replace")


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
        return "".join(self.char(code, len(raw)) for raw, code in self.codes(data))

    def codes(self, data: bytes) -> Iterable[tuple[bytes, int]]:
        """(bytes, code) for each character code in ``data``."""
        i = 0
        while i < len(data):
            width = self._code_width(data, i)
            raw = data[i:i + width]
            yield raw, int.from_bytes(raw, "big")
            i += width

    def char(self, code: int, width: int = 1) -> str:
        return self.map.get(code, chr(code) if width == 1 and not self.map else "�")

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
