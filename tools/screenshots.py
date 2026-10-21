"""Renders every theme, offscreen, for design review and documentation.

    python tools/screenshots.py OUT_DIR [theme numbers...]   # review set
    python tools/screenshots.py --previews                   # Settings card images
    python tools/screenshots.py --docs                       # README screenshots

The review set is each theme empty, with files added, and after cleaning
(a cleaned, an unchanged and a failed file, second row selected), in light
and dark. --previews writes senai_remover/gui/assets/previews/ and --docs
writes docs/screenshots/. A throwaway settings file is used, so your own
saved theme is never touched.
"""

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SENAI_REDUCE_MOTION", "1")  # capture finished states, not mid-animation
os.environ["SENAI_SETTINGS_FILE"] = str(Path(tempfile.mkdtemp()) / "settings.ini")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEventLoop, QItemSelectionModel, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from senai_remover.core import clean_pdf  # noqa: E402
from senai_remover.gui.app import Shell, configure  # noqa: E402
from senai_remover.gui.designs import DESIGNS  # noqa: E402
from senai_remover.gui.settings_panel import CARD_WIDTH, PREVIEW_HEIGHT  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "senai_sample.pdf"
SIZE = (880, 600)


def sample_files(folder: Path) -> list[Path]:
    hw = folder / "Homework" / "Week 7"
    hw.mkdir(parents=True)
    a = hw / "Algebra homework - due Monday.pdf"
    shutil.copy(FIXTURE, a)
    shutil.copy(FIXTURE, hw / "Angles and triangles.pdf")
    plain = hw / "Revision notes.pdf"
    clean_pdf(FIXTURE, plain)  # already clean: nothing to remove
    broken = hw / "Scanned worksheet.pdf"
    broken.write_bytes(b"not really a pdf")
    return [a, hw / "Angles and triangles.pdf", plain, broken]


def settle(ms=60):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def render(app, index: int, appearance: str, state: str, files, settings_open=False) -> QImage:
    """The window for theme ``index`` in ``state`` (empty, listed or done)."""
    os.environ["SENAI_APPEARANCE"] = appearance
    for stale in files[0].parent.glob("*_clean*.pdf"):
        stale.unlink()
    shell = Shell(app)
    shell.show(index)
    w = shell.window
    w.resize(*SIZE)
    if state != "empty":
        w.add_paths(files)
    if state == "done":
        loop = QEventLoop()
        shell.controller.finished.connect(lambda *_: loop.quit())
        shell.controller.run()
        loop.exec()
        view = w.list_view
        view.setFocus()
        view.selectionModel().select(view.model().index(1, 0),
                                     QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
    if settings_open:
        w.open_settings(animate=False)
    w.activateWindow()
    settle(150)
    image = w.grab().toImage()
    w.close()
    shell.deleteLater()
    settle()
    return image


def main() -> None:
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # the broken sample is meant to fail
    app = configure(QApplication.instance() or QApplication([]))
    args = sys.argv[1:]
    with tempfile.TemporaryDirectory() as tmp:
        files = sample_files(Path(tmp))
        if args == ["--previews"]:
            out = ROOT / "senai_remover" / "gui" / "assets" / "previews"
            out.mkdir(exist_ok=True)
            for index, design in enumerate(DESIGNS):
                for appearance in ("light", "dark"):
                    image = render(app, index, appearance, "done", files)
                    small = image.scaled(CARD_WIDTH * 2, (PREVIEW_HEIGHT - 8) * 2,
                                         Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    small.save(str(out / f"{design.ID}-{appearance}.png"), "PNG")
                    print("wrote", out / f"{design.ID}-{appearance}.png")
        elif args == ["--docs"]:
            out = ROOT / "docs" / "screenshots"
            out.mkdir(parents=True, exist_ok=True)
            for index, design in enumerate(DESIGNS):
                for appearance in ("light", "dark"):
                    render(app, index, appearance, "done", files).save(str(out / f"{design.ID}-{appearance}.png"))
                    print("wrote", out / f"{design.ID}-{appearance}.png")
            for appearance in ("light", "dark"):
                render(app, 0, appearance, "listed", files, settings_open=True).save(
                    str(out / f"settings-{appearance}.png"))
                print("wrote", out / f"settings-{appearance}.png")
        else:
            out = Path(args[0])
            out.mkdir(parents=True, exist_ok=True)
            which = [int(a) - 1 for a in args[1:]] or range(len(DESIGNS))
            for index in which:
                for appearance in ("light", "dark"):
                    for state in ("empty", "listed", "done"):
                        name = f"p{index + 1}-{appearance}-{state}.png"
                        render(app, index, appearance, state, files).save(str(out / name))
                        print("wrote", out / name)


if __name__ == "__main__":
    main()
