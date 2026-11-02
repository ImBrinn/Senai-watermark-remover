"""Mono: black, white and hairline rules. No tinted tiles, no rounded corners.

Status is still an icon plus words. The colour in a result is there so a
tick, a warning and an error can be told apart; the words say which it is.
"""

from .studio import CONTRAST as _CONTRAST
from .studio import StageWindow, StudioRows, mount, paint_tokens, stage_stylesheet

CONTRAST = _CONTRAST

TEXT = ["Inter"]
DISPLAY = ["Inter Display", "Inter"]

LIGHT = {
    "bg": "#FFFFFF", "surface": "#FFFFFF", "border": "#111111", "separator": "#111111",
    "label": "#111111", "secondary": "#333333", "disabled": "#767676",
    "accent": "#111111", "accent_hover": "#2A2A2A", "accent_pressed": "#000000", "on_accent": "#FFFFFF",
    "accent_disabled": "#E6E6E6", "on_accent_disabled": "#FFFFFF",
    "accent_text": "#111111", "accent_tint": "#F2F2F2",
    "success": "#0B5A28", "warning": "#7A4800", "danger": "#9B1B1B",
    "success_bg": "#E5F6EB", "warning_bg": "#FFF1D6", "danger_bg": "#FDECEC", "info_bg": "#F6F6F6",
    "hover": "#F2F2F2", "selected": "#E6E6E6", "control": "#FFFFFF",
    "control_hover": "#F7F7F7", "control_pressed": "#EFEFEF",
    "control_border": "#111111", "control_bottom": "#111111",
    "cmd_hover": "#F2F2F2", "cmd_pressed": "#E6E6E6",
    "focus": "#111111", "scroll": "rgba(17,17,17,0.45)",
}
DARK = {
    "bg": "#0A0A0A", "surface": "#111111", "border": "#F2F2F2", "separator": "#3A3A3A",
    "label": "#F5F5F5", "secondary": "#D4D4D4", "disabled": "#8A8A8A",
    "accent": "#F5F5F5", "accent_hover": "#E0E0E0", "accent_pressed": "#FFFFFF", "on_accent": "#111111",
    "accent_disabled": "#2A2A2A", "on_accent_disabled": "#8A8A8A",
    "accent_text": "#F5F5F5", "accent_tint": "#1C1C1C",
    "success": "#8EE0A8", "warning": "#FFD56A", "danger": "#FFB4B4",
    "success_bg": "#14301E", "warning_bg": "#3A3014", "danger_bg": "#3A2020", "info_bg": "#161616",
    "hover": "#1C1C1C", "selected": "#262626", "control": "#161616",
    "control_hover": "#1C1C1C", "control_pressed": "#0E0E0E",
    "control_border": "#F2F2F2", "control_bottom": "#F2F2F2",
    "cmd_hover": "#1C1C1C", "cmd_pressed": "#262626",
    "focus": "#F5F5F5", "scroll": "rgba(245,245,245,0.45)",
}


def tokens(prefs):
    return paint_tokens(LIGHT, DARK, prefs)


def stylesheet(t):
    return stage_stylesheet(t, radius=0, focus=2, control=32, hairline=1)


class Rows(StudioRows):
    height = 56
    radius = 0
    tile = False
    mark = "line"
    name_size = 14
    small_size = 12
    families = TEXT


class MonoWindow(StageWindow):
    ID = "mono"
    NAME = "Mono"
    DESCRIPTION = "Black, white and hairlines"
    TITLE_CASE = False
    DEFAULT_SIZE = (820, 600)
    MIN_SIZE = (600, 460)
    FAMILIES = TEXT
    DISPLAY = DISPLAY
    BODY = 14
    SMALL = 12
    TITLE_SIZE = 28
    PROGRESS = 2
    ROWS = Rows
    SUBTITLE = "The SenAI title, the footer and the broken symbols. Nothing else is rewritten."

    def build(self) -> None:
        mount(self)
