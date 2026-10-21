"""Draws the app icon: senai_remover/gui/assets/app.png and app.ico.

Run with PySide6 and Pillow installed:  python tools/make_icon.py
"""

import io
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath

OUT = Path(__file__).resolve().parent.parent / "senai_remover" / "gui" / "assets"


def draw(size: int = 1024) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 1024

    # Tile: a blue gradient square with continuous rounded corners.
    tile = QRectF(64, 64, 896, 896)
    gradient = QLinearGradient(tile.topLeft(), tile.bottomRight())
    gradient.setColorAt(0, QColor("#4C8DFF"))
    gradient.setColorAt(1, QColor("#1D4FD8"))
    p.scale(s, s)
    p.setPen(Qt.NoPen)
    p.setBrush(gradient)
    p.drawRoundedRect(tile, 200, 200)

    # Page with a folded corner and three lines of "text".
    page = QPainterPath()
    page.moveTo(270, 190)
    page.lineTo(600, 190)
    page.lineTo(740, 330)
    page.lineTo(740, 790)
    page.quadTo(740, 830, 700, 830)
    page.lineTo(310, 830)
    page.quadTo(270, 830, 270, 790)
    page.lineTo(270, 230)
    page.quadTo(270, 190, 310, 190)
    p.setBrush(QColor("#FFFFFF"))
    p.drawPath(page)
    fold = QPainterPath()
    fold.moveTo(600, 190)
    fold.lineTo(600, 300)
    fold.quadTo(600, 330, 630, 330)
    fold.lineTo(740, 330)
    fold.closeSubpath()
    p.setBrush(QColor("#C7D8FF"))
    p.drawPath(fold)
    p.setBrush(QColor("#B9CCF7"))
    for y, w in ((420, 340), (500, 380), (580, 260)):
        p.drawRoundedRect(QRectF(340, y, w, 34), 17, 17)

    # The erased mark: a pale streak where the stamp used to be.
    p.setBrush(QColor(255, 255, 255, 255))
    p.drawRoundedRect(QRectF(330, 660, 330, 60), 30, 30)
    p.setBrush(QColor("#FFD9D2"))
    p.drawRoundedRect(QRectF(330, 672, 170, 36), 18, 18)

    # Eraser, tilted, overlapping the page's lower edge.
    p.save()
    p.translate(QPointF(640, 690))
    p.rotate(-35)
    p.setBrush(QColor("#FF6B5B"))
    p.drawRoundedRect(QRectF(-80, -170, 160, 250), 34, 34)
    p.setBrush(QColor("#2B3A67"))
    p.drawRoundedRect(QRectF(-80, 30, 160, 80), 0, 0)
    p.setBrush(QColor("#2B3A67"))
    p.drawRoundedRect(QRectF(-80, 60, 160, 90), 34, 34)
    p.restore()
    p.end()
    return image


def to_pil(image: QImage) -> Image.Image:
    buffer = QBuffer()
    buffer.open(QBuffer.ReadWrite)
    image.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data())))


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    big = to_pil(draw(1024))
    big.resize((512, 512), Image.LANCZOS).save(OUT / "app.png")
    big.save(OUT / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", OUT / "app.png", OUT / "app.ico")
