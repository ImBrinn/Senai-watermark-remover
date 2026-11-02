from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from senai_remover import clean_pdf
from senai_remover.core import _page_fonts
from senai_remover.pdftext import Glyph, encode, glyphs, remove_glyphs, text_width
from senai_remover.repair import _degree, _place_relation, split_words

MATHS = Path(__file__).parent / "fixtures" / "maths_sample.pdf"


def visible_glyphs(path, number=0):
    page = PdfReader(path).pages[number]
    return [g for g in glyphs(page.get_contents().operations, _page_fonts(page), {}) if g.visible]


def test_the_sample_has_the_faults():
    # Chrome with only the Liberation fonts, like SenAI's: empty boxes and
    # squashed italic sentences. If this fails, regenerate the fixture.
    found = visible_glyphs(MATHS)
    assert sum(g.missing for g in found) == 6
    text = PdfReader(MATHS).pages[0].extract_text()
    assert "Anisoscelestrianglehastwoequalsides" in text.replace(" ", "")


def test_boxes_and_squashed_sentences_are_fixed(tmp_path):
    out = tmp_path / "out.pdf"
    result = clean_pdf(MATHS, out)

    assert Counter(what for _, what in result.repaired) == {"°": 4, "·": 1, "⟹": 1, "spaces": 2}
    assert not any(g.missing for g in visible_glyphs(out))  # no empty boxes left
    text = PdfReader(out).pages[0].extract_text()
    assert "An isosceles triangle has two equal sides." in text
    assert "Thus there are 2 equal angles." in text
    # The degree sign is a separate raised glyph, so an extractor may put a
    # space before it. Visually it still reads as 180°.
    assert "sumto180°" in text.replace(" ", "")
    assert "6 = 2 · 3" in text


def test_repaired_text_matches_the_text_around_it(tmp_path):
    out = tmp_path / "out.pdf"
    clean_pdf(MATHS, out)
    found = visible_glyphs(out)
    sentence = [g for g in found if g.text in "isosceles" and abs(g.y - _y_of(found, "An")) < 1]
    # Set again in the document's own upright serif, not italic.
    assert sentence and all(g.font.name == "LiberationSerif" for g in sentence)
    # Maths that wasn't broken stays as it was: "x = 60" keeps its italic x.
    x = [g for g in found if g.text == "x"]
    assert x and all(g.font.italic for g in x)


def _y_of(found, start):
    for a, b in zip(found, found[1:]):
        if a.text + b.text == start:
            return a.y
    raise AssertionError(start)


def test_repairs_can_be_turned_off(tmp_path):
    out = tmp_path / "out.pdf"
    result = clean_pdf(MATHS, out, repair=False)
    assert result.repaired == []
    assert sum(g.missing for g in visible_glyphs(out)) == 6


def test_cleaning_twice_repairs_nothing_more(tmp_path):
    once, twice = tmp_path / "once.pdf", tmp_path / "twice.pdf"
    clean_pdf(MATHS, once)
    assert clean_pdf(once, twice).repaired == []


def test_removing_a_glyph_leaves_the_rest_in_place(make_pdf):
    source = make_pdf(b"BT /F1 12 Tf 72 700 Td (Hello world) Tj ET")
    page = PdfReader(source).pages[0]
    fonts = _page_fonts(page)
    ops = page.get_contents().operations
    before = glyphs(ops, fonts, {})
    after = glyphs(remove_glyphs(ops, [before[1]]), fonts, {})  # take out the "e"
    assert "".join(g.text for g in after) == "Hllo world"
    assert [round(g.x, 3) for g in after] == [round(g.x, 3) for g in before if g is not before[1]]


def test_degree_signs_stay_raised_and_clear_of_what_follows(tmp_path):
    # Chrome draws the empty box as a small raised mark. The replacement has
    # to stay in that box: a full-size sign on the digit baseline overlaps the
    # full stop and closes the gap before a minus or an equals.
    out = tmp_path / "out.pdf"
    clean_pdf(MATHS, out)
    found = visible_glyphs(out)
    degrees = [g for g in found if g.text == "°"]
    assert len(degrees) == 4
    for deg in degrees:
        # The digit it sits on: raised by a fraction of an em, and just to its left.
        bases = [c for c in found if c.text.isdigit()
                 and 0.15 * c.size < deg.y - c.y < 0.8 * c.size
                 and c.right - 0.35 * c.size <= deg.x <= c.right + c.size]
        assert bases, "a degree sign has no digit under it"
        base = min(bases, key=lambda c: (deg.y - c.y, abs(deg.x - c.right)))
        assert deg.y - base.y > 0.2 * base.size
        assert deg.size < 0.9 * base.size
        obstacles = [c for c in found if c is not deg and c.x > deg.x + 0.15 * deg.size
                     and (abs(c.y - deg.y) <= 0.35 * deg.size
                          or abs(c.y - base.y) <= 0.25 * base.size)]
        nxt = min(obstacles, key=lambda c: c.x)
        assert deg.right <= nxt.x + 0.2


def _mark(x, y, size, width, text="0"):
    return Glyph(0, 0, b" ", 0, text, None, "/F1", (size, 0, 0, size, x, y),
                 width, 0, (0, 0, 0), True, None, True)


class _DegreeFace:
    def find(self, char, like):
        data = encode("Times-Roman", "°")
        return "Times-Roman", data, text_width("Times-Roman", data)


def test_degree_on_a_numerator_stays_above_the_bar():
    # 180° over 3: the box sits above the numerator. The denominator is not
    # an obstacle, and the sign must not drop onto the numerator's baseline.
    base = _mark(264.0, 437.13, 11.0, 6.1)
    box = _mark(270.1, 440.9, 7.69, 2.81, "")
    denom = _mark(260.78, 422.13, 11.0, 6.0, "3")
    run = _degree(box, base, [base, box, denom], _DegreeFace())
    assert run is not None
    assert abs(run.y - box.y) < 0.05
    assert run.size <= box.size + 0.01
    assert run.y > base.y + 0.2 * base.size


def test_degree_leaves_the_gap_before_an_operator():
    base = _mark(136.4, 596.9, 10.99, 6.0)          # ends at 142.4
    box = _mark(142.5, 601.38, 7.69, 2.81, "")
    minus = _mark(148.18, 596.9, 10.99, 6.3, "−")
    run = _degree(box, base, [base, box, minus], _DegreeFace())
    advance = text_width(run.font, run.data) * run.size
    assert run.y > base.y + 0.2 * base.size
    assert run.size <= box.size + 0.01
    assert run.x + advance <= minus.x - 0.1


def test_a_relation_keeps_a_gap_it_fits_and_shrinks_one_it_does_not():
    # Centred in the gap, same size, when the arrow already fits.
    size, x = _place_relation(114.6, 136.45, 11.25, 0.987, both=True)
    assert size == 11.25
    assert abs(x - ((114.6 + 136.45) / 2 - 0.987 * 11.25 / 2)) < 1e-6
    # Narrower than the arrow: smaller, and still inside the gap.
    size, x = _place_relation(100.0, 108.0, 11.25, 0.987, both=True)
    advance = 0.987 * size
    assert size < 11.25
    assert x >= 100.0 - 0.05
    assert x + advance <= 108.0 + 0.05
    # No neighbours: leave the natural size, even if the box is narrow.
    size, _ = _place_relation(0.0, 8.0, 11.25, 0.987, both=False)
    assert size == 11.25


def test_split_words():
    assert split_words("Anisoscelestrianglehastwoequalsides") == \
        ["An", "isosceles", "triangle", "has", "two", "equal", "sides"]
    assert split_words("Thusthereare") == ["Thus", "there", "are"]
    assert split_words("Commonprimefactors") == ["Common", "prime", "factors"]
    assert split_words("HCF") == ["HCF"]
    assert split_words("xqzvbn") is None  # not words: left alone
