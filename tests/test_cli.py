import shutil

from pypdf import PdfReader

from senai_remover.cli import main

from conftest import FIXTURE


def has_branding(path):
    return "senai" in "".join(p.extract_text() for p in PdfReader(path).pages).lower()


def test_single_file_saved_next_to_original(tmp_path, capsys):
    source = tmp_path / "homework.pdf"
    shutil.copy(FIXTURE, source)

    assert main([str(source)]) == 0
    assert not has_branding(tmp_path / "homework_clean.pdf")
    assert has_branding(source)
    assert "removed: SenAI Maths, senai.uk x3" in capsys.readouterr().out


def test_folder_skips_earlier_output(tmp_path, capsys):
    for name in ("a.pdf", "b.PDF", "a_clean.pdf"):
        shutil.copy(FIXTURE, tmp_path / name)
    (tmp_path / "notes.txt").write_text("not a pdf")

    assert main([str(tmp_path)]) == 0
    assert "Cleaned 2 of 2 file(s)." in capsys.readouterr().out
    assert sorted(p.name for p in tmp_path.glob("*_clean*")) == ["a_clean.pdf", "b_clean.PDF"]


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
    assert not (tmp_path / "homework_clean.pdf").exists()


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
    assert not has_branding(tmp_path / "good_clean.pdf")
