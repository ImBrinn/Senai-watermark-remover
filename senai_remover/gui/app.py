"""Starts the desktop app and swaps the window between themes."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Optional, Sequence

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication

from .controller import Controller
from .designs import DESIGNS
from .settings import Settings
from .theme import ASSETS, Prefs, load_fonts, system_prefs


class Shell(QObject):
    """Keeps one controller (the file list and results) and the saved
    settings, and shows them in whichever theme is current."""

    def __init__(self, app: QApplication, settings: Optional[Settings] = None):
        super().__init__()
        self.app = app
        self.designs = DESIGNS
        self.settings = settings or Settings()
        self.controller = Controller(self)
        self.controller.set_name_template(self.settings.output_name)
        self.window = None
        self.index = self.saved_index()
        app.styleHints().colorSchemeChanged.connect(self._scheme_changed)

    def saved_index(self) -> int:
        ids = [design.ID for design in self.designs]
        return ids.index(self.settings.theme) if self.settings.theme in ids else 0

    def prefs(self) -> Prefs:
        """The system settings, with the saved appearance applied unless
        SENAI_APPEARANCE forces one (tests and screenshots)."""
        prefs = system_prefs()
        mode = self.settings.appearance
        if mode != "system" and not os.environ.get("SENAI_APPEARANCE"):
            prefs = replace(prefs, dark=mode == "dark")
        return prefs

    def show(self, index: int, settings_open: bool = False, focus: str = "theme") -> None:
        """Build the window for theme ``index``, replacing the current one."""
        if self.controller.running:
            return
        self.index = index % len(self.designs)
        design = self.designs[self.index]
        old = self.window
        self.window = design(self.controller, self.prefs(), self, self.index)
        self.app.setStyleSheet(self.window.tooltip_style())
        if old is not None:
            self.window.setGeometry(old.geometry())
            if old.isMaximized():
                self.window.showMaximized()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        if old is not None:
            old.close()
        if settings_open:
            self.window.open_settings(animate=False, focus=focus)

    def switch(self, index: int, settings_open: bool = False) -> None:
        """Change theme (from Settings, the Theme menu or Ctrl+1 to 4) and
        remember it."""
        if self.controller.running:
            return
        self.settings.theme = self.designs[index % len(self.designs)].ID
        self.show(index, settings_open=settings_open or self._settings_open())

    def set_appearance(self, mode: str) -> None:
        self.settings.appearance = mode
        self.show(self.index, settings_open=True, focus="appearance")

    def set_output_name(self, template: str) -> None:
        """Save what cleaned copies are called; the window updates its wording."""
        self.settings.output_name = template
        self.controller.set_name_template(template)

    def _settings_open(self) -> bool:
        return self.window is not None and self.window.settings_open

    def _scheme_changed(self, *_) -> None:
        if self.settings.appearance == "system" and not self.controller.running:
            self.show(self.index, settings_open=self._settings_open())


def configure(app: QApplication) -> QApplication:
    app.setApplicationName("SenAI Watermark Remover")
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(ASSETS / "app.png")))
    load_fonts()
    return app


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Open the app in the saved theme, or theme N (1 to 4) with
    ``--design N``; any PDFs or folders passed are added to the list."""
    args = list(sys.argv[1:] if argv is None else argv)
    index = None
    if "--design" in args:
        at = args.index("--design")
        try:
            index = int(args[at + 1]) - 1
        except (IndexError, ValueError):
            pass
        del args[at:at + 2]
    paths = [Path(a) for a in args if Path(a).exists()]

    logging.getLogger("pypdf").setLevel(logging.ERROR)
    if sys.platform.startswith("win"):
        try:  # group the taskbar button under this app's icon, not Python's
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SenAI.WatermarkRemover")
        except Exception:
            pass
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = configure(QApplication.instance() or QApplication([sys.argv[0] if sys.argv else "senai-remover"]))
    shell = Shell(app)
    shell.show(shell.index if index is None else index)
    if paths:
        shell.window.add_paths(paths)
    return app.exec()
