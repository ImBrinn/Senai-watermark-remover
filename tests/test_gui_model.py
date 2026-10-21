import errno
import shutil

import pytest

pytest.importorskip("PySide6")  # the gui package needs it, even for its Qt-free model

from pypdf.errors import FileNotDecryptedError, PdfStreamError  # noqa: E402

from senai_remover.gui.model import (  # noqa: E402
    AddResult,
    FileJob,
    RunSummary,
    Session,
    Status,
    friendly_error,
    plural,
    run_job,
    summarize,
)

from conftest import FIXTURE  # noqa: E402


@pytest.fixture
def pdfs(tmp_path):
    folder = tmp_path / "homework"
    folder.mkdir()
    paths = []
    for name in ("a.pdf", "b.PDF", "a_clean.pdf"):
        shutil.copy(FIXTURE, folder / name)
        paths.append(folder / name)
    (folder / "notes.txt").write_text("not a pdf")
    return folder, paths


def test_add_files_folders_and_skips(pdfs, tmp_path):
    folder, (a, b, earlier) = pdfs
    session = Session()

    result = session.add([folder])  # folder scan skips earlier _clean output
    assert (result.added, result.duplicates, result.ignored) == (2, 0, 0)
    result = session.add([a, folder / "notes.txt", tmp_path / "missing.pdf"])
    assert (result.added, result.duplicates, result.ignored) == (0, 1, 2)
    assert result.text() == "2 items skipped: only PDF files can be added; 1 PDF already in the list"
    assert [job.name for job in session.jobs] == ["a.pdf", "b.PDF"]

    assert session.add([earlier]).added == 1  # named explicitly, it's added


def test_remove_and_clear(pdfs):
    folder, _ = pdfs
    session = Session()
    session.add([folder])
    assert session.remove([0, 7]) == [0]
    assert [job.name for job in session.jobs] == ["b.PDF"]
    session.clear()
    assert session.jobs == []


def test_plan_never_overwrites_originals_or_each_other(tmp_path):
    one, two, out = tmp_path / "one", tmp_path / "two", tmp_path / "out"
    for folder in (one, two, out):
        folder.mkdir()
    for folder in (one, two):
        shutil.copy(FIXTURE, folder / "hw.pdf")
    shutil.copy(FIXTURE, out / "hw_clean.pdf")  # a source sitting in the output folder
    session = Session()
    session.add([one / "hw.pdf", two / "hw.pdf", out / "hw_clean.pdf"])

    assert [t.name for _, t in session.plan()] == ["hw_clean.pdf", "hw_clean.pdf", "hw_clean_clean.pdf"]
    session.output_dir = out
    targets = [t for _, t in session.plan()]
    assert [t.name for t in targets] == ["hw_clean (2).pdf", "hw_clean (3).pdf", "hw_clean_clean.pdf"]
    assert all(t.parent == out for t in targets)


def test_run_job_outcomes(tmp_path):
    good = tmp_path / "good.pdf"
    shutil.copy(FIXTURE, good)
    job = FileJob(good)
    run_job(job, tmp_path / "good_clean.pdf")
    assert job.status is Status.CLEANED and job.removed == 4 and job.output.exists()
    assert job.status_text() == ("Cleaned", "4 removed")

    again = FileJob(job.output)
    run_job(again, tmp_path / "again.pdf")
    assert again.status is Status.UNCHANGED and again.status_text()[0] == "Nothing to remove"
    assert "unchanged copy" in again.message

    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not really a pdf")
    bad = FileJob(broken)
    run_job(bad, tmp_path / "broken_clean.pdf")
    assert bad.status is Status.FAILED and bad.output is None
    assert bad.message == "This file isn't a readable PDF."
    assert "PdfStreamError" in bad.detail

    summary = summarize([job, again, bad])
    assert (summary.cleaned, summary.unchanged, summary.failed) == (1, 1, 1)
    assert summary.text() == "1 PDF cleaned, 1 had nothing to remove, 1 couldn't be cleaned"
    assert summary.outputs == [job.output, again.output]


@pytest.mark.parametrize("exc, expected", [
    (PermissionError(errno.EACCES, "denied", "OUT"), "Couldn't save out_clean.pdf. If it's open in a PDF viewer"),
    (PermissionError(errno.EACCES, "denied", "SRC"), "Couldn't open this file. If it's open in another app"),
    (FileNotFoundError(errno.ENOENT, "gone", "SRC"), "This file has been moved or deleted."),
    (FileNotFoundError(errno.ENOENT, "gone", "OUT"), "Couldn't save to that folder."),
    (OSError(errno.ENOSPC, "full"), "There isn't enough disk space"),
    (PdfStreamError("Stream has ended unexpectedly"), "This file isn't a readable PDF."),
    (FileNotDecryptedError("File has not been decrypted"), "This PDF is password protected"),
    (ValueError("x.pdf is password protected"), "This PDF is password protected"),
    (KeyError("/Root"), "Couldn't clean this file."),
])
def test_friendly_errors(tmp_path, exc, expected):
    source, target = tmp_path / "in.pdf", tmp_path / "out_clean.pdf"
    if getattr(exc, "filename", None) == "OUT":
        exc.filename = str(target)
    elif getattr(exc, "filename", None) == "SRC":
        exc.filename = str(source)
    message, detail = friendly_error(exc, source, target)
    assert message.startswith(expected)
    assert type(exc).__name__ in detail


def test_wording():
    assert plural(1, "PDF") == "1 PDF" and plural(3, "PDF") == "3 PDFs"
    assert RunSummary(cleaned=3).text() == "3 PDFs cleaned"
    assert RunSummary(failed=1).text() == "1 PDF couldn't be cleaned"
    assert RunSummary().text() == "Nothing to clean"
    assert AddResult(added=2).text() == ""
