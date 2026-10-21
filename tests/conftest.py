from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.annotations import Link
from pypdf.generic import ContentStream, DictionaryObject, NameObject

FIXTURE = Path(__file__).parent / "fixtures" / "senai_sample.pdf"


@pytest.fixture
def make_pdf(tmp_path):
    """Build a one-page PDF with Helvetica as /F1 and the given content stream."""

    def make(content: bytes, name="input.pdf", link=None, metadata=None) -> Path:
        writer = PdfWriter()
        page = writer.add_blank_page(612, 792)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = ContentStream(None, writer)
        stream.set_data(content)
        page.replace_contents(stream)
        if link:
            writer.add_annotation(0, Link(rect=(70, 20, 200, 40), url=link))
        if metadata:
            writer.add_metadata(metadata)
        path = tmp_path / name
        writer.write(path)
        return path

    return make
