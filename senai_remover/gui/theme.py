"""Fonts, icons, colour maths and the system appearance settings."""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSettings, Qt
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).parent / "assets"
FONT_FILES = (
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
    "InterDisplay-SemiBold.ttf",
)


def load_fonts() -> None:
    for name in FONT_FILES:
        QFontDatabase.addApplicationFont(str(ASSETS / "fonts" / name))


@lru_cache(maxsize=None)
def _svg(name: str) -> str:
    return (ASSETS / "icons" / f"{name}.svg").read_text(encoding="utf-8")


@lru_cache(maxsize=512)
def pixmap(name: str, color: str, size: int, stroke: float = 2.0, scale: float = 2.0) -> QPixmap:
    """A Lucide icon drawn in ``color`` at ``size`` logical pixels."""
    svg = _svg(name).replace("currentColor", color).replace('stroke-width="2"', f'stroke-width="{stroke}"')
    pm = QPixmap(round(size * scale), round(size * scale))
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, pm.width(), pm.height()))
    painter.end()
    pm.setDevicePixelRatio(scale)
    return pm


def icon(name: str, color: str, size: int = 16, stroke: float = 2.0, disabled: str = "") -> QIcon:
    result = QIcon()
    result.addPixmap(pixmap(name, color, size, stroke))
    if disabled:
        result.addPixmap(pixmap(name, disabled, size, stroke), QIcon.Disabled)
    return result


_ICON_DIR: list[Path] = []


def icon_file(name: str, color: str, size: int, stroke: float = 2.0) -> str:
    """A PNG of the icon on disk, for stylesheet ``image:`` rules. Returned
    with forward slashes, which Qt stylesheets accept on every platform."""
    if not _ICON_DIR:
        _ICON_DIR.append(Path(tempfile.mkdtemp(prefix="senai-icons-")))
    path = _ICON_DIR[0] / f"{name}-{color.lstrip('#')}-{size}-{stroke}.png"
    if not path.exists():
        pixmap(name, color, size, stroke, scale=2.0).save(str(path), "PNG")
    return path.as_posix()


def luminance(color: str) -> float:
    c = QColor(color)
    channels = []
    for v in (c.redF(), c.greenF(), c.blueF()):
        channels.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(foreground: str, background: str) -> float:
    """WCAG 2 contrast ratio between two opaque colours."""
    a, b = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def mix(color: str, over: str, alpha: float) -> str:
    """``color`` at ``alpha`` opacity composited over ``over``, as #rrggbb."""
    a, b = QColor(color), QColor(over)
    blend = [round(x * alpha + y * (1 - alpha)) for x, y in
             ((a.red(), b.red()), (a.green(), b.green()), (a.blue(), b.blue()))]
    return "#{:02x}{:02x}{:02x}".format(*blend)


@dataclass(frozen=True)
class Prefs:
    """The system settings the designs respond to."""

    dark: bool = False
    reduce_transparency: bool = False
    high_contrast: bool = False
    animations: bool = True


def system_prefs() -> Prefs:
    """Read the current settings. SENAI_* environment variables override
    them so tests and screenshots can force each appearance."""
    hints = QGuiApplication.styleHints()
    dark = hints.colorScheme() == Qt.ColorScheme.Dark
    reduce_transparency = high_contrast = False
    animations = True
    if sys.platform.startswith("win"):
        reduce_transparency, high_contrast, animations = _windows_prefs()

    env = os.environ.get
    if env("SENAI_APPEARANCE") in ("light", "dark"):
        dark = env("SENAI_APPEARANCE") == "dark"
    if env("SENAI_REDUCE_TRANSPARENCY"):
        reduce_transparency = env("SENAI_REDUCE_TRANSPARENCY") == "1"
    if env("SENAI_HIGH_CONTRAST"):
        high_contrast = env("SENAI_HIGH_CONTRAST") == "1"
    if env("SENAI_REDUCE_MOTION"):
        animations = env("SENAI_REDUCE_MOTION") != "1"
    return Prefs(dark, reduce_transparency, high_contrast, animations)


def _windows_prefs() -> tuple[bool, bool, bool]:
    reduce_transparency = high_contrast = False
    animations = True
    try:
        personalize = QSettings(
            r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            QSettings.NativeFormat,
        )
        reduce_transparency = int(personalize.value("EnableTransparency", 1)) == 0
    except Exception:
        pass
    try:
        import ctypes
        from ctypes import wintypes

        class HIGHCONTRAST(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwFlags", wintypes.DWORD),
                        ("lpszDefaultScheme", wintypes.LPWSTR)]

        SPI_GETHIGHCONTRAST, HCF_HIGHCONTRASTON = 0x0042, 0x1
        SPI_GETCLIENTAREAANIMATION = 0x1042
        info = HIGHCONTRAST(ctypes.sizeof(HIGHCONTRAST), 0, None)
        if ctypes.windll.user32.SystemParametersInfoW(SPI_GETHIGHCONTRAST, info.cbSize, ctypes.byref(info), 0):
            high_contrast = bool(info.dwFlags & HCF_HIGHCONTRASTON)
        enabled = wintypes.BOOL(True)
        if ctypes.windll.user32.SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(enabled), 0):
            animations = bool(enabled.value)
    except Exception:
        pass
    return reduce_transparency, high_contrast, animations
