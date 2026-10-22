import shutil

import pytest
from pypdf import PdfReader

from senai_remover.cli import main

from conftest import FIXTURE


def has_branding(path):
    return "senai" in "".join(p.extract_text() for p in PdfReader(path).pages).lower()


def test_single_file_saved_next_to_original(tmp_path, capsys):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)

    assert main([str(source)]) == 0
    assert not has_branding(tmp_path / "homework-clean.pdf")
    assert has_branding(source)
    out = capsys.readouterr().out
    assert "removed SenAI Maths, senai.uk x3; title: Brinns autocompleter" in out


def test_folder_skips_earlier_output(tmp_path, capsys):
    # Copies named the new way and the old way (before 2.1.1) are both skipped.
    for name in ("a.pdf", "b.PDF", "a-clean.pdf", "old_clean.pdf"):
        shutil.copy(FIXTURE, tmp_path / name)
    (tmp_path / "notes.txt").write_text("not a pdf")

    assert main([str(tmp_path)]) == 0
    assert "Cleaned 2 of 2 file(s)." in capsys.readouterr().out
    assert sorted(p.name for p in tmp_path.glob("*-clean*")) == ["a-clean.pdf", "b-clean.PDF"]


def test_custom_name_and_title(tmp_path, capsys):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)

    assert main([str(source), "--name", "Brinn - {name}", "--title", "My answers"]) == 0
    out = tmp_path / "Brinn - homework.pdf"
    text = PdfReader(out).pages[0].extract_text()
    assert "My answers" in text and "Brinns" not in text
    assert main([str(source), "--suffix", "_x", "--title", ""]) == 0
    assert "My answers" not in PdfReader(tmp_path / "homework_x.pdf").pages[0].extract_text()


def test_bad_name_is_refused(tmp_path, capsys):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)
    with pytest.raises(SystemExit):
        main([str(source), "--name", "cleaned"])
    assert "Put {name} where the original file name should go" in capsys.readouterr().err


def test_output_dir_keeps_names(tmp_path):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)

    assert main([str(source), "-o", str(tmp_path / "clean")]) == 0
    assert not has_branding(tmp_path / "clean" / "homework.pdf")


def test_in_place(tmp_path):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)

    assert main([str(source), "--in-place"]) == 0
    assert not has_branding(source)
    assert not (tmp_path / "homework-clean.pdf").exists()


def test_refuses_to_overwrite_without_in_place(tmp_path, capsys):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)

    assert main([str(source), "-o", str(tmp_path)]) == 1
    assert "would overwrite the original" in capsys.readouterr().err
    assert has_branding(source)


def test_bad_files_are_reported_and_others_still_processed(tmp_path, capsys):
    good = tmp_path / "good.pdf"
    shutil.copy(FIXTURE, good)
    (tmp_path / "broken.pdf").write_bytes(b"not really a pdf")

    assert main([str(tmp_path / "broken.pdf"), str(tmp_path / "missing.pdf"), str(good)]) == 1
    err = capsys.readouterr().err
    assert "FAIL" in err and "broken.pdf" in err and "missing.pdf" in err
    assert not has_branding(tmp_path / "good-clean.pdf")
