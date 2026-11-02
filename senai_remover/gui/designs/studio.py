"""Shared stage for Midnight, Aurora, Mono and High Contrast.

Each of those themes still owns its colours, stylesheet and row painter.
This module builds the window they share: a title, command row, drop
target, file list, a progress line and a result banner. Motion follows
the system (and SENAI_REDUCE_MOTION); with motion off, states appear at
once.
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import QEasingCurve, QRect, QRectF, Qt, QPropertyAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..model import FileJob, Status
from ..theme import icon, icon_file, pixmap
from ..widgets import (
    EmptyState,
    FileListView,
    OutputPicker,
    RowDelegate,
    bind,
    font,
    icon_button,
    second_line,
    set_palette,
    status_icon,
)
from .base import BaseWindow

# Text on these pairs is checked for every newer theme, in light, dark and
# high contrast. Status icons on a tinted banner only need 3:1.
CONTRAST = [
    ("label", "bg", 4.5), ("label", "surface", 4.5),
    ("secondary", "bg", 4.5), ("secondary", "surface", 4.5),
    ("secondary", "hover", 4.5), ("secondary", "selected", 4.5), ("secondary", "cmd_hover", 4.5),
    ("label", "control", 4.5), ("label", "control_hover", 4.5),
    ("label", "selected", 4.5), ("label", "hover", 4.5),
    ("on_accent", "accent", 4.5), ("on_accent", "accent_hover", 4.5), ("on_accent", "accent_pressed", 4.5),
    ("accent_text", "surface", 4.5), ("accent_text", "accent_tint", 4.5), ("accent_text", "bg", 4.5),
    ("success", "surface", 4.5), ("warning", "surface", 4.5), ("danger", "surface", 4.5),
    ("success", "hover", 4.5), ("success", "selected", 4.5),
    ("warning", "hover", 4.5), ("warning", "selected", 4.5),
    ("danger", "hover", 4.5), ("danger", "selected", 4.5),
    ("label", "success_bg", 4.5), ("label", "warning_bg", 4.5), ("label", "danger_bg", 4.5),
    ("label", "info_bg", 4.5),
    ("success", "success_bg", 3.0), ("warning", "warning_bg", 3.0), ("danger", "danger_bg", 3.0),
    ("accent_text", "info_bg", 3.0),
]


_SEVERITY = {
    "success": ("circle-check", "success", "success_bg"),
    "warning": ("triangle-alert", "warning", "warning_bg"),
    "error": ("circle-x", "danger", "danger_bg"),
    "info": ("info", "accent_text", "info_bg"),
}


def paint_tokens(light: dict, dark: dict, prefs) -> dict:
    """Light or dark colours, with high contrast promoted to the label colour."""
    t = dict(dark if prefs.dark else light)
    if prefs.high_contrast:
        t.update(secondary=t["label"], border=t["label"], control_border=t["label"],
                 control_bottom=t["label"], separator=t["label"])
    return t


def stage_stylesheet(t: dict, *, radius: int = 10, focus: int = 2, control: int = 32, hairline: int = 1) -> str:
    """Controls, the list card and the result banner, in ``t``'s colours."""
    chevron = icon_file("chevron-down", t["secondary"], 12)
    r, f, h = radius, focus, hairline
    # A thicker focus ring keeps the outer size by giving a pixel back.
    focused = control - (f - h)
    pad = 12 - (f - h)
    return f"""
    QMainWindow, #root {{ background: {t['bg']}; }}
    QWidget {{ color: {t['label']}; }}
    #subtitle, #caption, #kicker, #progressLabel, #orLabel {{ color: {t['secondary']}; background: transparent; }}
    #title {{ background: transparent; }}
    #accentRule {{ background: {t['accent']}; border: none; border-radius: 2px; }}
    QMenu {{ background: {t['surface']}; color: {t['label']}; border: {h}px solid {t['border']};
             padding: 4px; }}
    QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: {min(r, 4)}px; }}
    QMenu::item:selected {{ background: {t['cmd_hover']}; color: {t['label']}; }}
    QMenu::item:disabled {{ color: {t['disabled']}; }}
    QMenu::separator {{ height: {h}px; background: {t['separator']}; margin: 4px 0; }}

    QToolButton#command {{ background: transparent; border: {f}px solid transparent; border-radius: {min(r, 6)}px;
                           padding: 0 10px; min-height: {control - 4}px; max-height: {control - 4}px; }}
    QToolButton#command:hover {{ background: {t['cmd_hover']}; }}
    QToolButton#command:pressed {{ background: {t['cmd_pressed']}; }}
    QToolButton#command:disabled {{ color: {t['disabled']}; }}
    QToolButton#command:focus {{ border-color: {t['focus']}; }}
    QToolButton#command::menu-indicator {{ image: none; width: 0; }}
    QToolButton {{ background: transparent; border: {f}px solid transparent; border-radius: {min(r, 6)}px; }}
    QToolButton:hover {{ background: {t['cmd_hover']}; }}
    QToolButton:focus {{ border-color: {t['focus']}; }}
    #commandSeparator {{ background: {t['separator']}; }}

    QPushButton {{ background: {t['control']}; color: {t['label']}; border: {h}px solid {t['control_border']};
                   border-bottom-color: {t['control_bottom']}; border-radius: {min(r, 8)}px;
                   padding: 0 14px; min-height: {control}px; max-height: {control}px; }}
    QPushButton:hover {{ background: {t['control_hover']}; }}
    QPushButton:pressed {{ background: {t['control_pressed']}; }}
    QPushButton:disabled {{ color: {t['disabled']}; }}
    QPushButton:focus {{ border: {f}px solid {t['focus']}; padding: 0 {pad}px;
                         min-height: {focused}px; max-height: {focused}px; }}
    QPushButton#primary {{ background: {t['accent']}; color: {t['on_accent']}; border: {h}px solid {t['accent']};
                           padding: 0 18px; min-width: 148px; }}
    QPushButton#primary:hover {{ background: {t['accent_hover']}; border-color: {t['accent_hover']}; }}
    QPushButton#primary:pressed {{ background: {t['accent_pressed']}; border-color: {t['accent_pressed']};
                                   color: {t['on_accent']}; }}
    QPushButton#primary:focus {{ border: {f}px solid {t['focus']}; }}
    QPushButton#primary:disabled {{ background: {t['accent_disabled']}; border-color: {t['accent_disabled']};
                                    color: {t['on_accent_disabled']}; }}
    QPushButton#link, QPushButton#bannerAction {{ background: transparent; border: {f}px solid transparent;
                        color: {t['accent_text']}; padding: 0 6px; min-height: {control - 4}px;
                        max-height: {control - 4}px; }}
    QPushButton#link:hover, QPushButton#bannerAction:hover {{ text-decoration: underline; }}
    QPushButton#link:focus, QPushButton#bannerAction:focus {{ border-color: {t['focus']}; }}

    QComboBox {{ background: {t['control']}; color: {t['label']}; border: {h}px solid {t['control_border']};
                 border-bottom-color: {t['control_bottom']}; border-radius: {min(r, 8)}px;
                 padding: 0 32px 0 12px; min-height: {control}px; max-height: {control}px; min-width: 150px; }}
    QComboBox:hover {{ background: {t['control_hover']}; }}
    QComboBox:focus {{ border: {f}px solid {t['focus']}; padding: 0 {32 - (f - h)}px 0 {12 - (f - h)}px;
                       min-height: {focused}px; max-height: {focused}px; }}
    QComboBox::drop-down {{ border: none; width: 30px; }}
    QComboBox::down-arrow {{ image: url({chevron}); width: 12px; height: 12px; }}
    QComboBox QAbstractItemView {{ background: {t['surface']}; color: {t['label']};
                                   border: {h}px solid {t['border']}; padding: 4px; outline: 0;
                                   selection-background-color: {t['cmd_hover']}; selection-color: {t['label']}; }}

    #card {{ background: {t['surface']}; border: {h}px solid {t['border']}; border-radius: {r}px; }}
    #card[drop="true"] {{ border: {max(h, 2)}px solid {t['accent']}; }}
    #banner {{ border: {h}px solid {t['border']}; border-radius: {min(r, 10)}px; }}
    #banner[severity="success"] {{ background: {t['success_bg']}; }}
    #banner[severity="warning"] {{ background: {t['warning_bg']}; }}
    #banner[severity="error"] {{ background: {t['danger_bg']}; }}
    #banner[severity="info"] {{ background: {t['info_bg']}; }}
    #banner QLabel {{ background: transparent; color: {t['label']}; }}
    QListView {{ background: transparent; border: none; outline: 0; }}
    #emptyState, #emptyIcon, #emptyTitle, #emptyBody {{ background: transparent; }}
    #emptyBody {{ color: {t['secondary']}; }}
    QProgressBar {{ background: {t['separator']}; border: none; border-radius: 2px; }}
    QProgressBar::chunk {{ background: {t['accent']}; border-radius: 2px; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 6px 2px; }}
    QScrollBar::handle:vertical {{ background: {t['scroll']}; border-radius: 3px; min-height: 32px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """


class StudioRows(RowDelegate):
    """A file row. Themes set ``radius``, ``tile`` and ``mark``."""

    height = 58
    radius = 8
    tile = True
    mark = "pill"          # pill | block | line
    name_size = 14
    small_size = 12
    families = ["Inter"]

    def __init__(self, view: FileListView, t: dict):
        super().__init__(view)
        self.t = t
        self.name_font = font(self.name_size, QFont.DemiBold, families=self.families)
        self.small_font = font(self.small_size, families=self.families)
        self.status_font = font(self.small_size, QFont.DemiBold, families=self.families)

    def paint_row(self, p: QPainter, rect: QRect, job: FileJob, row: int, st: dict) -> None:
        t = self.t
        r = QRectF(rect).adjusted(6, 3, -6, -3)
        if self.mark == "line":
            if st["selected"] or st["hover"]:
                p.fillRect(r, QColor(t["selected"] if st["selected"] else t["hover"]))
            elif not st["last"]:
                p.setPen(QPen(QColor(t["separator"]), 1))
                p.drawLine(int(r.left()), int(r.bottom()), int(r.right()), int(r.bottom()))
            if st["selected"]:
                p.fillRect(QRectF(r.left(), r.top(), 3, r.height()), QColor(t["accent"]))
        else:
            if st["selected"] or st["hover"]:
                path = QPainterPath()
                path.addRoundedRect(r, self.radius, self.radius)
                p.fillPath(path, QColor(t["selected"] if st["selected"] else t["hover"]))
            if st["selected"] and self.mark == "pill":
                pill = QRectF(r.left() + 4, r.center().y() - 9, 3, 18)
                path = QPainterPath()
                path.addRoundedRect(pill, 1.5, 1.5)
                p.fillPath(path, QColor(t["accent"]))
            if st["selected"] and self.mark == "block":
                p.fillRect(QRectF(r.left(), r.top(), 6, r.height()), QColor(t["accent"]))

        icon_size = 20 if self.name_size < 17 else 24
        if self.tile:
            side = icon_size + 16
            tile = QRectF(r.left() + 16, r.center().y() - side / 2, side, side)
            path = QPainterPath()
            path.addRoundedRect(tile, max(self.radius - 2, 0), max(self.radius - 2, 0))
            p.fillPath(path, QColor(t["accent_tint"]))
            p.drawPixmap(int(tile.left()) + 8, int(tile.top()) + 8,
                         pixmap("file-text", t["accent_text"], icon_size, 1.75))
            left = int(tile.right()) + 14
        else:
            p.drawPixmap(int(r.left()) + 14, int(r.center().y()) - icon_size // 2,
                         pixmap("file-text", t["label"], icon_size, 1.75))
            left = int(r.left()) + 14 + icon_size + 12

        status, extra = job.status_text()
        icon_name, role = status_icon(job)
        fm_status, fm_small, fm_name = (QFontMetrics(self.status_font), QFontMetrics(self.small_font),
                                        QFontMetrics(self.name_font))
        status_w = max(fm_status.horizontalAdvance(status) + (24 if icon_name else 0),
                       fm_small.horizontalAdvance(extra))
        right = int(r.right()) - 14
        text_right = right - status_w - 16
        line_h = fm_name.height()
        small_h = fm_small.height()
        top = int(r.center().y() - (line_h + 2 + small_h) / 2)

        p.setFont(self.name_font)
        p.setPen(QColor(t["label"]))
        p.drawText(QRect(left, top, max(text_right - left, 0), line_h), Qt.AlignLeft | Qt.AlignVCenter,
                   fm_name.elidedText(job.name, Qt.ElideRight, max(text_right - left, 0)))
        line, is_error = second_line(job)
        mode = Qt.ElideRight if is_error or job.status is Status.UNCHANGED else Qt.ElideMiddle
        p.setFont(self.small_font)
        p.setPen(QColor(t["danger" if is_error else "secondary"]))
        p.drawText(QRect(left, top + line_h + 2, max(text_right - left, 0), small_h),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   fm_small.elidedText(line, mode, max(text_right - left, 0)))

        status_h = fm_status.height()
        status_top = top if extra else int(r.center().y() - status_h / 2)
        p.setFont(self.status_font)
        p.setPen(QColor(t[role]))
        p.drawText(QRect(right - status_w, status_top, status_w, status_h), Qt.AlignRight | Qt.AlignVCenter, status)
        if icon_name:
            glyph = 16 if self.name_size < 17 else 18
            p.drawPixmap(right - fm_status.horizontalAdvance(status) - glyph - 6,
                         status_top + (status_h - glyph) // 2, pixmap(icon_name, t[role], glyph, 2))
        if extra:
            p.setFont(self.small_font)
            p.setPen(QColor(t["secondary"]))
            p.drawText(QRect(right - status_w, top + line_h + 2, status_w, small_h),
                       Qt.AlignRight | Qt.AlignVCenter, extra)


class _Ribbon(QWidget):
    """A full-width colour band with no text on it."""

    def __init__(self, colors: tuple[str, ...]):
        super().__init__()
        self.colors = colors
        self.setFixedHeight(8)
        self.setFocusPolicy(Qt.NoFocus)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        gradient = QLinearGradient(0, 0, max(self.width(), 1), 0)
        last = len(self.colors) - 1
        for i, color in enumerate(self.colors):
            gradient.setColorAt(i / last, QColor(color))
        p.fillRect(self.rect(), gradient)


class _DropWell(QWidget):
    """Dashed target. It fills with the accent tint while files are dragged
    over the window, and draws a focus ring only after keyboard focus."""

    def __init__(self, t: dict, inner: QWidget, on_activate, radius: int):
        super().__init__()
        self.t = t
        self.radius = radius
        self.active = False
        self.keyboard_focus = False
        self.on_activate = on_activate
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName("Drop PDFs here")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.addWidget(inner)

    def focusInEvent(self, event) -> None:
        self.keyboard_focus = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason)
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self.keyboard_focus = False
        self.update()
        super().focusOutEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.on_activate()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(16, 16, -16, -16)
        if self.active:
            p.setBrush(QColor(self.t["accent_tint"]))
            p.setPen(QPen(QColor(self.t["accent"]), 2))
        else:
            p.setBrush(Qt.NoBrush)
            pen = QPen(QColor(self.t["control_bottom"]), 1.5)
            pen.setDashPattern([5, 4])
            p.setPen(pen)
        p.drawRoundedRect(r, self.radius, self.radius)
        if self.keyboard_focus:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(self.t["focus"]), 2))
            p.drawRoundedRect(r.adjusted(-4, -4, 4, 4), self.radius + 2, self.radius + 2)


class _Banner(QFrame):
    """Result line: an icon, words, an optional action and a close button.
    The icon never stands alone."""

    def __init__(self, window: "StageWindow"):
        super().__init__(objectName="banner")
        self.window_ = window
        self._anim = None
        self._slot = None
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 8, 10)
        row.setSpacing(12)
        self.icon = QLabel()
        self.icon.setFixedSize(20, 20)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setFont(font(window.BODY, families=window.FAMILIES))
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.action = QPushButton(window.labels.show, objectName="bannerAction")
        self.action.setCursor(Qt.PointingHandCursor)
        self.action.setFont(font(window.BODY, families=window.FAMILIES))
        self.close_button = icon_button(icon("x", window.t["label"], 16), "Close", 32)
        self.close_button.clicked.connect(self.dismiss)
        row.addWidget(self.icon, 0, Qt.AlignVCenter)
        row.addWidget(self.text, 1)
        row.addWidget(self.action, 0, Qt.AlignVCenter)
        row.addWidget(self.close_button, 0, Qt.AlignVCenter)
        self.hide()

    def show_message(self, text: str, severity: str, action=None) -> None:
        icon_name, role, _ = _SEVERITY[severity]
        self.setProperty("severity", severity)
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon.setPixmap(pixmap(icon_name, self.window_.t[role], 18, 2))
        self.text.setText(text)
        self.setAccessibleName(text)
        if self._slot is not None:
            self.action.clicked.disconnect(self._slot)
            self._slot = None
        self.action.setVisible(action is not None)
        if action is not None:
            self._slot = action
            self.action.clicked.connect(action)
        self.show()
        self._animate()

    def _animate(self) -> None:
        if not self.window_.prefs.animations:
            self.setMaximumHeight(16777215)
            return
        self.ensurePolished()
        end = max(self.sizeHint().height(), 48)
        self.setMaximumHeight(0)
        anim = QPropertyAnimation(self, b"maximumHeight", self)
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(0)
        anim.setEndValue(end)
        anim.finished.connect(lambda: self.setMaximumHeight(16777215))
        anim.start()
        self._anim = anim

    def dismiss(self) -> None:
        self.hide()
        self.setMaximumHeight(16777215)


def _command(icon_name: str, text: str, t: dict, families: list[str], size: int) -> QToolButton:
    button = QToolButton(objectName="command")
    button.setIcon(icon(icon_name, t["label"], 16, 1.75, t["disabled"]))
    button.setText(f" {text}" if text else "")
    button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon if text else Qt.ToolButtonIconOnly)
    button.setFont(font(size, families=families))
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.StrongFocus)
    if text:
        button.setAccessibleName(text.rstrip("…"))
    return button


class StageWindow(BaseWindow):
    """Hooks shared by the four newer themes. ``build`` is still each theme's."""

    FAMILIES = ["Inter"]
    DISPLAY = ["Inter Display", "Inter"]
    BODY = 14
    ROWS = StudioRows
    RIBBON: Optional[tuple] = None
    RULE = False
    PROGRESS = 4
    SUBTITLE = ""
    TITLE_SIZE = 28
    SMALL = 12

    def update_view(self) -> None:
        running = self.controller.running
        self.stack.setCurrentIndex(1 if self.controller.jobs else 0)
        self.progress.setVisible(running)
        self.progress_label.setVisible(running)

    def on_progress(self, done: int, total: int) -> None:
        self.banner.dismiss()
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        words = f"Cleaning {done} of {total}"
        self.progress_label.setText(words)
        self.progress.setAccessibleName(words)
        self.progress.show()
        self.progress_label.show()

    def on_finished(self, summary) -> None:
        self.progress.hide()
        self.progress_label.hide()
        if summary.failed:
            kind = "warning" if summary.cleaned else "error"
        elif summary.cleaned:
            kind = "success"
        else:
            kind = "info"
        action = None
        if summary.outputs:
            action = lambda: self.controller.show_outputs(self.list_view.selected_rows())
        self.banner.show_message(summary.text() + ".", kind, action)

    def notify(self, text: str, kind: str = "info") -> None:
        shown = text[:1].upper() + text[1:]
        if not shown.endswith("."):
            shown += "."
        self.banner.show_message(shown, kind if kind in _SEVERITY else "info")

    def add_paths(self, paths) -> None:
        self.banner.dismiss()
        super().add_paths(paths)

    def set_drop_active(self, active: bool) -> None:
        self.drop_well.active = active
        self.drop_well.update()
        self.card.setProperty("drop", "true" if active and self.controller.jobs else "false")
        self.card.style().unpolish(self.card)
        self.card.style().polish(self.card)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.controller.jobs:
            self.list_view.setFocus()
        else:
            self.drop_well.setFocus()


def mount(window: StageWindow) -> None:
    """Build ``window`` from the tokens and stylesheet in its own module."""
    module = sys.modules[type(window).__module__]
    t = window.t = module.tokens(window.prefs)
    set_palette(window, t)
    window.setFont(font(window.BODY, families=window.FAMILIES))
    window.setStyleSheet(module.stylesheet(t))

    root = QWidget(objectName="root")
    window.setCentralWidget(root)
    page = QVBoxLayout(root)
    page.setContentsMargins(0, 0, 0, 0)
    page.setSpacing(0)
    if window.RIBBON:
        page.addWidget(_Ribbon(window.RIBBON))

    column = QVBoxLayout()
    column.setContentsMargins(32, 22, 32, 22)
    column.setSpacing(0)
    page.addLayout(column, 1)

    kicker = QLabel("SenAI Watermark Remover", objectName="kicker")
    kicker.setFont(font(window.SMALL, QFont.DemiBold, families=window.FAMILIES))
    column.addWidget(kicker)
    column.addSpacing(4)
    title = QLabel(window.labels.run, objectName="title")
    title.setFont(font(window.TITLE_SIZE, QFont.DemiBold, families=window.DISPLAY))
    title.setAccessibleName(window.labels.run)
    column.addWidget(title)
    if window.RULE:
        rule = QFrame(objectName="accentRule")
        rule.setFrameShape(QFrame.NoFrame)
        rule.setFixedSize(36, 3)
        column.addSpacing(8)
        column.addWidget(rule)
    column.addSpacing(6)
    subtitle = QLabel(window.SUBTITLE, objectName="subtitle")
    subtitle.setWordWrap(True)
    subtitle.setFont(font(window.BODY, families=window.FAMILIES))
    column.addWidget(subtitle)
    column.addSpacing(16)

    commands = QHBoxLayout()
    commands.setSpacing(2)
    for name, text, act in (("file-plus", window.labels.add_files, window.act_add_files),
                            ("folder-plus", window.labels.add_folder, window.act_add_folder)):
        button = _command(name, text, t, window.FAMILIES, window.BODY)
        bind(button, act)
        commands.addWidget(button)
    separator = QFrame(objectName="commandSeparator")
    separator.setFixedSize(1, 20)
    commands.addSpacing(6)
    commands.addWidget(separator, 0, Qt.AlignVCenter)
    commands.addSpacing(6)
    for name, text, act in (("trash-2", window.labels.remove, window.act_remove),
                            ("x", window.labels.clear, window.act_clear)):
        button = _command(name, text, t, window.FAMILIES, window.BODY)
        bind(button, act)
        commands.addWidget(button)
    commands.addStretch(1)
    more = _command("ellipsis", "", t, window.FAMILIES, window.BODY)
    more.setToolTip("See more")
    more.setAccessibleName("See more")
    more_menu = QMenu(window)
    more_menu.setFont(font(window.BODY, families=window.FAMILIES))
    more_menu.addActions([window.act_open_pdf, window.act_show])
    more_menu.addSeparator()
    window.more_menu_items(more_menu)
    more_menu.addAction(window.act_about)
    more_menu.addSeparator()
    more_menu.addAction(window.act_exit)
    more.setMenu(more_menu)
    more.setPopupMode(QToolButton.InstantPopup)
    gear = _command("settings", "", t, window.FAMILIES, window.BODY)
    gear.setToolTip(window.act_settings.toolTip())
    gear.setAccessibleName("Settings")
    bind(gear, window.act_settings)
    commands.addWidget(gear)
    commands.addWidget(more)
    column.addLayout(commands)
    column.addSpacing(12)

    window.banner = _Banner(window)
    column.addWidget(window.banner)
    column.addSpacing(12)

    window.card = QFrame(objectName="card")
    card_layout = QVBoxLayout(window.card)
    card_layout.setContentsMargins(4, 4, 4, 4)
    window.stack = QStackedWidget()
    browse = QPushButton(window.labels.choose_files, objectName="link")
    browse.setCursor(Qt.PointingHandCursor)
    browse.setFont(font(window.BODY, families=window.FAMILIES))
    bind(browse, window.act_add_files)
    inner = EmptyState(pixmap("upload", t["accent_text"], 36, 1.75), "Drag and drop PDFs here", "or",
                       browse, width=320)
    inner.title.setFont(font(window.BODY + 2, QFont.DemiBold, families=window.FAMILIES))
    inner.body.setFont(font(window.BODY, families=window.FAMILIES))
    caption = window.naming(QLabel(objectName="caption"),
                            "Folders work too. Cleaned copies are saved as {example}.")
    caption.setFont(font(window.SMALL, families=window.FAMILIES))
    caption.setAlignment(Qt.AlignCenter)
    inner.layout().addSpacing(12)
    inner.layout().addWidget(caption, 0, Qt.AlignHCenter)
    window.drop_well = _DropWell(t, inner, window.act_add_files.trigger, radius=window.ROWS.radius)
    window.list_view = FileListView(window.controller.model)
    window.list_view.setItemDelegate(window.ROWS(window.list_view, t))
    window.list_view.setFont(font(window.BODY, families=window.FAMILIES))
    window.stack.addWidget(window.drop_well)
    window.stack.addWidget(window.list_view)
    card_layout.addWidget(window.stack)
    column.addWidget(window.card, 1)

    column.addSpacing(10)
    window.progress = QProgressBar()
    window.progress.setTextVisible(False)
    window.progress.setFixedHeight(window.PROGRESS)
    window.progress_label = QLabel("Cleaning", objectName="progressLabel")
    window.progress_label.setFont(font(window.SMALL, families=window.FAMILIES))
    window.progress.hide()
    window.progress_label.hide()
    column.addWidget(window.progress)
    column.addWidget(window.progress_label)
    column.addSpacing(12)

    footer = QHBoxLayout()
    footer.setSpacing(10)
    save_label = QLabel(window.labels.save_to)
    save_label.setFont(font(window.BODY, families=window.FAMILIES))
    footer.addWidget(save_label)
    picker = OutputPicker(window.controller, window.labels)
    picker.setFont(font(window.BODY, families=window.FAMILIES))
    picker.view().setFont(font(window.BODY, families=window.FAMILIES))
    footer.addWidget(picker)
    footer.addStretch(1)
    primary = QPushButton(window.labels.run, objectName="primary")
    primary.setCursor(Qt.PointingHandCursor)
    primary.setFont(font(window.BODY, QFont.DemiBold, families=window.FAMILIES))
    bind(primary, window.act_run)
    footer.addWidget(primary)
    column.addLayout(footer)
