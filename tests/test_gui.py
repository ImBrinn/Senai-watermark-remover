"""Drives every theme offscreen: adding files, drag and drop, cleaning,
shortcuts, switching themes, the settings bar, and colour contrast."""

import os
import shutil
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from pypdf import PdfReader  # noqa: E402
from PySide6.QtCore import QEventLoop, QMimeData, QPoint, QPointF, Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from senai_remover.gui.app import Shell, configure  # noqa: E402
from senai_remover.gui.controller import Controller  # noqa: E402
from senai_remover.gui.settings import Settings  # noqa: E402
from senai_remover.gui.designs import DESIGNS  # noqa: E402
from senai_remover.gui.model import Status  # noqa: E402
from senai_remover.gui.theme import Prefs, contrast, mix  # noqa: E402

from conftest import FIXTURE  # noqa: E402

DESIGN_IDS = [cls.NAME for cls in DESIGNS]


@pytest.fixture(scope="module")
def app():
    return configure(QApplication.instance() or QApplication([]))


@pytest.fixture
def shell(app, monkeypatch, tmp_path):
    monkeypatch.setenv("SENAI_APPEARANCE", "light")
    monkeypatch.setenv("SENAI_SETTINGS_FILE", str(tmp_path / "settings.ini"))
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
        assert job.output == job.source.with_name(job.source.stem + "-clean.pdf")
        assert "senai" not in text_of(job.output)
        assert "brinns autocompleter" in text_of(job.output)
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
    assert sorted(p.name for p in out.iterdir()) == ["Algebra-clean.pdf", "Angles-clean.pdf"]
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


# Settings bar ------------------------------------------------------------------


def test_theme_choice_is_saved(shell, monkeypatch, tmp_path):
    s = shell(0)
    assert s.window.act_settings.shortcuts() == [QKeySequence("Ctrl+,")]
    s.window.act_designs[2].trigger()
    assert isinstance(s.window, DESIGNS[2])
    assert Settings().theme == DESIGNS[2].ID
    again = Shell(QApplication.instance())  # a later launch starts on the saved theme
    assert again.index == 2


def test_settings_bar_switches_theme_and_stays_open(shell, pdfs):
    s = shell(0)
    s.window.add_paths(pdfs)
    s.window.act_settings.trigger()
    panel = s.window.settings_panel
    assert panel.is_open and len(panel.cards.buttons()) == len(DESIGNS)
    assert panel.checked(panel.cards) is panel.cards.button(0)
    panel.cards.button(3).click()
    settle()
    assert isinstance(s.window, DESIGNS[3])
    new_panel = s.window.settings_panel
    assert s.window.settings_open and new_panel.checked(new_panel.cards) is new_panel.cards.button(3)
    assert QApplication.focusWidget() is new_panel.cards.button(3)  # focus follows the choice
    assert s.window.list_view.model().rowCount() == 2
    s.window.settings_panel.close_panel()
    assert not s.window.settings_open


def test_appearance_setting(shell, monkeypatch):
    monkeypatch.delenv("SENAI_APPEARANCE")
    s = shell(1)
    s.window.open_settings(animate=False)
    dark = [b for b in s.window.settings_panel.appearance.buttons() if b.text() == "Dark"][0]
    dark.click()
    settle()
    assert Settings().appearance == "dark"
    assert s.window.prefs.dark and s.window.settings_open
    light = [b for b in s.window.settings_panel.appearance.buttons() if b.text() == "Light"][0]
    light.click()
    settle()
    assert Settings().appearance == "light" and not s.window.prefs.dark


def test_escape_closes_settings(shell):
    from PySide6.QtTest import QTest

    s = shell(0)
    s.window.open_settings(animate=False)
    s.window.activateWindow()
    card = s.window.settings_panel.checked(s.window.settings_panel.cards)
    card.setFocus()
    settle()
    QTest.keyClick(card, Qt.Key_Escape)
    settle()
    assert not s.window.settings_open


def test_settings_locked_while_cleaning(shell, monkeypatch):
    s = shell(0)
    s.window.open_settings(animate=False)
    panel = s.window.settings_panel
    monkeypatch.setattr(Controller, "running", property(lambda self: True))
    panel._sync_enabled()
    assert not any(b.isEnabled() for b in panel.cards.buttons() + panel.appearance.buttons())
    assert not panel.name_field.isEnabled()
    assert not panel.busy_note.isHidden()


@pytest.mark.parametrize("index", range(len(DESIGNS)), ids=DESIGN_IDS)
def test_every_theme_shows_a_settings_button(shell, index):
    window = shell(index).window
    gears = [b for b in window.findChildren(QToolButton) if b.accessibleName() == "Settings" and b.isVisible()]
    assert len(gears) == 1
    gears[0].click()
    assert window.settings_open


@pytest.mark.parametrize("cls", DESIGNS, ids=DESIGN_IDS)
@pytest.mark.parametrize("prefs", [Prefs(), Prefs(dark=True), Prefs(high_contrast=True),
                                   Prefs(dark=True, high_contrast=True)],
                         ids=["light", "dark", "light-hc", "dark-hc"])
def test_settings_bar_contrast(cls, prefs):
    t = sys.modules[cls.__module__].tokens(prefs)
    card_hover = mix(t["label"], t["surface"], 0.06)
    field = mix(t["label"], t["surface"], 0.04)
    pairs = [("label", t["label"], t["surface"]), ("secondary", t["secondary"], t["surface"]),
             ("label on card", t["label"], card_hover), ("secondary on card", t["secondary"], card_hover),
             ("on_accent", t["on_accent"], t["accent"]), ("name field", t["label"], field),
             ("reset button", t["accent_text"], t["surface"]), ("name error", t["danger"], t["surface"])]
    failures = [f"{name}: {contrast(fg, bg):.2f}" for name, fg, bg in pairs if contrast(fg, bg) < 4.5]
    assert not failures, failures


def test_keyboard_stays_in_settings_bar(shell):
    from PySide6.QtTest import QTest

    s = shell(0)
    s.window.open_settings(animate=False)
    s.window.activateWindow()
    panel = s.window.settings_panel
    chain = panel.focus_chain()
    # close, every card, three appearance buttons, the name field (Reset only shows once it's changed)
    assert len(chain) == 1 + len(DESIGNS) + 3 + 1
    chain[0].setFocus()
    settle()
    seen = []
    for _ in range(len(chain) + 1):
        QTest.keyClick(QApplication.focusWidget(), Qt.Key_Tab)
        seen.append(QApplication.focusWidget())
    assert seen[:-1] == chain[1:] + chain[:1] and seen[-1] is chain[1]  # wraps, never leaves
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_Backtab)
    assert QApplication.focusWidget() is chain[0]

    fluent_card = panel.cards.button(3)
    fluent_card.setFocus()
    QTest.keyClick(fluent_card, Qt.Key_Space)
    settle()
    assert isinstance(s.window, DESIGNS[3]) and s.window.settings_open


def test_output_name_setting(shell, pdfs):
    from PySide6.QtTest import QTest

    s = shell(3)  # Fluent says what copies are called under its drop area
    window = s.window
    caption = [label for label, _ in window._naming][0]
    assert "name-clean.pdf" in caption.text()
    window.open_settings(animate=False)
    panel = window.settings_panel
    assert panel.name_field.text() == "{name}-clean"
    assert panel.name_reset.isHidden()

    panel.name_field.clear()
    QTest.keyClicks(panel.name_field, "Brinn - {name}")
    assert Settings().output_name == "Brinn - {name}"
    assert s.controller.name_template == "Brinn - {name}"
    assert "Brinn - name.pdf" in caption.text()  # the theme's wording follows
    assert panel.name_example.text() == "For example: Brinn - Algebra homework.pdf"
    assert not panel.name_reset.isHidden()
    assert panel.name_reset in panel.focus_chain()

    panel.name_field.clear()
    QTest.keyClicks(panel.name_field, "cleaned?")  # no {name}, and a ? Windows won't allow
    assert not panel.name_error.isHidden() and panel.name_example.isHidden()
    assert panel.name_error.text() == "Put {name} where the original file name should go."
    assert Settings().output_name == "Brinn - {name}"  # the last good name is kept
    assert panel.name_field.property("error") is True

    window.add_paths(pdfs)
    run_and_wait(s.controller)
    assert pdfs[0].with_name("Brinn - Algebra.pdf").exists()

    panel.name_reset.click()
    assert panel.name_field.text() == "{name}-clean" and Settings().output_name == "{name}-clean"
    assert panel.name_error.isHidden() and panel.name_reset.isHidden()


def test_saved_output_name_is_used_at_launch(shell, tmp_path):
    Settings().output_name = "{name} (clean)"
    s = shell(0)
    assert s.controller.name_template == "{name} (clean)"
    assert s.controller.example_name() == "name (clean).pdf"
