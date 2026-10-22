"""Behaviour every design shares: commands and shortcuts, drag and drop,
file dialogs, the context menu, and staying in sync with the controller.
Each design only builds its widgets and decides how things look."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QItemSelectionModel, QPoint, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QMessageBox, QToolButton

from ..controller import Controller
from ..model import RunSummary
from ..theme import Prefs, icon
from ..widgets import FileListView, Labels, bind, icon_button

PDF_FILTER = "PDF files (*.pdf)"


class BaseWindow(QMainWindow):
    ID = ""  # saved in settings, e.g. "apple-classic"
    NAME = ""  # shown in Settings and the Theme menu, e.g. "Apple Classic"
    DESCRIPTION = ""  # one line under the name in Settings
    TITLE_CASE = True
    DEFAULT_SIZE = (760, 560)
    MIN_SIZE = (560, 420)

    def __init__(self, controller: Controller, prefs: Prefs, shell, index: int):
        """``shell`` is the app's Shell: it owns the saved settings and
        swaps the window when the theme or appearance changes."""
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.controller = controller
        self.prefs = prefs
        self.shell = shell
        self.labels = Labels(self.TITLE_CASE)
        self.design_index = index
        self.list_view: Optional[FileListView] = None
        self.settings_panel = None
        self._naming: list = []  # (label, text) that mention what copies are called
        self.setWindowTitle("SenAI Watermark Remover")
        self.resize(*self.DEFAULT_SIZE)
        self.setMinimumSize(*self.MIN_SIZE)
        self.setAcceptDrops(True)
        self._make_actions([design.NAME for design in shell.designs])
        self.build()
        assert self.list_view is not None, "a design must create self.list_view"
        self.list_view.customContextMenuRequested.connect(self._context_menu)
        self.list_view.doubleClicked.connect(lambda index: self.controller.open_output(index.row()))
        self.list_view.selectionModel().selectionChanged.connect(lambda *_: self.refresh())

        model = controller.model
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset, model.dataChanged):
            signal.connect(self.refresh)
        controller.running_changed.connect(self._running_changed)
        controller.progress.connect(self.on_progress)
        controller.finished.connect(self.on_finished)
        controller.output_changed.connect(self.refresh)
        controller.name_changed.connect(self._update_naming)
        self.refresh()
        if controller.last_summary is not None:  # e.g. after switching designs
            self.on_finished(controller.last_summary)

    # Hooks for designs ---------------------------------------------------------

    def build(self) -> None:
        raise NotImplementedError

    def naming(self, label, text: str):
        """Keep ``label`` reading ``text``, with {example} replaced by what
        cleaned copies are called (``name-clean.pdf`` unless changed)."""
        self._naming.append((label, text))
        label.setText(text.replace("{example}", self.controller.example_name()))
        return label

    def _update_naming(self) -> None:
        for label, text in self._naming:
            label.setText(text.replace("{example}", self.controller.example_name()))

    def update_view(self) -> None:
        """Called after anything changes; show the right page and counts."""

    def on_progress(self, done: int, total: int) -> None:
        pass

    def on_finished(self, summary: RunSummary) -> None:
        pass

    def notify(self, text: str, kind: str = "info") -> None:
        """Show a short message (``info``, ``success``, ``warning`` or ``error``)."""

    def set_drop_active(self, active: bool) -> None:
        """Highlight the window while PDFs are dragged over it."""

    def tooltip_style(self) -> str:
        """Tooltips are separate windows, styled from the application."""
        t = self.t
        return (f"QToolTip {{ background: {t['surface']}; color: {t['label']}; "
                f"border: 1px solid {t['border']}; padding: 4px 6px; font-family: Inter; font-size: 12px; }}")

    # Commands ------------------------------------------------------------------

    def _make_actions(self, designs: list[str]) -> None:
        L = self.labels

        def action(text, slot, shortcuts=(), tip=""):
            act = QAction(text, self)
            act.triggered.connect(slot)
            if shortcuts:
                act.setShortcuts([QKeySequence(s) for s in shortcuts])
            shortcut = act.shortcut().toString(QKeySequence.NativeText).replace("Return", "Enter")
            act.setToolTip(f"{tip or text.rstrip('…')} ({shortcut})" if shortcut else (tip or text.rstrip("…")))
            self.addAction(act)  # shortcuts work even without a menu bar
            return act

        self.act_add_files = action(L.add_files, self.pick_files, [QKeySequence.Open])
        self.act_add_folder = action(L.add_folder, self.pick_folder, ["Ctrl+Shift+O"])
        self.act_remove = action(L.remove, self.remove_selected, [QKeySequence.Delete])
        self.act_clear = action(L.clear, self.controller.clear)
        self.act_run = action(L.run, self.controller.run, ["Ctrl+Return", "Ctrl+Enter"])
        self.act_show = action(L.show, lambda: self.controller.show_outputs(self.list_view.selected_rows()))
        self.act_open_pdf = action(L.open_pdf, self._open_selected)
        self.act_settings = action(L.settings, self.open_settings, ["Ctrl+,"], "Settings")
        self.act_exit = action(L.exit, self.close, ["Ctrl+Q"])
        self.act_about = action(L.about, self._about)

        self.design_group = QActionGroup(self)
        self.act_designs = []
        for i, name in enumerate(designs):
            act = action(name, lambda _=False, i=i: self.shell.switch(i), [f"Ctrl+{i + 1}"])
            act.setCheckable(True)
            act.setChecked(i == self.design_index)
            self.design_group.addAction(act)
            self.act_designs.append(act)

    def fill_menu_bar(self) -> None:
        """A standard menu bar holding every command."""
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")
        file_menu.addActions([self.act_add_files, self.act_add_folder])
        file_menu.addSeparator()
        file_menu.addAction(self.act_run)
        file_menu.addSeparator()
        file_menu.addActions([self.act_open_pdf, self.act_show])
        file_menu.addSeparator()
        file_menu.addAction(self.act_settings)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)
        edit_menu = bar.addMenu("&Edit")
        edit_menu.addActions([self.act_remove, self.act_clear])
        view_menu = bar.addMenu("&View")
        theme_menu = view_menu.addMenu("&Theme")
        theme_menu.addActions(self.act_designs)
        view_menu.addSeparator()
        view_menu.addAction(self.act_settings)
        help_menu = bar.addMenu("&Help")
        help_menu.addAction(self.act_about)

    def more_menu_items(self, menu: QMenu) -> None:
        """The Theme submenu and Settings, for designs with a More menu."""
        themes = menu.addMenu("Theme")
        themes.addActions(self.act_designs)
        menu.addAction(self.act_settings)

    def settings_button(self, color: str, size: int = 28) -> "QToolButton":
        """A gear button that opens Settings."""
        button = icon_button(icon("settings", color, 18, 1.75), self.act_settings.toolTip(), size)
        button.setAccessibleName("Settings")
        bind(button, self.act_settings)
        return button

    def open_settings(self, animate: bool = True, focus: str = "theme") -> None:
        from ..settings_panel import SettingsPanel

        if self.settings_panel is None:
            self.settings_panel = SettingsPanel(self)
        self.settings_panel.open(animate=animate and self.isVisible(), focus=focus)

    @property
    def settings_open(self) -> bool:
        return self.settings_panel is not None and self.settings_panel.is_open

    def refresh(self, *_) -> None:
        if self.list_view is None:
            return
        running = self.controller.running
        has_jobs = bool(self.controller.jobs)
        selected = self.list_view.selected_rows()
        has_outputs = bool(self.controller.outputs())
        selected_output = any(self.controller.jobs[r].output for r in selected if r < len(self.controller.jobs))
        self.act_add_files.setEnabled(not running)
        self.act_add_folder.setEnabled(not running)
        self.act_remove.setEnabled(not running and bool(selected))
        self.act_clear.setEnabled(not running and has_jobs)
        self.act_run.setEnabled(not running and has_jobs)
        self.act_show.setEnabled(not running and has_outputs)
        self.act_open_pdf.setEnabled(not running and selected_output)
        for act in self.act_designs:
            act.setEnabled(not running)
        self.update_view()

    def _running_changed(self, running: bool) -> None:
        self.refresh()

    # Adding files --------------------------------------------------------------

    def add_paths(self, paths) -> None:
        paths = list(paths)
        if not paths:
            return
        self.controller.last_dir = Path(paths[0]).parent if Path(paths[0]).is_file() else Path(paths[0])
        result = self.controller.add_paths(paths)
        note = result.text()
        if note:
            self.notify(note, "warning" if not result.added else "info")
        if result.added:
            self.list_view.setFocus()

    def pick_files(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(self, "Choose PDFs", str(self.controller.last_dir), PDF_FILTER)
        self.add_paths(Path(n) for n in names)

    def pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder of PDFs", str(self.controller.last_dir))
        if folder:
            self.add_paths([Path(folder)])

    def remove_selected(self) -> None:
        rows = self.list_view.selected_rows()
        if rows:
            self.controller.remove_rows(rows)

    def _open_selected(self) -> None:
        for row in self.list_view.selected_rows():
            self.controller.open_output(row)

    # Drag and drop -------------------------------------------------------------

    @staticmethod
    def _dropped_paths(mime) -> list[Path]:
        paths = [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]
        return [p for p in paths if p.is_dir() or p.suffix.lower() == ".pdf"]

    def dragEnterEvent(self, event) -> None:
        if not self.controller.running and self._dropped_paths(event.mimeData()):
            event.acceptProposedAction()
            self.set_drop_active(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not self.controller.running and self._dropped_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.set_drop_active(False)

    def dropEvent(self, event) -> None:
        self.set_drop_active(False)
        paths = self._dropped_paths(event.mimeData())
        if paths and not self.controller.running:
            event.acceptProposedAction()
            self.add_paths(paths)

    # Menus, closing ------------------------------------------------------------

    def _context_menu(self, pos: QPoint) -> None:
        index = self.list_view.indexAt(pos)
        if index.isValid() and index.row() not in self.list_view.selected_rows():
            self.list_view.selectionModel().select(
                index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        menu = QMenu(self)
        menu.addActions([self.act_open_pdf, self.act_show])
        menu.addSeparator()
        menu.addActions([self.act_remove, self.act_clear])
        menu.exec(self.list_view.viewport().mapToGlobal(pos))

    def _about(self) -> None:
        QMessageBox.about(
            self, self.labels.about,
            "Replaces the SenAI title with \u201cBrinns autocompleter\u201d, removes the senai.uk "
            "footer, and fixes SenAI's missing symbols and spaces.\n\n"
            f"Cleaned copies are saved as {self.controller.example_name()}; "
            "originals are never changed.\n\n"
            "Fonts: Inter (SIL Open Font License). Icons: Lucide (ISC License).",
        )

    def closeEvent(self, event) -> None:
        self.controller.wait()
        super().closeEvent(event)
