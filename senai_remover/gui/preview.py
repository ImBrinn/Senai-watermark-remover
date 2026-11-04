"""A before/after look at the words on page 1.

The picture is the text layer only: each character sits where the PDF put
it. Rules, pictures and the exact font aren't drawn. That keeps the window
on the same libraries as the rest of the app (no PDF renderer), and it is
enough to see a leftover footer or a sentence that is still run together.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from pypdf import PdfReader

from ..core import _page_fonts
from ..pdftext import glyphs
from .theme import icon
from .widgets import font, icon_button


def _page(path: Path, number: int = 0):
    reader = PdfReader(path)
    if number >= len(reader.pages):
        return [], 1.0, 1.0
    page = reader.pages[number]
    found = [g for g in glyphs(page.get_contents().operations, _page_fonts(page), {}) if g.visible]
    box = page.mediabox
    return found, float(box.width), float(box.height)


class _Page(QWidget):
    """One page of text, scaled to fit."""

    def __init__(self, found, width: float, height: float):
        super().__init__()
        self.found = found
        self.page_w = width or 1.0
        self.page_h = height or 1.0
        self.setMinimumSize(300, 400)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        avail = QRectF(self.rect()).adjusted(10, 8, -10, -8)
        scale = min(avail.width() / self.page_w, avail.height() / self.page_h)
        pw, ph = self.page_w * scale, self.page_h * scale
        page = QRectF(avail.center().x() - pw / 2, avail.center().y() - ph / 2, pw, ph)
        p.fillRect(self.rect(), QColor("#e7e9ee"))
        p.fillRect(page, QColor("#ffffff"))
        p.setPen(QPen(QColor("#c5cad3"), 1))
        p.drawRect(page)
        p.setPen(QColor("#1c1c1c"))
        for g in self.found:
            if not g.text.strip():
                continue
            size = max(g.size * scale, 1.0)
            face = QFont("Times New Roman")
            face.setStyleHint(QFont.Serif)
            face.setPixelSize(max(1, round(size)))
            face.setItalic(bool(g.font.italic))
            face.setBold(bool(g.font.bold))
            p.setFont(face)
            x = page.left() + g.x * scale
            baseline = page.top() + (self.page_h - g.y) * scale
            if g.missing:
                p.drawRect(QRectF(x, baseline - size, max(size * 0.6, 2), size))
                continue
            p.drawText(QPointF(x, baseline), g.text)


class PagePreview(QDialog):
    def __init__(self, parent, source: Path, output: Path, name: str):
        super().__init__(parent)
        self.setWindowTitle(f"Page 1 — {name}")
        self.resize(920, 680)
        self.setMinimumSize(640, 480)
        t = parent.t
        self.setStyleSheet(
            f"QDialog {{ background: {t['bg']}; color: {t['label']}; }}"
            f"QLabel#hint {{ color: {t['secondary']}; }}"
            f"QLabel#side {{ color: {t['label']}; }}"
        )

        column = QVBoxLayout(self)
        column.setContentsMargins(20, 16, 20, 16)
        column.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel("Page 1, before and after")
        title.setFont(font(18, QFont.DemiBold))
        header.addWidget(title, 1)
        close = icon_button(icon("x", t["label"], 16, 2), "Close", 30)
        close.clicked.connect(self.accept)
        header.addWidget(close)
        column.addLayout(header)
        hint = QLabel("The words only, each one where the PDF put it. "
                      "Lines, pictures and the exact font aren't shown.", objectName="hint")
        hint.setWordWrap(True)
        hint.setFont(font(13))
        column.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(16)
        before, bw, bh = _page(source)
        after, aw, ah = _page(output)
        row.addWidget(self._side("Before", before, bw, bh))
        row.addWidget(self._side("After", after, aw, ah))
        column.addLayout(row, 1)

    @staticmethod
    def _side(caption: str, found, width: float, height: float) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        label = QLabel(caption, objectName="side")
        label.setFont(font(13, QFont.DemiBold))
        lay.addWidget(label)
        lay.addWidget(_Page(found, width, height), 1)
        return wrap
