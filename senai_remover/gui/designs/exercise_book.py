"""Theme 3, Exercise Book: a free-form design drawn from where these
PDFs come from, SenAI maths homework and the squared exercise books it
gets copied into.

- The window is a page of 5 mm squared paper (a 20 px grid) with a red
  margin line; the file list scrolls with its own grid so rows always sit
  on the lines, two squares tall.
- The header is the top of a fresh page: today's date on the right and
  the title underlined with a ruler, the underline landing on a grid line.
- Buttons are paper tabs; the output choice is written on a line.
- Results are marked like homework: a green-pen tick, a red-pen cross,
  and after a run a teacher's score ("3/4") in the corner, drawn in when
  animations are on. Every mark comes with words; colour never works alone.
- The selected row is swiped with a highlighter.
- In dark mode the page becomes a chalkboard.
"""

from __future__ import annotations

import datetime
import random
from typing import Optional

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPointF, QRect, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
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

from ..model import FileJob, RunSummary
from ..theme import Prefs, icon, icon_file, mix, pixmap
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

GRID = 20  # one square of 5 mm paper
MARGIN_X = 50  # the red margin line
CONTENT_X = 80  # writing starts on the fourth grid line
RIGHT_PAD = 28
HEADER_TOP = 20
HEADER_H = 100
TABS_H = 40
FOOTER_H = 80

LIGHT = {
    "bg": "#FBFCFE", "surface": "#FFFFFF", "grid": "#DCE6F2", "margin": "#E5484D",
    "border": "#1F2A44", "separator": "#DCE6F2", "pencil": "#8A94A6",
    "label": "#1F2A44", "secondary": "#545E73", "disabled": "#A3AABB",
    "accent": "#2747C9", "accent_hover": "#2140B5", "accent_pressed": "#1B379C", "on_accent": "#FFFFFF",
    "accent_text": "#2747C9", "focus": "#2747C9", "focus_on_accent": "#1F2A44",
    "success": "#1A6F33", "warning": "#975A00", "danger": "#C2262E",
    "highlight": "#FFE45C", "highlight_alpha": 0.80, "highlight_soft_alpha": 0.38,
    "hover": "#2747C9", "hover_alpha": 0.06, "tab_hover": "#F3F6FB",
    "disabled_fill": "#E6EAF1", "drop_tint": "#2747C9", "drop_alpha": 0.07,
    "scroll": "rgba(31,42,68,0.30)",
}
DARK = {
    "bg": "#1E2723", "surface": "#25302B", "grid": "#2D3A34", "margin": "#D9605E",
    "border": "#C9D3CC", "separator": "#2D3A34", "pencil": "#8E9C94",
    "label": "#EEF2EE", "secondary": "#B4C0B9", "disabled": "#5F6B65",
    "accent": "#8DB8FF", "accent_hover": "#A3C6FF", "accent_pressed": "#7AA8F5", "on_accent": "#10213F",
    "accent_text": "#9EC2FF", "focus": "#9EC2FF", "focus_on_accent": "#EEF2EE",
    "success": "#7FD99A", "warning": "#F2C46B", "danger": "#FF9A95",
    "highlight": "#FFFFFF", "highlight_alpha": 0.12, "highlight_soft_alpha": 0.07,
    "hover": "#FFFFFF", "hover_alpha": 0.05, "tab_hover": "#2B3731",
    "disabled_fill": "#2A3530", "drop_tint": "#8DB8FF", "drop_alpha": 0.10,
    "scroll": "rgba(238,242,238,0.30)",
}
# (text, background, minimum ratio). The *_rest colours are the
# translucent highlighter and hover as they actually land on the page.
CONTRAST = [
    ("label", "bg", 4.5), ("secondary", "bg", 4.5), ("label", "surface", 4.5), ("secondary", "surface", 4.5),
    ("label", "tab_hover", 4.5), ("label", "hover_rest", 4.5), ("secondary", "hover_rest", 4.5),
    ("label", "highlight_rest", 4.5), ("secondary", "highlight_rest", 4.5), ("danger", "highlight_rest", 4.5),
    ("success", "highlight_rest", 4.5), ("warning", "highlight_rest", 4.5),
    ("label", "highlight_soft_rest", 4.5), ("secondary", "highlight_soft_rest", 4.5),
    ("success", "bg", 4.5), ("warning", "bg", 4.5), ("danger", "bg", 4.5), ("danger", "hover_rest", 4.5),
    ("accent_text", "bg", 4.5), ("on_accent", "accent", 4.5), ("on_accent", "accent_hover", 4.5),
    ("label", "surface", 4.5),
]


def tokens(prefs: Prefs) -> dict:
    t = dict(DARK if prefs.dark else LIGHT)
    if prefs.high_contrast:
        t.update(secondary=t["label"], pencil=t["label"], grid=mix(t["label"], t["bg"], 0.35))
    t["highlight_rest"] = mix(t["highlight"], t["bg"], t["highlight_alpha"])
    t["highlight_soft_rest"] = mix(t["highlight"], t["bg"], t["highlight_soft_alpha"])
    t["hover_rest"] = mix(t["hover"], t["bg"], t["hover_alpha"])
    t["animations"] = prefs.animations
    return t


def stylesheet(t: dict) -> str:
    chevron = icon_file("chevron-down", t["secondary"], 12)
    return f"""
    * {{ font-family: Inter; font-size: 13px; color: {t['label']}; }}
    QMainWindow {{ background: {t['bg']}; }}
    #date {{ color: {t['secondary']}; background: transparent; }}
    #title {{ font-family: "Inter Display"; font-size: 24px; font-weight: 600; background: transparent;
              border-bottom: 2px solid {t['label']}; padding: 0 2px 3px 0; }}
    #subtitle {{ color: {t['secondary']}; background: transparent; }}
    #saveLabel {{ color: {t['secondary']}; background: transparent; }}
    QPushButton#tab {{ background: {t['surface']}; border: 1px solid {t['border']}; border-bottom-width: 2px;
                       border-radius: 6px; padding: 0 12px; min-height: 25px; max-height: 25px; }}
    QPushButton#tab:hover {{ background: {t['tab_hover']}; }}
    QPushButton#tab:pressed {{ background: {t['hover_rest']}; border-bottom-width: 1px;
                               min-height: 26px; max-height: 26px; }}
    QPushButton#tab:focus {{ border: 2px solid {t['focus']}; padding: 0 11px; min-height: 24px; max-height: 24px; }}
    QPushButton#tab:disabled {{ color: {t['disabled']}; border-color: {t['disabled']}; }}
    QPushButton#primary {{ background: {t['accent']}; color: {t['on_accent']}; border: 2px solid {t['accent']};
                           border-radius: 8px; padding: 0 18px 0 14px; min-height: 36px; max-height: 36px;
                           font-size: 14px; font-weight: 600; }}
    QPushButton#primary:hover {{ background: {t['accent_hover']}; border-color: {t['accent_hover']}; }}
    QPushButton#primary:pressed {{ background: {t['accent_pressed']}; border-color: {t['accent_pressed']}; }}
    QPushButton#primary:focus {{ border-color: {t['focus_on_accent']}; }}
    QPushButton#primary:disabled {{ background: {t['disabled_fill']}; border-color: {t['disabled_fill']};
                                    color: {t['disabled']}; }}
    QPushButton#primary[running="true"]:disabled {{ background: {t['accent']}; border-color: {t['accent']};
                                                    color: {t['on_accent']}; }}
    QComboBox {{ background: transparent; border: none; border-bottom: 1px solid {t['secondary']};
                 border-radius: 0; padding: 0 22px 0 4px; min-height: 26px; max-height: 26px; }}
    QComboBox:hover {{ background: {t['hover_rest']}; }}
    QComboBox:focus {{ border-bottom: 2px solid {t['focus']}; min-height: 25px; max-height: 25px; }}
    QComboBox::drop-down {{ border: none; width: 20px; subcontrol-position: center right; }}
    QComboBox::down-arrow {{ image: url({chevron}); width: 11px; height: 11px; }}
    QComboBox QAbstractItemView {{ background: {t['surface']}; border: 1px solid {t['border']}; padding: 4px;
                                   outline: 0; selection-background-color: {t['highlight_rest']};
                                   selection-color: {t['label']}; }}
    QToolButton {{ background: transparent; border: 2px solid transparent; border-radius: 6px; }}
    QToolButton:hover {{ background: {t['hover_rest']}; }}
    QToolButton:focus {{ border-color: {t['focus']}; }}
    QToolButton::menu-indicator {{ image: none; width: 0; }}
    QMenu {{ background: {t['surface']}; border: 1px solid {t['border']}; padding: 5px; }}
    QMenu::item {{ padding: 5px 26px 5px 14px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {t['highlight_rest']}; color: {t['label']}; }}
    QMenu::item:disabled {{ color: {t['disabled']}; }}
    QMenu::separator {{ height: 1px; background: {t['grid']}; margin: 4px 8px; }}
    QListView {{ background: transparent; border: none; outline: 0; }}
    #emptyTitle {{ font-family: "Inter Display"; font-size: 20px; font-weight: 600; }}
    #emptyBody {{ color: {t['secondary']}; }}
    #emptyState, #emptyIcon, #emptyTitle, #emptyBody {{ background: transparent; }}
    QProgressBar {{ background: transparent; border: none; min-height: 3px; max-height: 3px; }}
    QProgressBar::chunk {{ background: {t['accent_text']}; border-radius: 1px; }}
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 4px 2px; }}
    QScrollBar::handle:vertical {{ background: {t['scroll']}; border-radius: 4px; min-height: 32px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """


def paint_paper(p: QPainter, rect: QRect, origin: QPoint, t: dict) -> None:
    """Squared paper and the margin line. ``origin`` is where this
    widget's (0, 0) falls on the page, so every grid lines up."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing, False)
    p.fillRect(rect, QColor(t["bg"]))
    p.setPen(QPen(QColor(t["grid"]), 1))
    first_x = rect.left() + (-(origin.x() + rect.left())) % GRID
    for x in range(first_x, rect.right() + 1, GRID):
        p.drawLine(x, rect.top(), x, rect.bottom())
    first_y = rect.top() + (-(origin.y() + rect.top())) % GRID
    for y in range(first_y, rect.bottom() + 1, GRID):
        p.drawLine(rect.left(), y, rect.right(), y)
    margin = MARGIN_X - origin.x()
    if rect.left() - 2 <= margin <= rect.right() + 2:
        p.setPen(QPen(QColor(t["margin"]), 2))
        p.drawLine(margin, rect.top(), margin, rect.bottom())
    p.restore()


def tick_path(x: float, y: float, s: float = 1.0) -> QPainterPath:
    """A quick hand-drawn tick, about 17 by 14 at scale 1."""
    path = QPainterPath(QPointF(x, y + 8 * s))
    path.cubicTo(x + 2 * s, y + 9 * s, x + 3.6 * s, y + 11 * s, x + 5.2 * s, y + 14 * s)
    path.cubicTo(x + 7.6 * s, y + 8 * s, x + 11 * s, y + 3 * s, x + 17 * s, y)
    return path


def cross_path(x: float, y: float, s: float = 1.0) -> QPainterPath:
    path = QPainterPath(QPointF(x + 1 * s, y + 1 * s))
    path.quadTo(x + 7 * s, y + 6 * s, x + 14 * s, y + 13 * s)
    path.moveTo(x + 14 * s, y + 0.5 * s)
    path.quadTo(x + 6 * s, y + 7 * s, x + 0.5 * s, y + 13.5 * s)
    return path


def pen(color: str, width: float) -> QPen:
    result = QPen(QColor(color), width)
    result.setCapStyle(Qt.RoundCap)
    result.setJoinStyle(Qt.RoundJoin)
    return result


def highlighter(r: QRectF, seed: int) -> QPainterPath:
    """A highlighter swipe: straight-ish edges, slanted wobbly ends."""
    rnd = random.Random(seed)

    def j(n: float = 1.4) -> float:
        return rnd.uniform(-n, n)

    path = QPainterPath(QPointF(r.left() + 5 + j(), r.top() + j(0.8)))
    path.lineTo(r.right() - 3 + j(), r.top() + 1 + j(0.8))
    path.quadTo(r.right() + 4 + j(), r.center().y() + j(), r.right() - 1 + j(), r.bottom() + j(0.8))
    path.lineTo(r.left() + 1 + j(), r.bottom() - 1 + j(0.8))
    path.quadTo(r.left() - 4 + j(), r.center().y() + j(), r.left() + 5, r.top())
    return path


MARK = {"success": "tick", "warning": "tick", "secondary": "tick", "danger": "cross"}


class _Rows(RowDelegate):
    height = 2 * GRID

    def __init__(self, view: FileListView, t: dict):
        super().__init__(view)
        self.t = t
        self.name_font = font(14, QFont.Medium)
        self.small_font = font(12)
        self.status_font = font(13, QFont.Medium)

    def paint_row(self, p: QPainter, rect: QRect, job: FileJob, row: int, st: dict) -> None:
        t = self.t
        left = CONTENT_X
        right = rect.right() - RIGHT_PAD
        band = QRectF(left - 10, rect.top() + 3, right - left + 18, rect.height() - 6)
        if st["selected"]:
            color = QColor(t["highlight"])
            color.setAlphaF(t["highlight_alpha"] if st["focused"] else t["highlight_soft_alpha"])
            p.fillPath(highlighter(band, row), color)
        elif st["hover"]:
            color = QColor(t["hover"])
            color.setAlphaF(t["hover_alpha"])
            path = QPainterPath()
            path.addRoundedRect(band, 4, 4)
            p.fillPath(path, color)

        top = rect.top()
        p.drawPixmap(left, top + 11, pixmap("file-text", t["label"], 18, 1.6))

        status, extra = job.status_text()
        icon_name, role = status_icon(job)
        fm_status, fm_small = QFontMetrics(self.status_font), QFontMetrics(self.small_font)
        mark = MARK.get(role) if icon_name else None
        glyph_w = 24 if (mark or icon_name) else 0
        status_w = max(fm_status.horizontalAdvance(status) + glyph_w, fm_small.horizontalAdvance(extra))
        text_x = left + 28
        text_right = right - status_w - 18

        p.setFont(self.name_font)
        p.setPen(QColor(t["label"]))
        p.drawText(QRect(text_x, top + 2, text_right - text_x, 19), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(self.name_font).elidedText(job.name, Qt.ElideRight, text_right - text_x))
        line, is_error = second_line(job)
        mode = Qt.ElideRight if is_error or job.message else Qt.ElideMiddle
        p.setFont(self.small_font)
        p.setPen(QColor(t["danger" if is_error else "secondary"]))
        p.drawText(QRect(text_x, top + 21, text_right - text_x, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   fm_small.elidedText(line, mode, text_right - text_x))

        status_top = top + (2 if extra else 10)
        text_w = fm_status.horizontalAdvance(status)
        glyph_x = right - text_w - glyph_w + 2
        if mark == "tick":
            width = 1.6 if role == "secondary" else 2.3
            p.strokePath(tick_path(glyph_x, status_top + 2.5, 1.0), pen(t[role], width))
        elif mark == "cross":
            p.strokePath(cross_path(glyph_x + 1, status_top + 3, 1.0), pen(t[role], 2.3))
        elif icon_name:
            p.drawPixmap(glyph_x, status_top + 1, pixmap(icon_name, t[role], 16, 2))
        p.setFont(self.status_font)
        p.setPen(QColor(t[role]))
        p.drawText(QRect(right - text_w, status_top, text_w, 19), Qt.AlignRight | Qt.AlignVCenter, status)
        if extra:
            p.setFont(self.small_font)
            p.setPen(QColor(t["secondary"]))
            p.drawText(QRect(right - status_w, top + 21, status_w, 16), Qt.AlignRight | Qt.AlignVCenter, extra)


class Page(QWidget):
    """The central widget: a sheet of squared paper."""

    def __init__(self, t: dict):
        super().__init__()
        self.t = t
        self.drop_active = False

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        paint_paper(p, event.rect(), QPoint(0, 0), self.t)


class EmptyPage(QWidget):
    """A dashed pencil box ruled along the grid, around the empty state."""

    def __init__(self, page: Page, t: dict, inner: QWidget):
        super().__init__()
        self.page = page
        self.t = t
        layout = QVBoxLayout(self)
        layout.setContentsMargins(CONTENT_X, GRID, RIGHT_PAD + GRID, GRID)
        layout.addWidget(inner, 0, Qt.AlignCenter)

    def box(self) -> QRectF:
        origin = self.mapTo(self.page, QPoint(0, 0))

        def snap_up(v: int, o: int) -> int:
            return v + (-(o + v)) % GRID

        def snap_down(v: int, o: int) -> int:
            return v - (o + v) % GRID

        left = snap_up(CONTENT_X - origin.x(), origin.x())
        right = snap_down(self.width() - RIGHT_PAD, origin.x())
        top = snap_up(0, origin.y())
        bottom = snap_down(self.height() - 1, origin.y())
        return QRectF(left, top, right - left, bottom - top)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.box()
        if self.page.drop_active:
            tint = QColor(self.t["drop_tint"])
            tint.setAlphaF(self.t["drop_alpha"])
            p.setBrush(tint)
            p.setPen(pen(self.t["accent_text"], 2))
        else:
            p.setBrush(Qt.NoBrush)
            outline = pen(self.t["pencil"], 1.5)
            outline.setDashPattern([5, 4])
            p.setPen(outline)
        p.drawRoundedRect(r, 3, 3)


class Mark(QWidget):
    """Bottom-left corner: the teacher's score after a run, or a note."""

    def __init__(self, t: dict):
        super().__init__()
        self.t = t
        self.mode = ""
        self.text = ""
        self.role = "label"
        self.score = ""
        self.drawn = 1.0
        self.summary_font = font(13)
        self.score_font = font(28, QFont.DemiBold, "Inter Display")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(FOOTER_H - 20)
        self._anim: Optional[QVariantAnimation] = None

    def clear(self) -> None:
        self.mode = ""
        self.setAccessibleName("")
        self.setToolTip("")
        self.update()

    def show_note(self, text: str, role: str, icon_name: str) -> None:
        self.mode, self.text, self.role, self.icon_name = "note", text, role, icon_name
        self.setAccessibleName(text)
        self.setToolTip(text)
        self.update()

    def show_score(self, summary: RunSummary) -> None:
        ok = summary.cleaned + summary.unchanged
        self.mode = "score"
        self.score = f"{ok}/{summary.total}"
        self.text = summary.text()
        self.role = "success" if not summary.failed else "warning" if ok else "danger"
        self.setAccessibleName(f"{self.score}. {self.text}")
        self.setToolTip(self.text)
        if self._anim is not None:
            self._anim.stop()
        if self.t["animations"]:
            self._anim = QVariantAnimation(self)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.setDuration(450)
            self._anim.setEasingCurve(QEasingCurve.OutCubic)
            self._anim.valueChanged.connect(self._step)
            self.drawn = 0.0
            self._anim.start()
        else:
            self.drawn = 1.0
        self.update()

    def _step(self, value) -> None:
        self.drawn = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        if not self.mode:
            return
        t = self.t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        cy = self.height() / 2
        if self.mode == "note":
            p.drawPixmap(0, int(cy) - 8, pixmap(self.icon_name, t[self.role], 16, 2))
            p.setFont(self.summary_font)
            p.setPen(QColor(t[self.role]))
            p.drawText(QRectF(24, 0, self.width() - 24, self.height()),
                       Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, self.text)
            return

        fm = QFontMetrics(self.score_font)
        score_w = fm.horizontalAdvance(self.score)
        group_w = score_w + 8 + 26
        p.save()
        p.translate(4 + group_w / 2, cy)
        p.rotate(-6)
        p.translate(-group_w / 2, 0)
        p.setFont(self.score_font)
        p.setPen(QColor(t[self.role]))
        p.drawText(QRectF(0, -fm.height() / 2, score_w + 2, fm.height()), Qt.AlignLeft | Qt.AlignVCenter, self.score)
        if self.role == "danger":
            shape = cross_path(score_w + 10, -11, 1.5)
        else:
            shape = tick_path(score_w + 8, -12, 1.5)
        partial = QPainterPath()
        steps = 48
        upto = max(1, int(steps * self.drawn))
        partial.moveTo(shape.pointAtPercent(0))
        for i in range(1, upto + 1):
            partial.lineTo(shape.pointAtPercent(i / steps))
        if self.role == "danger":
            partial = shape  # two strokes; tracing them would join them up
        p.strokePath(partial, pen(t[self.role], 3.2))
        p.restore()

        x = 4 + group_w + 22
        p.setFont(self.summary_font)
        p.setPen(QColor(t["label"]))
        p.drawText(QRectF(x, 0, max(0, self.width() - x), self.height()),
                   Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, self.text)


class Footer(QWidget):
    """The bottom strip: the score or a note, the primary action, and while
    cleaning an ink progress line ruled along a grid line beside the button."""

    def __init__(self, page: Page, mark: Mark, primary: QPushButton, progress: QProgressBar):
        super().__init__()
        self.page = page
        self.primary = primary
        self.progress = progress
        self.setFixedHeight(FOOTER_H)
        row = QHBoxLayout(self)
        row.setContentsMargins(CONTENT_X - 4, 10, RIGHT_PAD, 10)
        row.setSpacing(20)
        row.addWidget(mark, 1)
        row.addWidget(primary, 0, Qt.AlignVCenter)
        progress.setParent(self)
        primary.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.primary and event.type() in (QEvent.Move, QEvent.Resize):
            self._place_progress()
        return False

    def _place_progress(self) -> None:
        origin = self.mapTo(self.page, QPoint(0, 0))
        middle = self.height() // 2
        line = middle - (origin.y() + middle) % GRID  # the grid line at or just above the middle
        if middle - line > GRID // 2:
            line += GRID
        right = self.primary.geometry().left() - 24
        self.progress.setGeometry(CONTENT_X, line - 1, max(0, right - CONTENT_X), 3)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._place_progress()


class ExerciseBookWindow(BaseWindow):
    ID = "exercise-book"
    NAME = "Exercise Book"
    DESCRIPTION = "Maths paper and teacher's marks"
    TITLE_CASE = False
    DEFAULT_SIZE = (820, 600)

    def build(self) -> None:
        t = self.t = tokens(self.prefs)
        L = self.labels
        set_palette(self, t)
        self.setStyleSheet(stylesheet(t))

        self.page = Page(t)
        self.setCentralWidget(self.page)
        column = QVBoxLayout(self.page)
        column.setContentsMargins(0, HEADER_TOP, 0, 0)
        column.setSpacing(0)

        # Top of the page: date, ruled title, one line of explanation. The
        # title's underline lands on the grid line at y = 80.
        header = QWidget()
        header.setFixedHeight(HEADER_H)
        head = QVBoxLayout(header)
        head.setContentsMargins(CONTENT_X, 0, RIGHT_PAD, 0)
        head.setSpacing(0)
        today = datetime.date.today()
        date = QLabel(f"{today:%A} {today.day} {today:%B}", objectName="date")
        date.setFixedHeight(GRID)
        date.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(date)
        title = QLabel("Remove the SenAI watermark", objectName="title")
        title.setFixedHeight(2 * GRID + 1)  # the 2 px underline covers the grid line
        title.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        title.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        head.addWidget(title, 0, Qt.AlignLeft)
        subtitle = QLabel("Clean copies are saved as name_clean.pdf. Originals aren't changed.",
                          objectName="subtitle")
        subtitle.setFixedHeight(GRID + 3)
        subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        head.addWidget(subtitle)
        head.addStretch(1)
        column.addWidget(header)

        # Paper tabs, and the output choice written on a line.
        tabs = QWidget()
        tabs.setFixedHeight(TABS_H)
        row = QHBoxLayout(tabs)
        row.setContentsMargins(CONTENT_X, 6, RIGHT_PAD, 6)
        row.setSpacing(10)
        for name, act in (("file-plus", self.act_add_files), ("folder-plus", self.act_add_folder)):
            button = QPushButton(icon(name, t["label"], 16, 1.75, t["disabled"]), f" {act.text()}", objectName="tab")
            button.setAccessibleName(act.text())
            button.setCursor(Qt.PointingHandCursor)
            bind(button, act)
            row.addWidget(button)
        more = icon_button(icon("ellipsis", t["label"], 18, 2), "More", 30)
        menu = QMenu(self)
        menu.addActions([self.act_open_pdf, self.act_show])
        menu.addSeparator()
        menu.addActions([self.act_remove, self.act_clear])
        menu.addSeparator()
        self.more_menu_items(menu)
        menu.addAction(self.act_about)
        menu.addSeparator()
        menu.addAction(self.act_exit)
        more.setMenu(menu)
        more.setPopupMode(QToolButton.InstantPopup)
        row.addWidget(self.settings_button(t["label"], 30))
        row.addWidget(more)
        row.addStretch(1)
        row.addWidget(QLabel(L.save_to, objectName="saveLabel"))
        row.addWidget(OutputPicker(self.controller, L))
        column.addWidget(tabs)
        column.addSpacing(GRID)

        # The list (or the empty page) starts on a grid line, y = 180.
        self.stack = QStackedWidget()
        choose = QPushButton(L.choose_files, objectName="tab")
        choose.setCursor(Qt.PointingHandCursor)
        bind(choose, self.act_add_files)
        self.empty_state = EmptyState(
            pixmap("eraser", t["label"], 36, 1.6), "Drop your SenAI PDFs here",
            "Or choose them from a folder. Each one gets a clean copy without the SenAI title "
            "or the senai.uk footer.", choose, width=360)
        self.empty = EmptyPage(self.page, t, self.empty_state)
        self.list_view = FileListView(self.controller.model)
        self.list_view.setItemDelegate(_Rows(self.list_view, t))
        self.list_view.backdrop = self._list_backdrop
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.list_view)
        column.addWidget(self.stack, 1)

        self.mark = Mark(t)
        self.primary = QPushButton(icon("eraser", t["on_accent"], 18, 1.75), f" {L.run}", objectName="primary")
        self.primary.setAccessibleName(L.run)
        self.primary.setCursor(Qt.PointingHandCursor)
        self.primary.setProperty("running", "false")
        metrics = QFontMetrics(font(14, QFont.DemiBold))
        self.primary.setMinimumWidth(max(metrics.horizontalAdvance("Cleaning 88 of 88…"),
                                         metrics.horizontalAdvance(L.run)) + 18 + 8 + 36)
        bind(self.primary, self.act_run)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        column.addWidget(Footer(self.page, self.mark, self.primary, self.progress))

    def _list_backdrop(self, p: QPainter, rect: QRect, scroll: int) -> None:
        origin = self.list_view.viewport().mapTo(self.page, QPoint(0, 0)) + QPoint(0, scroll)
        paint_paper(p, rect, origin, self.t)
        if self.page.drop_active:
            box = QRectF(self.list_view.viewport().rect()).adjusted(CONTENT_X - 12, 1, -RIGHT_PAD + 10, -1)
            tint = QColor(self.t["drop_tint"])
            tint.setAlphaF(self.t["drop_alpha"])
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(pen(self.t["accent_text"], 2))
            p.setBrush(tint)
            p.drawRoundedRect(box, 3, 3)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        (self.list_view if self.controller.jobs else self.empty_state.findChild(QPushButton)).setFocus()

    def update_view(self) -> None:
        self.stack.setCurrentIndex(1 if self.controller.jobs else 0)
        if not self.controller.running:
            self._set_running(False)
            if self.mark.mode == "score" and self.controller.last_summary is None:
                self.mark.clear()

    def _set_running(self, running: bool) -> None:
        if self.primary.property("running") == ("true" if running else "false"):
            return
        self.primary.setProperty("running", "true" if running else "false")
        self.primary.style().unpolish(self.primary)
        self.primary.style().polish(self.primary)
        self.progress.setVisible(running)
        if not running:
            self.primary.setText(f" {self.labels.run}")

    def on_progress(self, done: int, total: int) -> None:
        self.mark.clear()
        self._set_running(True)
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        self.primary.setText(f" Cleaning {min(done + 1, total)} of {total}…" if done < total else " Finishing…")

    def on_finished(self, summary: RunSummary) -> None:
        self._set_running(False)
        self.mark.show_score(summary)

    def notify(self, text: str, kind: str = "info") -> None:
        role, name = {"success": ("success", "circle-check"), "warning": ("warning", "triangle-alert"),
                      "error": ("danger", "circle-x")}.get(kind, ("accent_text", "info"))
        self.mark.show_note(text, role, name)

    def add_paths(self, paths) -> None:
        if self.mark.mode == "note":
            self.mark.clear()
        super().add_paths(paths)

    def set_drop_active(self, active: bool) -> None:
        self.page.drop_active = active
        self.empty.update()
        self.list_view.viewport().update()
