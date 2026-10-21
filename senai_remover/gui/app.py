"""Starts the desktop app and swaps between the design prototypes."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional, Sequence

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication

from .controller import Controller
from .designs import DESIGNS
from .theme import ASSETS, load_fonts, system_prefs


class Shell(QObject):
    """Keeps one controller (the file list and results) and shows it in
    whichever design is current."""

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.controller = Controller(self)
        self.window = None
        self.index = 0
        app.styleHints().colorSchemeChanged.connect(lambda *_: self.show(self.index))

    def show(self, index: int) -> None:
        if self.controller.running:
            return
        self.index = index % len(DESIGNS)
        design = DESIGNS[self.index]
        old = self.window
        self.window = design(self.controller, system_prefs(), [d.NAME for d in DESIGNS], self.index, self.show)
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


def configure(app: QApplication) -> QApplication:
    app.setApplicationName("SenAI Watermark Remover")
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(ASSETS / "app.png")))
    load_fonts()
    return app


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Open the app. ``--design N`` (1 to 4) picks the prototype; any PDFs
    or folders passed are added to the list."""
    args = list(sys.argv[1:] if argv is None else argv)
    index = 0
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
    shell.show(index)
    if paths:
        shell.window.add_paths(paths)
    return app.exec()
