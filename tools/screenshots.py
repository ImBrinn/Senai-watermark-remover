"""Renders every design prototype in each state, for design review.

    python tools/screenshots.py OUTPUT_DIR [design numbers...]

Uses Qt's offscreen platform, so it needs no display. States: empty,
files added, after cleaning (with a cleaned, an unchanged and a failed
file, second row selected), in light and dark.
"""

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SENAI_REDUCE_MOTION", "1")  # capture finished states, not mid-animation
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEventLoop, QItemSelectionModel, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from senai_remover.core import clean_pdf  # noqa: E402
from senai_remover.gui.app import Shell, configure  # noqa: E402
from senai_remover.gui.designs import DESIGNS  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "senai_sample.pdf"


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


def settle(app, ms=60):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def shoot(app, index: int, appearance: str, state: str, out: Path, files) -> None:
    os.environ["SENAI_APPEARANCE"] = appearance
    shell = Shell(app)
    shell.show(index)
    w = shell.window
    w.resize(880, 600)
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
    w.activateWindow()
    settle(app, 150)
    w.grab().save(str(out))
    w.close()
    shell.deleteLater()
    settle(app)


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    which = [int(a) - 1 for a in sys.argv[2:]] or range(len(DESIGNS))
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # the broken sample is meant to fail
    app = configure(QApplication.instance() or QApplication([]))
    with tempfile.TemporaryDirectory() as tmp:
        files = sample_files(Path(tmp))
        for index in which:
            for appearance in ("light", "dark"):
                for state in ("empty", "listed", "done"):
                    for stale in Path(tmp, "Homework", "Week 7").glob("*_clean*.pdf"):
                        stale.unlink()
                    name = f"p{index + 1}-{appearance}-{state}.png"
                    shoot(app, index, appearance, state, out / name, files)
                    print("wrote", out / name)


if __name__ == "__main__":
    main()
