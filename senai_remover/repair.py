"""Repair the typesetting faults in SenAI exports.

SenAI draws its answers with headless Chrome, which sets maths in the
Liberation fonts. Those fonts lack some maths symbols, and the generator
puts some sentences inside maths, so its PDFs come out with:

- empty boxes where a symbol should be (the font's glyph 0, ".notdef"):
  degree signs, multiplication dots and the "implies" arrow;
- sentences with no spaces, in maths italic:
  "Anisoscelestrianglehastwoequalsides."

``repair_page`` finds both, takes the broken glyphs out of the page, and
draws the right text in their place. It uses the fonts already in the PDF
wherever they have the characters needed, so a repair looks like the text
around it, and otherwise the standard PDF fonts (Times, Symbol), which every
PDF viewer has.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Optional

from .pdftext import Font, Glyph, Run, draw, encode, glyphs, page_fonts, remove_glyphs, text_width

SERIF = "Times-Roman"
SYMBOL = "Symbol"

# Maths words SenAI uses that aren't in the general word list, or that it
# would otherwise split ("hcf" -> "h cf").
EXTRA_WORDS = (
    "hcf lcm gcd gcf lcd factorise factorised factorises factorising factorisation "
    "simplify simplified simplifies simplifying denominators numerators "
    "multiples factors integers decimals fractions"
).split()

# Punctuation that hangs on the word before it, and brackets that open.
CLOSING = set(".,:;!?)]}%")
OPENING = set("([{")


@dataclass
class Repairs:
    removed: list[Glyph] = field(default_factory=list)
    # Replacement text, each with the glyph whose place in the stream it takes.
    drawn: list[tuple[Glyph, list[Run]]] = field(default_factory=list)
    # What was fixed: a symbol such as "°" for each box, "spaces" for each sentence.
    fixes: list[str] = field(default_factory=list)


def repair_page(ops, fonts, cache: dict, library: Optional[list] = None,
                add_font: Optional[Callable] = None,
                name_for: Callable = lambda font: font) -> tuple[list, list[str]]:
    """(new operators, list of fixes) for one page.

    ``library`` lists (reference, Font) for fonts on other pages, which may
    have a symbol this page's fonts don't; ``add_font(reference)`` adds one
    to this page and returns its resource name. ``name_for(font)`` gives the
    resource name for a font, standard fonts included.
    """
    found = [g for g in glyphs(ops, fonts, cache)
             if g.visible and g.upright and g.size > 0 and g.end >= 0]
    faces = _Faces(page_fonts(fonts, cache), library or [], add_font)
    repairs = Repairs()
    symbols = _missing_symbols(found)
    done: set[Glyph] = set()
    for line in _lines(found):
        for chain in _chains(line):
            if _respace(chain, found, symbols, faces, repairs):
                done.update(chain)
    for g, char in symbols.items():
        if g in done:
            continue
        drawn = _draw_symbol(g, char, found, faces)
        if drawn is not None:
            repairs.removed.append(g)
            repairs.drawn.append(drawn)
            repairs.fixes.append(char)
    insert: dict[int, list] = {}
    for anchor, runs in repairs.drawn:
        # Right after the anchor's text object, so it reads in the same order.
        insert.setdefault(anchor.end, []).extend(draw(runs, anchor.ctm, name_for))
    return remove_glyphs(ops, repairs.removed, insert), repairs.fixes


class _Faces:
    """Where to get a glyph for a character: the PDF's own fonts first.

    Letters come only from the same typeface, so a word never mixes fonts.
    A symbol can come from any upright font in the document, as Chrome drew
    the symbols it did have from fallback fonts.
    """

    def __init__(self, fonts: dict[str, Font], library: list, add_font: Optional[Callable]):
        self.fonts = fonts
        self.library = library
        self.add_font = add_font

    def find(self, char: str, like: Font, italic: Optional[bool] = None) -> Optional[tuple[str, bytes, float]]:
        """(font, bytes, width at size 1) for ``char`` in the style of ``like``."""
        want_italic = like.italic if italic is None else italic
        for name, font in self.fonts.items():
            if (like.family and font.family == like.family and font.italic == want_italic
                    and font.bold == like.bold):
                code = font.code_for(char)
                if code is not None:
                    return name, code, font.width(int.from_bytes(code, "big"))
        if not char.isalnum():
            for name, font in self.fonts.items():
                code = font.code_for(char) if not font.italic else None
                if code is not None:
                    return name, code, font.width(int.from_bytes(code, "big"))
            if self.add_font is not None:
                for ref, font in self.library:
                    code = font.code_for(char) if not font.italic else None
                    if code is not None:
                        return self.add_font(ref), code, font.width(int.from_bytes(code, "big"))
        for face in (("Times-Bold" if like.bold else SERIF), SYMBOL):
            data = encode(face, char)
            if data is not None:
                return face, data, text_width(face, data)
        return None

    def first(self, chars: str, like: Font) -> Optional[tuple[str, str, bytes, float]]:
        """(char, font, bytes, width) for the first of ``chars`` there's a glyph for."""
        for char in chars:
            face = self.find(char, like)
            if face is not None:
                return (char, *face)
        return None


# -- Missing symbols ---------------------------------------------------------

def _missing_symbols(found: list[Glyph]) -> dict[Glyph, str]:
    """{glyph: the character it should be} for each empty box we can identify."""
    out = {}
    for g in found:
        if not g.missing:
            continue
        actual = (g.actual or "").strip()
        if actual in ("∘", "°", "º") or (not actual and _base_of_superscript(g, found)):
            out[g] = "°"
        elif actual in ("⋅", "·", "∙"):
            out[g] = "·"
        elif actual in ("⟹", "⇒"):
            out[g] = "⟹"
        elif len(actual) == 1:
            out[g] = actual
        elif not actual:
            gap = _operator_gap(g, found)
            if gap is not None and 0.15 <= gap < 0.25:     # a binary operator's spacing: the dot
                out[g] = "·"
            elif gap is not None and 0.25 <= gap <= 0.7:   # a relation's: the implies arrow
                out[g] = "⟹"
    return out


# Stand-ins, best first, for a symbol no font in the file has.
ALTERNATIVES = {"⟹": "⟹⇒", "·": "·⋅"}


def _draw_symbol(g: Glyph, char: str, found: list[Glyph], faces: _Faces):
    """(the glyph to draw it after, [Run]) for the symbol replacing box ``g``."""
    face = faces.first(ALTERNATIVES.get(char, char), g.font)
    if face is None:
        return None
    char, font, data, width = face
    if char == "°":
        base = _base_of_superscript(g, found)
        if base is not None:
            run = _degree(g, base, found, faces)
            return (base, [run]) if run is not None else None  # so it reads "180°"
    if char in "⟹⇒→":
        left, right = _neighbours(g, found)
        lo = left.right if left else g.x
        hi = right.x if right else g.right
        return g, [Run(font, g.size, (lo + hi) / 2 - width * g.size / 2, g.y, data, g.fill)]
    return g, [Run(font, g.size, g.x + (g.width - width * g.size) / 2, g.y, data, g.fill)]


def _base_of_superscript(g: Glyph, found: list[Glyph]) -> Optional[Glyph]:
    """The full-size glyph a raised, smaller box sits on, if it is a superscript."""
    best = None
    for c in found:
        if c is g or c.missing or c.size < g.size * 1.15:
            continue
        raised = (g.y - c.y) / c.size
        if not 0.1 <= raised <= 0.8:
            continue
        if not (g.x - 0.6 * c.size <= c.right <= g.x + 0.25 * c.size):
            continue
        if best is None or c.right > best.right:
            best = c
    return best


def _degree(g: Glyph, base: Glyph, found: list[Glyph], faces: _Faces) -> Optional[Run]:
    """A degree sign after ``base``, its top level with the top of the digits.

    It is drawn a little smaller than the text if that's what keeps it clear
    of whatever follows, usually a full stop.
    """
    face = faces.find("°", base.font)
    if face is None:
        return None
    font, data, _ = face
    size = base.size
    after = [c for c in found if c is not g and c is not base and abs(c.y - base.y) < 0.2 * size
             and c.x >= base.right - 0.05 * size]
    limit = min((c.x for c in after), default=math.inf)
    start = base.right + 0.03 * size
    # A degree sign's ring spans about 0.06 to 0.34 em across and 0.39 to
    # 0.68 em up; a following full stop has about 0.07 em of side bearing.
    room = limit + 0.04 * size - start
    scale = max(0.7, min(1.0, room / (0.34 * size))) if limit < math.inf else 1.0
    deg = size * scale
    rise = 0.676 * (size - deg)
    return Run(font, deg, start - 0.057 * deg, base.y + rise, data, g.fill)


def _operator_gap(g: Glyph, found: list[Glyph]) -> Optional[float]:
    """The narrower of the spaces either side of ``g``, in ems, or None."""
    left, right = _neighbours(g, found)
    if left is None or right is None:
        return None
    return min(g.x - left.right, right.x - g.right) / g.size


def _neighbours(g: Glyph, found: list[Glyph]):
    same = [c for c in found if c is not g and abs(c.y - g.y) < 0.05 * g.size
            and abs(c.size - g.size) < 0.05 * g.size]
    left = max((c for c in same if c.right <= g.x + 0.05 * g.size), key=lambda c: c.right, default=None)
    right = min((c for c in same if c.x >= g.right - 0.05 * g.size), key=lambda c: c.x, default=None)
    return left, right


# -- Sentences with no spaces ------------------------------------------------

def _lines(found: list[Glyph]) -> list[list[Glyph]]:
    """Glyphs grouped by baseline and size, each line in reading order."""
    lines: list[list[Glyph]] = []
    for g in sorted(found, key=lambda g: (-g.y, g.size)):
        for line in lines:
            first = line[0]
            if abs(first.y - g.y) < 0.05 * first.size and abs(first.size - g.size) < 0.03 * first.size:
                line.append(g)
                break
        else:
            lines.append([g])
    return [sorted(line, key=lambda g: g.x) for line in lines]


def _chains(line: list[Glyph]) -> list[list[Glyph]]:
    """A line split wherever there's a gap wider than a space or two."""
    chains, chain = [], []
    for g in line:
        if chain and g.x - chain[-1].right > 0.8 * g.size:
            chains.append(chain)
            chain = []
        chain.append(g)
    if chain:
        chains.append(chain)
    return chains


def _letter_runs(chain: list[Glyph], symbols) -> list[list[Glyph]]:
    """Runs of single maths-italic letters set without spaces between them."""
    runs, run = [], []
    for g in chain:
        letter = (g.alone and g.font.italic and g not in symbols
                  and len(g.text) == 1 and g.text.isalpha())
        if letter and run and g.x - run[-1].right < 0.2 * g.size:
            run.append(g)
            continue
        if len(run) > 1:
            runs.append(run)
        run = [g] if letter else []
    if len(run) > 1:
        runs.append(run)
    return runs


@dataclass
class _Piece:
    text: str
    source: Optional[Glyph]   # draw this original glyph again, or None for new text
    like: Glyph               # whose font, size, rise and colour the text takes
    upright: bool = False     # set it in the upright face of the font


def _respace(chain: list[Glyph], found: list[Glyph], symbols, faces: _Faces, repairs: Repairs) -> bool:
    """Set a run-together sentence again with its spaces. True if it was."""
    splits = {}
    for run in _letter_runs(chain, symbols):
        letters = "".join(g.text for g in run)
        words = split_words(letters)
        if words is None:
            if len(run) > 4:
                return False  # a long run we can't read: leave the line alone
            words = [letters]  # short, like "HCF": keep it as it is
        splits[run[0]] = (run, words)
    if not any(len(words) > 1 for _, words in splits.values()):
        return False

    first = chain[0]
    size, y = first.size, first.y
    x0, x1 = first.x, chain[-1].right
    members = set(chain)
    attached = [g for g in found if g not in members and g.right > x0 and g.x < x1
                and -0.5 * size < g.y - y < 0.9 * size]
    if any(g.size > 0.9 * size for g in attached):
        return False  # something else shares the line (a fraction, another line)
    items = sorted(chain + attached, key=lambda g: g.x)

    # The new line as pieces of text, with the spaces put back.
    pieces: list[_Piece] = []
    previous: Optional[Glyph] = None
    i = 0
    while i < len(items):
        g = items[i]
        if g in splits:
            run, words = splits[g]
            text = " ".join(words)
            piece = _Piece(text, None, g, upright=True)
            last = run[-1]
        elif _is_label(items, i, symbols):
            # "a)" starting a point: a label, so upright like the words after it.
            text = g.text
            piece = _Piece(text, None, g, upright=True)
            last = g
        else:
            text = symbols.get(g, g.text)
            piece = _Piece(text, None if g in symbols else g, g)
            last = g
        if previous is not None and _needs_space(previous, g, pieces[-1].text, text,
                                                 _next_text(items, i, splits), g in members):
            pieces.append(_Piece(" ", None, first, upright=True))
        pieces.append(piece)
        previous = last
        i = items.index(last) + 1

    runs = _layout(pieces, x0, y, faces)
    if runs is None:
        return False
    end = max(r.x + r_width for r, r_width in runs)
    right_edge = max(g.right for g in found)
    if end > max(right_edge, x1) + 0.5:
        return False  # it would run past the text column
    clash = [g for g in found if g not in members and g not in attached
             and abs(g.y - y) < size and x1 < g.x < end + 0.3 * size]
    if clash:
        return False  # it would run into text further along the line

    repairs.removed += items
    repairs.drawn.append((first, [run for run, _ in runs]))
    repairs.fixes.append("spaces")
    repairs.fixes += [symbols[g] for g in items if g in symbols]
    return True


def _is_label(items, i, symbols) -> bool:
    g = items[i]
    return (i == 0 and g.font.italic and g not in symbols and len(g.text) == 1
            and g.text.isalpha() and i + 1 < len(items) and items[i + 1].text == ")")


def _next_text(items, i, splits) -> str:
    """The text that follows item ``i``, looking past one bracket: "(more" -> "more"."""
    for g in items[i + 1:i + 3]:
        if g in splits:
            return splits[g][1][0]
        if g.text not in OPENING:
            return g.text
    return ""


def _needs_space(previous: Glyph, g: Glyph, before: str, text: str, following: str,
                 on_line: bool) -> bool:
    if not on_line or not before or not text or before.endswith(" ") or text.startswith(" "):
        return False  # superscripts and subscripts hang on what's before them
    if text[0] in CLOSING or before[-1] in OPENING:
        return False
    a, b = before[-1], text[0]
    if b in OPENING:
        # "16(more than two)" -> "16 (more than two)", but "4(2p + 3)" stays.
        return a.isalnum() and len(following) > 1 and following.isalpha()
    if (g.x - previous.right) / previous.size > 0.1:
        return True
    # "are2equal", "2and11", "a)1": a space between words and numbers.
    return ((a.isalpha() and b.isdigit()) or (a.isdigit() and b.isalpha())
            or (a in ")]}" and b.isalnum()))


def _layout(pieces: list[_Piece], x: float, y: float, faces: _Faces) -> Optional[list[tuple[Run, float]]]:
    """(run, width) for each piece of the new line, left to right."""
    runs: list[tuple[Run, float]] = []
    for piece in pieces:
        like = piece.like
        rise = like.y - y
        if piece.source is not None and not piece.source.missing:
            g = piece.source
            parts = [(g.resource, g.raw, g.font.width(g.code))]
        else:
            parts = []
            for char in piece.text:
                face = faces.first(ALTERNATIVES.get(char, char), like.font) if piece.source is None \
                    and not piece.upright else None
                face = face[1:] if face else faces.find(char, like.font, italic=False if piece.upright else None)
                if face is None:
                    return None
                parts.append(face)
        for font, data, width in parts:
            advance = width * like.size
            if runs:
                last, last_width = runs[-1]
                if last.font == font and last.size == like.size and last.y == y + rise \
                        and abs(last.x + last_width - x) < 1e-6:
                    last.data += data
                    runs[-1] = (last, last_width + advance)
                    x += advance
                    continue
            runs.append((Run(font, like.size, x, y + rise, data, like.fill), advance))
            x += advance
    return runs


@lru_cache(maxsize=1)
def _vocabulary() -> tuple[dict[str, float], int]:
    from ._words import words

    ranked = words()
    scale = math.log(len(ranked))
    cost = {w: math.log((i + 1) * scale) for i, w in enumerate(ranked)}
    for w in EXTRA_WORDS:
        cost[w] = min(cost.get(w, math.inf), math.log(2000 * scale))
    return cost, max(len(w) for w in cost)


@lru_cache(maxsize=4096)
def _split(lowered: str) -> Optional[tuple[str, ...]]:
    cost, longest = _vocabulary()
    best = [0.0] + [math.inf] * len(lowered)
    back = [0] * (len(lowered) + 1)
    for i in range(1, len(lowered) + 1):
        for k in range(1, min(i, longest) + 1):
            c = cost.get(lowered[i - k:i])
            if c is not None and best[i - k] + c < best[i]:
                best[i], back[i] = best[i - k] + c, k
    if best[-1] == math.inf:
        return None
    words, i = [], len(lowered)
    while i:
        words.append(lowered[i - back[i]:i])
        i -= back[i]
    words.reverse()
    # Lone letters other than "a" and "I" mean the split is a guess.
    if any(len(w) == 1 and w not in ("a", "i") for w in words):
        return None
    return tuple(words)


def split_words(text: str) -> Optional[list[str]]:
    """``text`` (letters only, no spaces) split into English words, or None.

    Takes the most likely split by word frequency (Zipf's law), as wordninja
    does, keeping the letters' case. Returns None when the letters can't be
    read as real words.
    """
    words = _split(text.lower())
    if words is None:
        return None
    out, i = [], 0
    for word in words:
        out.append(text[i:i + len(word)])
        i += len(word)
    return out
