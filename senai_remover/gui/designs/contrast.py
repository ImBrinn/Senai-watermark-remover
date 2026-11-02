"""High Contrast: large type, thick borders and a yellow mark you can't miss.

Every state is an icon plus words. Focus is a 3px ring. Text on the window
is black on white, or white on black, including the secondary line.
"""

from .studio import CONTRAST as _CONTRAST
from .studio import StageWindow, StudioRows, mount, paint_tokens, stage_stylesheet

CONTRAST = _CONTRAST

TEXT = ["Inter"]
DISPLAY = ["Inter Display", "Inter"]

LIGHT = {
    "bg": "#FFFFFF", "surface": "#FFFFFF", "border": "#000000", "separator": "#000000",
    "label": "#000000", "secondary": "#000000", "disabled": "#595959",
    "accent": "#000000", "accent_hover": "#222222", "accent_pressed": "#000000", "on_accent": "#FFFFFF",
    "accent_disabled": "#D0D0D0", "on_accent_disabled": "#FFFFFF",
    "accent_text": "#000000", "accent_tint": "#FFF7A8",
    "success": "#005000", "warning": "#5C3A00", "danger": "#9B0000",
    "success_bg": "#D9F5D9", "warning_bg": "#FFF3C4", "danger_bg": "#FFD9D9", "info_bg": "#FFFFFF",
    "hover": "#FFF7A8", "selected": "#FFE14A", "control": "#FFFFFF",
    "control_hover": "#FFFBE2", "control_pressed": "#FFF7A8",
    "control_border": "#000000", "control_bottom": "#000000",
    "cmd_hover": "#FFF7A8", "cmd_pressed": "#FFE14A",
    "focus": "#000000", "scroll": "rgba(0,0,0,0.55)",
}
DARK = {
    "bg": "#000000", "surface": "#000000", "border": "#FFFFFF", "separator": "#FFFFFF",
    "label": "#FFFFFF", "secondary": "#FFFFFF", "disabled": "#C8C8C8",
    "accent": "#FFE14A", "accent_hover": "#FFE56A", "accent_pressed": "#F5D23A", "on_accent": "#000000",
    "accent_disabled": "#333333", "on_accent_disabled": "#A0A0A0",
    "accent_text": "#FFE14A", "accent_tint": "#333300",
    "success": "#7DFFA0", "warning": "#FFE14A", "danger": "#FF9A9A",
    "success_bg": "#003300", "warning_bg": "#332B00", "danger_bg": "#330000", "info_bg": "#000000",
    "hover": "#1A1A1A", "selected": "#333300", "control": "#000000",
    "control_hover": "#1A1A1A", "control_pressed": "#000000",
    "control_border": "#FFFFFF", "control_bottom": "#FFFFFF",
    "cmd_hover": "#1A1A1A", "cmd_pressed": "#333300",
    "focus": "#FFE14A", "scroll": "rgba(255,255,255,0.55)",
}


def tokens(prefs):
    return paint_tokens(LIGHT, DARK, prefs)


def stylesheet(t):
    return stage_stylesheet(t, radius=6, focus=3, control=40, hairline=2)


class Rows(StudioRows):
    height = 64
    radius = 4
    tile = True
    mark = "block"
    name_size = 17
    small_size = 14
    families = TEXT


class ContrastWindow(StageWindow):
    ID = "contrast"
    NAME = "High Contrast"
    DESCRIPTION = "Large type, thick focus"
    TITLE_CASE = False
    DEFAULT_SIZE = (880, 660)
    MIN_SIZE = (680, 520)
    FAMILIES = TEXT
    DISPLAY = DISPLAY
    BODY = 16
    SMALL = 14
    TITLE_SIZE = 28
    PROGRESS = 8
    ROWS = Rows
    SUBTITLE = "Large type and a thick focus ring. Status is always an icon plus words."

    def build(self) -> None:
        mount(self)
