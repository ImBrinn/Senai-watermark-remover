"""Drives every design prototype offscreen: adding files, drag and drop,
cleaning, shortcuts, switching designs, and colour contrast."""

import os
import shutil
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from pypdf import PdfReader  # noqa: E402
from PySide6.QtCore import QEventLoop, QMimeData, QPoint, QPointF, Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from senai_remover.gui.app import Shell, configure  # noqa: E402
from senai_remover.gui.designs import DESIGNS  # noqa: E402
from senai_remover.gui.model import Status  # noqa: E402
from senai_remover.gui.theme import Prefs, contrast  # noqa: E402

from conftest import FIXTURE  # noqa: E402

DESIGN_IDS = [cls.NAME for cls in DESIGNS]


@pytest.fixture(scope="module")
def app():
    return configure(QApplication.instance() or QApplication([]))


@pytest.fixture
def shell(app, monkeypatch):
    monkeypatch.setenv("SENAI_APPEARANCE", "light")
    shells = []

    def make(index):
        s = Shell(app)
        s.show(index)
        shells.append(s)
        return s

    yield make
    for s in shells:
        if s.window is not None:
            s.window.close()
    settle()


@pytest.fixture
def pdfs(tmp_path):
    folder = tmp_path / "Homework"
    folder.mkdir()
    paths = []
    for name in ("Algebra.pdf", "Angles.pdf"):
        shutil.copy(FIXTURE, folder / name)
        paths.append(folder / name)
    return paths


def settle(ms=30):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_and_wait(controller):
    loop = QEventLoop()
    controller.finished.connect(lambda *_: loop.quit())
    QTimer.singleShot(20000, loop.quit)  # never hang the test run
    controller.run()
    loop.exec()


def text_of(path):
    return "".join(page.extract_text() for page in PdfReader(path).pages).lower()


def drop(window, paths, kind=QDropEvent):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    if kind is QDragEnterEvent:
        event = QDragEnterEvent(QPoint(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        window.dragEnterEvent(event)
    else:
        event = QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        window.dropEvent(event)
    return event


@pytest.mark.parametrize("index", range(len(DESIGNS)), ids=DESIGN_IDS)
def test_add_clean_and_report(shell, pdfs, index):
    s = shell(index)
    window = s.window
    assert not window.act_run.isEnabled()  # nothing to clean yet

    window.add_paths(pdfs)
    assert window.list_view.model().rowCount() == 2
    assert window.act_run.isEnabled() and not window.act_show.isEnabled()

    run_and_wait(s.controller)
    settle()
    jobs = s.controller.jobs
    assert [job.status for job in jobs] == [Status.CLEANED, Status.CLEANED]
    for job in jobs:
        assert job.output == job.source.with_name(job.source.stem + "_clean.pdf")
        assert "senai" not in text_of(job.output)
    assert s.controller.last_summary.text() == "2 PDFs cleaned"
    assert window.act_show.isEnabled() and window.act_run.isEnabled()


@pytest.mark.parametrize("index", range(len(DESIGNS)), ids=DESIGN_IDS)
def test_drag_and_drop(shell, pdfs, tmp_path, index):
    window = shell(index).window
    note = tmp_path / "notes.txt"
    note.write_text("hi")

    assert not drop(window, [note], QDragEnterEvent).isAccepted()  # not a PDF: refused
    assert drop(window, [pdfs[0], note], QDragEnterEvent).isAccepted()
    drop(window, [pdfs[0].parent])  # a folder adds the PDFs in it
    assert window.list_view.model().rowCount() == 2


@pytest.mark.parametrize("index", range(len(DESIGNS)), ids=DESIGN_IDS)
def test_shortcuts_and_list_commands(shell, pdfs, index):
    window = shell(index).window
    shortcuts = {
        window.act_add_files: QKeySequence(QKeySequence.Open),
        window.act_add_folder: QKeySequence("Ctrl+Shift+O"),
        window.act_remove: QKeySequence(QKeySequence.Delete),
        window.act_run: QKeySequence("Ctrl+Return"),
    }
    for action, key in shortcuts.items():
        assert key in action.shortcuts(), action.text()
    for n, action in enumerate(window.act_designs, start=1):
        assert QKeySequence(f"Ctrl+{n}") in action.shortcuts()

    window.add_paths(pdfs)
    view = window.list_view
    view.selectionModel().select(view.model().index(0, 0), view.selectionModel().SelectionFlag.ClearAndSelect)
    assert window.act_remove.isEnabled()
    window.act_remove.trigger()
    assert [job.name for job in window.controller.jobs] == ["Angles.pdf"]
    window.act_clear.trigger()
    assert window.controller.jobs == []


def test_switching_designs_keeps_the_list_and_results(shell, pdfs):
    s = shell(0)
    s.window.add_paths(pdfs)
    run_and_wait(s.controller)
    for index in range(1, len(DESIGNS)):
        s.window.act_designs[index].trigger()
        settle()
        assert isinstance(s.window, DESIGNS[index])
        assert s.window.list_view.model().rowCount() == 2
        assert all(job.status is Status.CLEANED for job in s.controller.jobs)
        assert s.controller.last_summary.text() == "2 PDFs cleaned"


def test_output_folder(shell, pdfs, tmp_path):
    s = shell(0)
    s.window.add_paths(pdfs)
    out = tmp_path / "cleaned"
    out.mkdir()
    s.controller.set_output_dir(out)
    run_and_wait(s.controller)
    assert sorted(p.name for p in out.iterdir()) == ["Algebra_clean.pdf", "Angles_clean.pdf"]
    assert all(p.exists() for p in pdfs)  # originals untouched


@pytest.mark.parametrize("cls", DESIGNS, ids=DESIGN_IDS)
@pytest.mark.parametrize("prefs", [Prefs(), Prefs(dark=True), Prefs(high_contrast=True),
                                   Prefs(dark=True, high_contrast=True)],
                         ids=["light", "dark", "light-hc", "dark-hc"])
def test_text_contrast(cls, prefs):
    module = sys.modules[cls.__module__]
    t = module.tokens(prefs)
    failures = []
    for fg, bg, minimum in module.CONTRAST:
        ratio = contrast(t[fg], t[bg])
        if ratio < minimum:
            failures.append(f"{fg} on {bg}: {ratio:.2f} < {minimum}")
    assert not failures, failures


@pytest.mark.parametrize("index", range(len(DESIGNS)), ids=DESIGN_IDS)
@pytest.mark.parametrize("appearance", ["light", "dark"])
def test_every_design_builds_in_both_appearances(shell, monkeypatch, pdfs, index, appearance):
    monkeypatch.setenv("SENAI_APPEARANCE", appearance)
    monkeypatch.setenv("SENAI_REDUCE_TRANSPARENCY", "1")
    window = shell(index).window
    window.add_paths(pdfs)
    window.notify("A message", "warning")
    settle()
    assert not window.grab().isNull()
