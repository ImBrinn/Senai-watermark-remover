"""Dry run, the change report, and the checks that keep a file safe.

Reports name a kind and a count. They never repeat text from the PDF.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from senai_remover.cli import find_pdfs, main
from senai_remover.core import (
    MAX_PDF_PAGES,
    REPORT_WHATS,
    PdfLimitError,
    clean_pdf,
    default_output_path,
    name_problem,
    output_name,
    report_payload,
    report_text,
    safe_error,
    scan_pdf,
)

from conftest import FIXTURE

MATHS = Path(__file__).parent / "fixtures" / "maths_sample.pdf"
WORD = "zqxvplum"
_WHAT = re.compile(rf"(?:{'|'.join(REPORT_WHATS)})(?: x[0-9]+)?")


def _fingerprint(path: Path) -> tuple:
    st = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), st.st_mtime_ns, st.st_size


def _names(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir())


def _student_pdf(make_pdf) -> Path:
    """Branding plus one made-up word in the body, the title and the metadata."""
    return make_pdf(
        (
            "BT /F1 24 Tf 72 720 Td (SenAI Maths) Tj ET\n"
            "BT /F1 12 Tf 72 680 Td (Answer: 42) Tj ET\n"
            f"BT /F1 12 Tf 72 640 Td ({WORD} is the working) Tj ET\n"
            "BT /F1 9 Tf 72 30 Td (senai.uk) Tj ET\n"
        ).encode(),
        name="homework.pdf",
        link=f"https://senai.uk/{WORD}",
        metadata={
            "/Title": f"{WORD} SenAI Maths",
            "/Author": WORD,
            "/Subject": f"see senai.uk/{WORD}",
        },
    )


def _assert_private(text: str) -> None:
    assert WORD not in text
    assert "Brinns" not in text
    assert "autocompleter" not in text
    for change_line in text.splitlines():
        # The file name and the "pages" line are not change entries.
        if change_line.startswith("page ") or change_line.startswith("document:"):
            assert WORD not in change_line


def _assert_payload(data: dict) -> None:
    assert set(data) == {"file", "pages", "changes"}
    assert isinstance(data["pages"], int)
    for change in data["changes"]:
        assert set(change) == {"page", "kind", "what"}
        assert change["kind"] in {"removed", "repaired", "title", "link", "metadata"}
        assert _WHAT.fullmatch(change["what"]), change
        if change["kind"] in {"title", "link", "metadata"}:
            assert change["page"] is None
        else:
            assert isinstance(change["page"], int) and change["page"] >= 1
        assert WORD not in json.dumps(change)


def test_scan_matches_a_real_clean_and_writes_nothing(tmp_path):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)
    before = _fingerprint(source)
    listing = _names(tmp_path)

    scanned = scan_pdf(source)
    assert scanned.output is None
    assert _fingerprint(source) == before
    assert _names(tmp_path) == listing

    out = tmp_path / "out.pdf"
    cleaned = clean_pdf(source, out)
    assert scanned.removed == cleaned.removed
    assert scanned.repaired == cleaned.repaired
    assert scanned.title == cleaned.title
    assert scanned.pages == cleaned.pages
    assert scanned.links == cleaned.links
    assert [c.as_dict() for c in scanned.changes()] == [c.as_dict() for c in cleaned.changes()]


def test_scan_of_the_maths_sample_counts_the_same_repairs(tmp_path):
    source = tmp_path / "week.pdf"
    shutil.copy(MATHS, source)
    scanned = scan_pdf(source)
    cleaned = clean_pdf(source, tmp_path / "out.pdf")
    assert [c.as_dict() for c in scanned.changes()] == [c.as_dict() for c in cleaned.changes()]
    kinds = {(c.kind, c.what) for c in cleaned.changes()}
    assert sum(c.count for c in cleaned.changes() if c.kind == "repaired" and c.what == "degree") == 4
    assert any(c.kind == "repaired" and c.what in {"dot", "arrow", "spaces"} for c in cleaned.changes())
    assert ("title", "title") in kinds
    assert any(c.kind == "removed" and c.what == "branding" for c in cleaned.changes())


def test_each_report_kind_and_null_pages_for_document_changes(make_pdf):
    source = _student_pdf(make_pdf)
    result = scan_pdf(source)
    payload = report_payload(result)
    _assert_payload(payload)
    by_kind = {}
    for change in payload["changes"]:
        by_kind.setdefault(change["kind"], []).append(change)
    assert set(by_kind) >= {"removed", "title", "link", "metadata"}
    assert all(c["page"] is None for c in by_kind["title"] + by_kind["link"] + by_kind["metadata"])
    assert all(c["page"] == 1 for c in by_kind["removed"])
    assert by_kind["link"][0]["what"] == "link"
    assert by_kind["metadata"][0]["what"].startswith("metadata")
    # The subject and the title both matched; the author did not, and is absent.
    assert by_kind["metadata"][0]["what"] == "metadata x2"
    text = report_text(result)
    _assert_private(text)
    _assert_private(json.dumps(payload))


def test_reports_from_the_command_omit_student_words(make_pdf, tmp_path, capsys):
    source = _student_pdf(make_pdf)
    before = _fingerprint(source)
    listing = _names(source.parent)
    text_path = tmp_path / "report.txt"
    json_path = tmp_path / "report.json"

    assert main([str(source), "--dry-run", "--report", "text", "--report-file", str(text_path)]) == 0
    written = text_path.read_text(encoding="utf-8")
    shown = capsys.readouterr()
    _assert_private(written)
    _assert_private(shown.out)
    _assert_private(shown.err)
    assert _fingerprint(source) == before

    assert main([str(source), "--dry-run", "--report", "json", "--report-file", str(json_path)]) == 0
    raw = json_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    _assert_payload(data)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == data
    _assert_private(raw)
    _assert_private(captured.out)
    _assert_private(captured.err)
    assert "Checked" in captured.err
    assert _fingerprint(source) == before
    # A dry run does not add a cleaned copy. The report files were requested.
    assert source.name in listing
    assert not any(p.suffix == ".pdf" and p != source for p in source.parent.glob("*.pdf"))


def test_a_real_clean_report_and_summary_omit_student_words(make_pdf, capsys):
    source = _student_pdf(make_pdf)
    report = source.parent / "out.json"
    assert main([str(source), "--report", "json", "--report-file", str(report)]) == 0
    captured = capsys.readouterr()
    _assert_private(captured.out)
    _assert_private(captured.err)
    _assert_private(report.read_text(encoding="utf-8"))
    assert (source.parent / "homework-clean.pdf").exists()
    # The human summary, with no --report, is branding words only.
    assert main([str(source), "--name", "{name}-again"]) == 0
    captured = capsys.readouterr()
    assert WORD not in captured.out and WORD not in captured.err
    assert "removed" in captured.out


def test_scan_is_remembered_until_the_file_changes(tmp_path, monkeypatch):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)
    calls = []
    real = __import__("senai_remover.core", fromlist=["_process"])._process

    def wrapped(*args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    monkeypatch.setattr("senai_remover.core._process", wrapped)
    scan_pdf(source)
    scan_pdf(source)
    assert len(calls) == 1
    os.utime(source, (source.stat().st_atime, source.stat().st_mtime + 10))
    scan_pdf(source)
    assert len(calls) == 2


def test_dry_run_leaves_the_directory_and_the_file_alone(tmp_path, capsys):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)
    before = _fingerprint(source)
    listing = _names(tmp_path)
    assert main([str(source), "--dry-run"]) == 0
    assert _fingerprint(source) == before
    assert _names(tmp_path) == listing
    out = capsys.readouterr().out
    assert "dry run" in out and "Checked 1 of 1" in out


def test_dry_run_json_on_a_plain_pdf_exits_zero(make_pdf, capsys):
    source = make_pdf(b"BT /F1 12 Tf 72 700 Td (Just a triangle) Tj ET", name="plain.pdf")
    assert main([str(source), "--dry-run", "--report", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["file"] == "plain.pdf"
    assert data["changes"] == []
    assert not (source.parent / "plain-clean.pdf").exists()


def test_a_corrupt_pdf_fails_that_file_only(tmp_path, capsys):
    good = tmp_path / "good.pdf"
    shutil.copy(FIXTURE, good)
    bad = tmp_path / "broken.pdf"
    bad.write_bytes(f"not really a pdf {WORD}".encode())
    assert main([str(bad), str(good)]) == 1
    err = capsys.readouterr().err
    assert "FAIL" in err and "broken.pdf" in err
    assert WORD not in err
    assert "not really" not in err
    assert (tmp_path / "good-clean.pdf").exists()


def test_recursion_and_other_errors_hide_page_text(tmp_path, monkeypatch, capsys):
    source = tmp_path / "bad.pdf"
    source.write_bytes(b"%PDF-1.4")
    other = tmp_path / "good.pdf"
    shutil.copy(FIXTURE, other)

    def explode(*_args, **_kwargs):
        raise RecursionError(f"nested {WORD} on page 4")

    monkeypatch.setattr("senai_remover.cli.clean_pdf", explode)
    assert main([str(source), str(other)]) == 1
    err = capsys.readouterr().err
    assert "too deeply nested" in err
    assert WORD not in err
    assert "page 4" not in err

    def boom(*_args, **_kwargs):
        raise RuntimeError(f"stream said {WORD}")

    monkeypatch.setattr("senai_remover.cli.clean_pdf", boom)
    assert main([str(source)]) == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert WORD not in err
    assert safe_error(RuntimeError(WORD)) == "Couldn't read this PDF (RuntimeError)."
    assert WORD not in safe_error(RecursionError(WORD))


def test_oversize_file_is_refused_before_it_is_read(tmp_path, monkeypatch):
    path = tmp_path / "big.pdf"
    path.write_bytes(b"%PDF-1.7 " + b"0" * 40)
    monkeypatch.setattr("senai_remover.core.MAX_PDF_BYTES", 16)
    reads = []
    real = Path.read_bytes

    def wrapped(self):
        reads.append(self)
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", wrapped)
    with pytest.raises(PdfLimitError, match="100 MB"):
        scan_pdf(path)
    assert reads == []
    assert WORD not in str(PdfLimitError("left alone"))


def test_too_many_pages_are_refused_before_the_content_is_parsed(tmp_path, monkeypatch):
    path = tmp_path / "long.pdf"
    writer = PdfWriter()
    for _ in range(MAX_PDF_PAGES + 1):
        writer.add_blank_page(20, 20)
    writer.write(path)

    def parsed(*_args, **_kwargs):
        raise AssertionError("content was parsed")

    monkeypatch.setattr("senai_remover.core._strip_operations", parsed)
    monkeypatch.setattr(
        "senai_remover.core.PdfWriter",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("the document was cloned")),
    )
    with pytest.raises(PdfLimitError, match="500 pages"):
        scan_pdf(path)
    assert not (tmp_path / "long-clean.pdf").exists()


def test_importing_the_cli_does_not_load_qt():
    script = (
        "import senai_remover.cli, sys\n"
        "assert not any(name.startswith('PySide6') for name in sys.modules)\n"
    )
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_pypdf_is_a_patched_release():
    from importlib.metadata import version

    numbers = tuple(int(part) for part in version("pypdf").split(".")[:3])
    assert numbers >= (6, 21, 4)


def test_find_pdfs_does_not_follow_a_symlinked_directory(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    shutil.copy(FIXTURE, real / "a.pdf")
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    assert list(find_pdfs([linked])) == []
    assert list(find_pdfs([real])) == [real / "a.pdf"]

    outside = tmp_path / "outside.pdf"
    shutil.copy(FIXTURE, outside)
    alias = real / "alias.pdf"
    alias.symlink_to(outside)
    found = list(find_pdfs([real]))
    assert alias not in found
    assert real / "a.pdf" in found
    # Named on its own, a symlink to a file is the path the person asked for.
    assert list(find_pdfs([alias])) == [alias]


def test_output_that_is_the_original_is_refused(tmp_path):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)
    before = _fingerprint(source)

    with pytest.raises(ValueError, match="overwrite"):
        clean_pdf(source, source)
    link = tmp_path / "link.pdf"
    link.symlink_to(source)
    with pytest.raises(ValueError, match="overwrite"):
        clean_pdf(source, link)
    hard = tmp_path / "hard.pdf"
    os.link(source, hard)
    with pytest.raises(ValueError, match="overwrite"):
        clean_pdf(source, hard)
    assert _fingerprint(source) == before

    cleaned = clean_pdf(source, source, overwrite=True)
    assert cleaned.output == source.resolve()
    assert "senai" not in "".join(p.extract_text() or "" for p in PdfReader(source).pages).lower()


def test_existing_output_gets_a_numbered_name_and_no_temp_file(tmp_path):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)
    first = clean_pdf(source, tmp_path / "homework-clean.pdf")
    assert first.output.name == "homework-clean.pdf"
    second = clean_pdf(source, tmp_path / "homework-clean.pdf")
    assert second.output.name == "homework-clean (2).pdf"
    assert first.output.read_bytes()  # the first copy was not truncated
    assert not list(tmp_path.glob(".senai-*"))
    assert not list(tmp_path.glob("*.part"))


def test_a_failed_write_removes_its_temp_file(tmp_path, monkeypatch):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)

    def boom(self, stream):
        raise RuntimeError(WORD)

    monkeypatch.setattr("senai_remover.core.PdfWriter.write", boom)
    with pytest.raises(RuntimeError):
        clean_pdf(source, tmp_path / "out.pdf")
    assert not list(tmp_path.glob(".senai-*"))
    assert not (tmp_path / "out.pdf").exists()
    assert _fingerprint(source)


def test_output_names_cannot_leave_the_folder(tmp_path):
    assert name_problem("..{name}") == "File names can't contain .."
    assert name_problem("{name}/../x") == "File names can't contain /"
    assert name_problem("../{name}") == "File names can't contain /"
    weird = tmp_path / "..homework.pdf"
    weird.write_bytes(b"%PDF")
    named = output_name(weird)
    assert "/" not in named and "\\" not in named and ".." not in named
    folder = tmp_path / "out"
    folder.mkdir()
    target = default_output_path(weird, folder)
    assert target.parent == folder.resolve()
    assert "/" not in target.name and "\\" not in target.name and ".." not in target.name

    escaped = tmp_path / "out" / ".." / "elsewhere.pdf"
    with pytest.raises(ValueError, match="isn't allowed"):
        clean_pdf(weird, escaped)


def test_non_regular_files_in_a_folder_are_skipped(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    shutil.copy(FIXTURE, folder / "a.pdf")
    fifo = folder / "pipe.pdf"
    os.mkfifo(fifo)
    assert stat.S_ISFIFO(fifo.lstat().st_mode)
    assert list(find_pdfs([folder])) == [folder / "a.pdf"]
