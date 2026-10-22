from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from senai_remover import clean_pdf
from senai_remover.core import _page_fonts
from senai_remover.pdftext import glyphs, remove_glyphs
from senai_remover.repair import split_words

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
    assert "sum to 180°" in text
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


def test_split_words():
    assert split_words("Anisoscelestrianglehastwoequalsides") == \
        ["An", "isosceles", "triangle", "has", "two", "equal", "sides"]
    assert split_words("Thusthereare") == ["Thus", "there", "are"]
    assert split_words("Commonprimefactors") == ["Common", "prime", "factors"]
    assert split_words("HCF") == ["HCF"]
    assert split_words("xqzvbn") is None  # not words: left alone
