"""Aurora: a cool, quiet window with a violet-to-teal band along the top.

The band is decoration. Titles and buttons sit on solid colours, so the
text keeps its contrast when the band shifts from violet to teal.
"""

from .studio import CONTRAST as _CONTRAST
from .studio import StageWindow, StudioRows, mount, paint_tokens, stage_stylesheet

CONTRAST = _CONTRAST

TEXT = ["Inter"]
DISPLAY = ["Inter Display", "Inter"]

LIGHT = {
    "bg": "#F2F6FB", "surface": "#FFFFFF", "border": "#D5E0EE", "separator": "#D5E0EE",
    "label": "#122033", "secondary": "#3E5168", "disabled": "#8AA0B8",
    "accent": "#0E6E86", "accent_hover": "#0C6176", "accent_pressed": "#0A5568", "on_accent": "#FFFFFF",
    "accent_disabled": "#D5E0EE", "on_accent_disabled": "#FFFFFF",
    "accent_text": "#0C5F74", "accent_tint": "#E3F4F8",
    "success": "#0E6B3C", "warning": "#8A5600", "danger": "#B42318",
    "success_bg": "#E3F6EC", "warning_bg": "#FFF1D6", "danger_bg": "#FDECEA", "info_bg": "#F2F6FB",
    "hover": "#E7F0F8", "selected": "#DCEAF6", "control": "#FFFFFF",
    "control_hover": "#F4F8FC", "control_pressed": "#E7F0F8",
    "control_border": "#D5E0EE", "control_bottom": "#B7C6DA",
    "cmd_hover": "#E7F0F8", "cmd_pressed": "#DCEAF6",
    "focus": "#122033", "scroll": "rgba(18,32,51,0.35)",
}
DARK = {
    "bg": "#0E1422", "surface": "#171E30", "border": "#2E3B54", "separator": "#2E3B54",
    "label": "#F4F7FF", "secondary": "#C9D4E8", "disabled": "#7E8DA8",
    "accent": "#5EEAD4", "accent_hover": "#4AD8C4", "accent_pressed": "#8AF6E4", "on_accent": "#042F2E",
    "accent_disabled": "#243044", "on_accent_disabled": "#8AA0B4",
    "accent_text": "#7AF0DC", "accent_tint": "#12343A",
    "success": "#6EE7B7", "warning": "#FCD34D", "danger": "#FFB4C0",
    "success_bg": "#12352A", "warning_bg": "#3A3014", "danger_bg": "#3A222C", "info_bg": "#1A2336",
    "hover": "#1E2740", "selected": "#24304C", "control": "#1A2336",
    "control_hover": "#1E2740", "control_pressed": "#141B2C",
    "control_border": "#2E3B54", "control_bottom": "#3D4E6C",
    "cmd_hover": "#1E2740", "cmd_pressed": "#24304C",
    "focus": "#F4F7FF", "scroll": "rgba(244,247,255,0.40)",
}


def tokens(prefs):
    return paint_tokens(LIGHT, DARK, prefs)


def stylesheet(t):
    return stage_stylesheet(t, radius=16, focus=2, control=32, hairline=1)


class Rows(StudioRows):
    height = 62
    radius = 14
    tile = True
    mark = "pill"
    name_size = 15
    small_size = 12
    families = TEXT


class AuroraWindow(StageWindow):
    ID = "aurora"
    NAME = "Aurora"
    DESCRIPTION = "Teal light on a quiet ground"
    TITLE_CASE = False
    DEFAULT_SIZE = (840, 620)
    MIN_SIZE = (620, 480)
    FAMILIES = TEXT
    DISPLAY = DISPLAY
    BODY = 15
    SMALL = 12
    TITLE_SIZE = 30
    RIBBON = ("#5B4BDB", "#0F766E", "#22D3EE")
    PROGRESS = 4
    ROWS = Rows
    SUBTITLE = ("A quiet place to clean a pile of PDFs. The title, the footer and the broken "
                 "symbols change. Your answers do not.")

    def build(self) -> None:
        mount(self)
