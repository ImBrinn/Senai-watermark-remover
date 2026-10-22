import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

from senai_remover.cli import main

from conftest import FIXTURE

MATHS = Path(__file__).parent / "fixtures" / "maths_sample.pdf"


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


def test_bad_title_is_refused(tmp_path, capsys):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)
    with pytest.raises(SystemExit):
        main([str(source), "--title", "x" * 51])
    assert "That title is too long" in capsys.readouterr().err
    assert not (tmp_path / "homework-clean.pdf").exists()


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


def test_repairs_are_described_in_words(tmp_path, capsys):
    source = tmp_path / "week7.pdf"
    shutil.copy(MATHS, source)
    assert main([str(source)]) == 0
    out = capsys.readouterr().out
    assert "fixed 4 degree signs, 1 multiplication dot, 1 arrow, 2 sentences respaced" in out


def test_output_survives_a_windows_console(tmp_path):
    # Windows consoles and pipes are often Windows-1252, with no "⟹" and no
    # emoji: printing must not crash, so every file still gets cleaned.
    for name in ("week7.pdf", "notes 📐.pdf"):
        shutil.copy(MATHS, tmp_path / name)
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    done = subprocess.run([sys.executable, "-m", "senai_remover.cli", str(tmp_path)],
                          capture_output=True, env=env, cwd=Path(__file__).parent.parent)
    assert done.returncode == 0, done.stderr.decode("cp1252", "replace")
    assert b"Cleaned 2 of 2 file(s)." in done.stdout
    assert (tmp_path / "notes 📐-clean.pdf").exists()
