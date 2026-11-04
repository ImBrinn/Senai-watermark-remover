"""Midnight: warm paper in the day, ink after dark, with a short gold rule.

The gold is the accent, on buttons and the selected row. Body text stays
on the paper or the ink, never on the gold except where the button says so.
"""

from .studio import CONTRAST as _CONTRAST
from .studio import StageWindow, StudioRows, mount, paint_tokens, stage_stylesheet

CONTRAST = _CONTRAST

TEXT = ["Inter"]
DISPLAY = ["Inter Display", "Inter"]

LIGHT = {
    "bg": "#F4EFE6", "surface": "#FFFBF5", "border": "#DDD2C2", "separator": "#DDD2C2",
    "label": "#1A1612", "secondary": "#5C5348", "disabled": "#9A9084",
    "accent": "#7A4B0A", "accent_hover": "#8F5A10", "accent_pressed": "#653E08", "on_accent": "#FFFFFF",
    "accent_disabled": "#D9D0C4", "on_accent_disabled": "#FFFFFF",
    "accent_text": "#6B4108", "accent_tint": "#F6E7D0",
    "success": "#1B6B38", "warning": "#8A5200", "danger": "#9D2424",
    "success_bg": "#E4F4EA", "warning_bg": "#FFF0D4", "danger_bg": "#FDECEC", "info_bg": "#F4EFE6",
    "hover": "#EFE6D8", "selected": "#E8DCC8", "control": "#FFFBF5",
    "control_hover": "#F7F1E8", "control_pressed": "#EFE6D8",
    "control_border": "#DDD2C2", "control_bottom": "#C9BBA6",
    "cmd_hover": "#EFE6D8", "cmd_pressed": "#E4D8C6",
    "focus": "#1A1612", "scroll": "rgba(26,22,18,0.35)",
}
DARK = {
    "bg": "#12100E", "surface": "#1C1916", "border": "#3C352C", "separator": "#3C352C",
    "label": "#F6F1E7", "secondary": "#D9CBB8", "disabled": "#7A7166",
    "accent": "#F0C36A", "accent_hover": "#E2B45A", "accent_pressed": "#F6D48A", "on_accent": "#1A1408",
    "accent_disabled": "#3A342C", "on_accent_disabled": "#8A8176",
    "accent_text": "#F0C36A", "accent_tint": "#3A2E1C",
    "success": "#8FDBA8", "warning": "#F0C14A", "danger": "#FFB4AE",
    "success_bg": "#1A3324", "warning_bg": "#3A2E14", "danger_bg": "#3A2220", "info_bg": "#221F1B",
    "hover": "#2A251F", "selected": "#332C24", "control": "#221F1B",
    "control_hover": "#2A251F", "control_pressed": "#1A1714",
    "control_border": "#3C352C", "control_bottom": "#4A4338",
    "cmd_hover": "#2A251F", "cmd_pressed": "#332C24",
    "focus": "#F6F1E7", "scroll": "rgba(246,241,231,0.40)",
}


def tokens(prefs):
    return paint_tokens(LIGHT, DARK, prefs)


def stylesheet(t):
    return stage_stylesheet(t, radius=14, focus=2, control=32, hairline=1)


class Rows(StudioRows):
    height = 62
    radius = 10
    tile = True
    mark = "pill"
    name_size = 15
    small_size = 12
    families = TEXT


class MidnightWindow(StageWindow):
    ID = "midnight"
    NAME = "Midnight"
    DESCRIPTION = "Ink, paper and warm gold"
    TITLE_CASE = False
    DEFAULT_SIZE = (840, 620)
    MIN_SIZE = (620, 480)
    FAMILIES = TEXT
    DISPLAY = DISPLAY
    BODY = 15
    SMALL = 12
    TITLE_SIZE = 30
    RULE = True
    PROGRESS = 3
    ROWS = Rows
    SUBTITLE = ("Swaps the SenAI title for yours, takes off the senai.uk footer and puts the "
                 "missing symbols back. Your originals are not changed.")

    def build(self) -> None:
        mount(self)
