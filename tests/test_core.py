import shutil
from collections import Counter

from pypdf import PdfReader
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from senai_remover import DEFAULT_PATTERNS, clean_pdf, default_output_path
from senai_remover.core import _FontDecoder, is_output_name, name_problem, output_name

from conftest import FIXTURE


def page_texts(path):
    return [page.extract_text() for page in PdfReader(path).pages]


def glyphs(text):
    return Counter(c for c in text if not c.isspace())


def test_removes_title_and_every_footer(tmp_path):
    out = tmp_path / "out.pdf"
    result = clean_pdf(FIXTURE, out)

    assert result.pages == 3
    assert result.removed == [(1, "SenAI Maths"), (1, "senai.uk"), (2, "senai.uk"), (3, "senai.uk")]
    assert result.warnings == []
    for text in page_texts(out):
        assert "senai" not in text.lower()


def test_everything_else_is_untouched(tmp_path):
    out = tmp_path / "out.pdf"
    clean_pdf(FIXTURE, out)

    for number, (before, after) in enumerate(zip(page_texts(FIXTURE), page_texts(out)), start=1):
        branding = glyphs("senai.uk") + (glyphs("SenAI Maths") if number == 1 else Counter())
        title = glyphs("Brinns autocompleter") if number == 1 else Counter()
        assert glyphs(after) == glyphs(before) - branding + title
        assert "The Senate of senators agrees" in after
        assert str(number) in after  # page number stays


def test_cleaning_twice_finds_nothing(tmp_path):
    once, twice = tmp_path / "once.pdf", tmp_path / "twice.pdf"
    clean_pdf(FIXTURE, once)
    result = clean_pdf(once, twice)
    assert not result.changed
    assert page_texts(once) == page_texts(twice)


def test_can_overwrite_the_source(tmp_path):
    path = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, path)
    assert clean_pdf(path, path).changed
    assert "senai" not in "".join(page_texts(path)).lower()


def test_simple_font_without_tounicode(make_pdf, tmp_path):
    source = make_pdf(
        b"BT /F1 24 Tf 72 720 Td (SenAI Maths) Tj ET\n"
        b"BT /F1 12 Tf 72 680 Td (Answer: 42) Tj ET"
    )
    out = tmp_path / "out.pdf"
    result = clean_pdf(source, out)

    assert result.removed == [(1, "SenAI Maths")]
    text = page_texts(out)[0]
    assert "SenAI" not in text
    assert "Answer: 42" in text


def test_branding_that_positions_later_text_is_hidden_not_deleted(make_pdf, tmp_path):
    # Deleting "senai.uk" would slide the page number left, so it is drawn
    # invisibly (render mode 3) instead.
    source = make_pdf(b"BT /F1 9 Tf 72 30 Td (senai.uk) Tj (    1) Tj ET")
    out = tmp_path / "out.pdf"
    result = clean_pdf(source, out)

    assert result.removed == [(1, "senai.uk")]
    assert any("hidden" in w for w in result.warnings)
    ops = PdfReader(out).pages[0].get_contents().operations
    assert ops[3:7] == [([3], b"Tr"), (["senai.uk"], b"Tj"), ([0], b"Tr"), (["    1"], b"Tj")]


def test_quote_operators_keep_line_spacing(make_pdf, tmp_path):
    source = make_pdf(b"BT /F1 12 Tf 14 TL 72 700 Td (Line one) Tj (senai.uk) ' (Line three) ' ET")
    out = tmp_path / "out.pdf"
    clean_pdf(source, out)

    ops = [op for _, op in PdfReader(out).pages[0].get_contents().operations]
    assert ops[-4:] == [b"Tj", b"T*", b"'", b"ET"]
    assert "senai" not in page_texts(out)[0]


def test_branding_mixed_into_other_text_is_reported_not_mangled(make_pdf, tmp_path):
    source = make_pdf(b"BT /F1 12 Tf 72 700 Td (Made with SenAI tools) Tj ET")
    out = tmp_path / "out.pdf"
    result = clean_pdf(source, out)

    assert not result.changed
    assert any("could not cleanly remove 'SenAI'" in w for w in result.warnings)
    assert "Made with SenAI tools" in page_texts(out)[0]


def test_links_and_metadata(make_pdf, tmp_path):
    source = make_pdf(
        b"BT /F1 12 Tf 72 700 Td (Answer: 42) Tj ET",
        link="https://senai.uk/maths",
        metadata={"/Title": "SenAI Maths", "/Author": "Student"},
    )
    out = tmp_path / "out.pdf"
    result = clean_pdf(source, out)

    assert (1, "https://senai.uk/maths") in result.removed
    assert (0, "/Title: SenAI Maths") in result.removed
    reader = PdfReader(out)
    assert not reader.pages[0].get("/Annots")
    assert reader.metadata.get("/Title") == "input"  # the file's name, not SenAI's
    assert reader.metadata.get("/Author") == "Student"


def test_extra_patterns(make_pdf, tmp_path):
    source = make_pdf(b"BT /F1 12 Tf 72 700 Td (Answer: 42) Tj ET BT /F1 12 Tf 72 680 Td (Keep me) Tj ET")
    out = tmp_path / "out.pdf"
    result = clean_pdf(source, out, patterns=[*DEFAULT_PATTERNS, r"answer: \d+"])

    assert result.removed == [(1, "Answer: 42")]
    assert page_texts(out)[0].strip() == "Keep me"


def test_tounicode_cmap_parsing():
    cmap = DecodedStreamObject()
    cmap.set_data(
        b"1 begincodespacerange <0000> <FFFF> endcodespacerange\n"
        b"1 beginbfchar <0003> <0020> endbfchar\n"
        b"2 beginbfrange <0010> <0012> <0041>\n<0020> <0021> [<0078> <00D7>] endbfrange"
    )
    font = DictionaryObject({NameObject("/Subtype"): NameObject("/Type0"), NameObject("/ToUnicode"): cmap})
    decoder = _FontDecoder(font)
    assert decoder.decode(bytes.fromhex("0010 0011 0012 0003 0020 0021")) == "ABC x×"


def test_default_output_path(tmp_path):
    source = tmp_path / "hw.pdf"
    assert default_output_path(source) == tmp_path / "hw-clean.pdf"
    assert default_output_path(source, tmp_path / "out") == tmp_path / "out" / "hw.pdf"
    assert default_output_path(source, tmp_path / "out", "_x") == tmp_path / "out" / "hw_x.pdf"


def test_title_takes_the_place_of_senais(tmp_path):
    out = tmp_path / "out.pdf"
    result = clean_pdf(FIXTURE, out)
    assert result.title == "Brinns autocompleter"
    first = page_texts(out)[0]
    assert first.lstrip().startswith("Brinns autocompleter")
    assert "Brinns" not in "".join(page_texts(out)[1:])  # only ever on page 1

    clean_pdf(FIXTURE, out, title="Week 7 answers")
    assert page_texts(out)[0].lstrip().startswith("Week 7 answers")
    for no_title in (None, ""):
        assert clean_pdf(FIXTURE, out, title=no_title).title is None
        assert "Brinns" not in page_texts(out)[0]


def test_title_is_drawn_like_the_old_one(tmp_path):
    from senai_remover.core import _page_fonts, _title_run

    page = PdfReader(FIXTURE).pages[0]
    run, old = _title_run(page.get_contents().operations, _page_fonts(page), {}, "Brinns autocompleter")
    assert (round(run.x), round(run.y)) == (round(old.x), round(old.y))  # where SenAI's started
    assert run.font == "Helvetica-Bold"  # SenAI's title is Liberation Sans Bold
    assert 15 < run.size < 18 and run.data == b"Brinns autocompleter"


def test_no_title_added_without_senais(make_pdf, tmp_path):
    source = make_pdf(b"BT /F1 12 Tf 72 700 Td (Answer: 42) Tj ET")
    result = clean_pdf(source, tmp_path / "out.pdf")
    assert result.title is None
    assert "Brinns" not in page_texts(tmp_path / "out.pdf")[0]


def test_output_names():
    assert output_name("Week 3.pdf") == "Week 3-clean.pdf"
    assert output_name("Week 3.pdf", "Brinn - {name}") == "Brinn - Week 3.pdf"
    assert output_name("a/b/hw.PDF", "{name} (done)") == "hw (done).PDF"

    assert name_problem("{name}-clean") is None
    assert name_problem("{name}") is None
    assert name_problem("") == "Type a name for the cleaned copies, using {name} for the original name."
    assert name_problem("clean") == "Put {name} where the original file name should go."
    assert name_problem("{name}?") == "File names can't contain ?"
    assert name_problem("{name}.") == "File names can't end with a full stop."

    assert is_output_name("hw-clean") and is_output_name("hw_clean")  # new and old style
    assert not is_output_name("hw") and not is_output_name("clean")
    assert is_output_name("Brinn - hw", "Brinn - {name}")
    assert not is_output_name("hw", "{name}")
