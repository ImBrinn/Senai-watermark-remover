"""Prototype 2, Apple Liquid Glass: Apple's current design language,
following the Human Interface Guidelines and the skill's Liquid Glass guide.

- Two layers. Content (file cards, the drop well) is opaque; the controls
  float above it on glass that blurs whatever scrolls beneath, with a
  scroll edge effect where content meets the bar (materials.md, layout.md
  › Visual hierarchy).
- Glass is used sparingly: three capsules and a transient message
  (liquid-glass.md › Where the material belongs).
- Colour on glass is kept to the one primary action, which tints its
  background rather than its label (color.md › Liquid Glass color).
- Reduce Transparency gets an opaque fallback; high contrast gets solid
  fills and stronger borders.
- Less-used commands sit in a More menu (toolbars.md); every command is in
  the menu bar, shown by tapping Alt as in other Windows apps.
- The message after cleaning stays until dismissed (accessibility.md ›
  Cognitive: no time-boxed elements).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..model import FileJob, RunSummary, Status
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

LIGHT = {
    "bg": "#F2F2F7", "surface": "#FFFFFF", "border": "#E2E2E7", "separator": "#E5E5EA",
    "label": "#1D1D1F", "secondary": "#636366", "disabled": "#A1A1A6",
    "accent": "#0071E3", "accent_hover": "#0068D1", "accent_pressed": "#005BB8", "on_accent": "#FFFFFF",
    "accent_text": "#0066CC", "accent_tint": "#E5EFFC", "progress": "#4C9BF0",
    "success": "#1F7A35", "warning": "#C93400", "danger": "#D70015",
    "select_inactive": "#E3E3E8", "hover": "#F7F7FA",
    "glass": (255, 255, 255, 184), "glass_solid": "#FFFFFF", "glass_highlight": (255, 255, 255, 230),
    "glass_edge": (0, 0, 0, 26), "glass_shadow": (0, 0, 0, 16), "glass_hover": (0, 0, 0, 14),
    "edge_tint": (242, 242, 247, 150), "focus": "#7AB6F2", "scroll": "rgba(0,0,0,0.28)",
}
DARK = {
    "bg": "#161618", "surface": "#242426", "border": "#323235", "separator": "#323235",
    "label": "#F5F5F7", "secondary": "#AEAEB2", "disabled": "#636366",
    "accent": "#0071E3", "accent_hover": "#0A7CF0", "accent_pressed": "#0062C4", "on_accent": "#FFFFFF",
    "accent_text": "#409CFF", "accent_tint": "#102A47", "progress": "#3D8EEA",
    "success": "#30D158", "warning": "#FF9F0A", "danger": "#FF6961",
    "select_inactive": "#38383B", "hover": "#2A2A2D",
    "glass": (40, 40, 43, 190), "glass_solid": "#2C2C2E", "glass_highlight": (255, 255, 255, 40),
    "glass_edge": (0, 0, 0, 120), "glass_shadow": (0, 0, 0, 70), "glass_hover": (255, 255, 255, 20),
    "edge_tint": (22, 22, 24, 160), "focus": "#2E86E8", "scroll": "rgba(255,255,255,0.30)",
}
CONTRAST = [
    ("label", "surface", 4.5), ("label", "bg", 4.5), ("secondary", "surface", 4.5), ("secondary", "bg", 4.5),
    ("secondary", "hover", 4.5), ("label", "select_inactive", 4.5), ("secondary", "select_inactive", 4.5),
    ("on_accent", "accent", 4.5), ("accent_text", "surface", 4.5), ("accent_text", "accent_tint", 4.5),
    ("success", "surface", 4.5), ("warning", "surface", 4.5), ("danger", "surface", 4.5),
    ("label", "glass_rest", 4.5), ("secondary", "glass_rest", 4.5), ("label", "accent_tint", 4.5),
]
BAR_HEIGHT = 72


def tokens(prefs: Prefs) -> dict:
    t = dict(DARK if prefs.dark else LIGHT)
    if prefs.high_contrast:
        t.update(secondary=t["label"], border=t["label"], separator=t["secondary"],
                 glass_edge=QColor(t["label"]).getRgb())
    # The glass at rest over the window background, for contrast checks.
    r, g, b, a = t["glass"]
    t["glass_rest"] = mix(QColor(r, g, b).name(), t["bg"], a / 255)
    t["solid_glass"] = prefs.reduce_transparency or prefs.high_contrast
    return t


def stylesheet(t: dict) -> str:
    chevron = icon_file("chevron-down", t["secondary"], 12)
    return f"""
    * {{ font-family: Inter; font-size: 13px; color: {t['label']}; }}
    QMainWindow, #root {{ background: {t['bg']}; }}
    QMenuBar {{ background: {t['bg']}; padding: 2px 4px; }}
    QMenuBar::item {{ background: transparent; padding: 4px 10px; border-radius: 6px; }}
    QMenuBar::item:selected {{ background: {t['select_inactive']}; }}
    QMenu {{ background: {t['surface']}; border: 1px solid {t['border']}; padding: 6px; }}
    QMenu::item {{ padding: 6px 28px 6px 14px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {t['accent']}; color: {t['on_accent']}; }}
    QMenu::item:disabled {{ color: {t['disabled']}; }}
    QMenu::separator {{ height: 1px; background: {t['separator']}; margin: 5px 8px; }}
    QToolButton {{ background: transparent; border: 2px solid transparent; border-radius: 16px; }}
    QToolButton:hover {{ background: rgba({','.join(map(str, t['glass_hover']))}); }}
    QToolButton:focus {{ border-color: {t['focus']}; }}
    QToolButton::menu-indicator {{ image: none; width: 0; }}
    QPushButton {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 15px;
                   padding: 0 16px; min-height: 28px; max-height: 28px; }}
    QPushButton:hover {{ background: {t['hover']}; }}
    QPushButton:focus {{ border: 2px solid {t['focus']}; padding: 0 15px; min-height: 26px; max-height: 26px; }}
    QPushButton#primaryCapsule {{ background: transparent; border: none; padding: 0;
                                  min-height: {40 + 2 * 5}px; max-height: {40 + 2 * 5}px; }}
    QPushButton#toastAction {{ background: transparent; border: none; color: {t['accent_text']};
                               font-weight: 600; padding: 0 8px; }}
    QPushButton#toastAction:focus {{ border: 2px solid {t['focus']}; }}
    QComboBox {{ background: transparent; border: 2px solid transparent; border-radius: 14px;
                 padding: 0 22px 0 8px; min-height: 28px; font-weight: 500; }}
    QComboBox:hover {{ background: rgba({','.join(map(str, t['glass_hover']))}); }}
    QComboBox:focus {{ border-color: {t['focus']}; }}
    QComboBox::drop-down {{ border: none; width: 20px; subcontrol-position: center right; }}
    QComboBox::down-arrow {{ image: url({chevron}); width: 11px; height: 11px; }}
    QComboBox QAbstractItemView {{ background: {t['surface']}; border: 1px solid {t['border']}; padding: 4px;
                                   outline: 0; selection-background-color: {t['accent']};
                                   selection-color: {t['on_accent']}; }}
    #glassLabel {{ color: {t['secondary']}; background: transparent; }}
    #toastText {{ background: transparent; font-weight: 500; }}
    QListView {{ background: transparent; border: none; outline: 0; }}
    #emptyTitle {{ font-size: 20px; font-weight: 600; }}
    #emptyBody {{ color: {t['secondary']}; }}
    #emptyState, #emptyIcon, #emptyTitle, #emptyBody {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: {BAR_HEIGHT}px 2px 6px 2px; }}
    QScrollBar::handle:vertical {{ background: {t['scroll']}; border-radius: 4px; min-height: 32px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """


def _rgba(value) -> QColor:
    return QColor(*value) if isinstance(value, tuple) else QColor(value)


def _blur(image: QImage, passes=((4, 2), (3, 2))) -> QImage:
    """A cheap, smooth blur: shrink in steps, then scale back up."""
    size = image.size()
    small = image
    for factor, _ in passes:
        small = small.scaled(max(1, small.width() // factor), max(1, small.height() // factor),
                             Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return small.scaled(size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


class GlassBar(QWidget):
    """The functional layer along the top: a scroll edge effect over the
    content, and the glass capsules (its children) that sit in it."""

    def __init__(self, t: dict, source_getter, parent=None):
        super().__init__(parent)
        self.t = t
        self.source_getter = source_getter
        self.backdrop = QImage()
        self.setFixedHeight(BAR_HEIGHT)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def capture(self, widget: QWidget) -> QImage:
        """The content beneath ``widget``, blurred, as an image the size of
        the widget."""
        source = self.source_getter()
        window = self.window()
        rect = QRect(widget.mapTo(window, QPoint(0, 0)) - source.mapTo(window, QPoint(0, 0)), widget.size())
        shot = source.grab(rect).toImage()
        dpr = shot.devicePixelRatio()
        shot.setDevicePixelRatio(1)
        base = QImage(shot.size(), QImage.Format_ARGB32_Premultiplied)
        base.fill(QColor(self.t["bg"]))
        painter = QPainter(base)
        painter.drawImage(0, 0, shot)
        painter.end()
        blurred = _blur(base)
        blurred.setDevicePixelRatio(dpr)
        return blurred

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        if self.t["solid_glass"]:
            self.backdrop = QImage()
            p.fillRect(self.rect(), QColor(self.t["bg"]))
            p.setPen(QPen(QColor(self.t["border"]), 1))
            p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
            return
        self.backdrop = self.capture(self)
        # Scroll edge effect: blurred content that fades out downwards,
        # softened with a little of the background colour.
        band = QImage(self.backdrop)
        band.setDevicePixelRatio(self.backdrop.devicePixelRatio())
        bp = QPainter(band)
        bp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        fade = QLinearGradient(0, 0, 0, self.height())
        fade.setColorAt(0.0, QColor(0, 0, 0, 255))
        fade.setColorAt(0.78, QColor(0, 0, 0, 250))
        fade.setColorAt(1.0, QColor(0, 0, 0, 0))
        bp.fillRect(QRect(0, 0, self.width(), self.height()), fade)
        bp.end()
        p.drawImage(0, 0, band)
        tint = QLinearGradient(0, 0, 0, self.height())
        edge = _rgba(self.t["edge_tint"])
        tint.setColorAt(0.0, edge)
        edge.setAlpha(edge.alpha() // 2)
        tint.setColorAt(0.75, edge)
        tint.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), tint)

    def backdrop_origin(self, widget: QWidget) -> QPoint:
        """Where the bar's backdrop starts, in ``widget``'s coordinates."""
        window = self.window()
        return self.mapTo(window, QPoint(0, 0)) - widget.mapTo(window, QPoint(0, 0))


class Capsule(QWidget):
    """A Liquid Glass capsule holding controls. Draws the blurred backdrop
    from its GlassBar, a translucent fill, an inner highlight and a
    hairline edge."""

    PAD = 5  # room around the capsule for its shadow

    def __init__(self, bar: GlassBar, t: dict, parent=None):
        super().__init__(parent)
        self.bar = bar
        self.t = t
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(self.PAD + 4, self.PAD + 2, self.PAD + 4, self.PAD + 2)
        self.row.setSpacing(2)

    def shape_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(self.PAD, self.PAD, -self.PAD, -self.PAD)

    def backdrop(self) -> tuple[QImage, QPoint]:
        return self.bar.backdrop, self.bar.backdrop_origin(self)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        paint_glass(p, self.shape_rect(), self.t, *self.backdrop())


def paint_glass(p: QPainter, r: QRectF, t: dict, backdrop: QImage = QImage(), origin: QPoint = QPoint(),
                fill=None) -> None:
    radius = r.height() / 2
    path = QPainterPath()
    path.addRoundedRect(r, radius, radius)
    # Soft shadow: a few widening, fading outlines.
    for i, alpha in enumerate((0.55, 0.3, 0.15)):
        shadow = QPainterPath()
        grow = 1 + i * 1.5
        shadow.addRoundedRect(r.adjusted(-grow, -grow + 1.5, grow, grow + 1.5), radius + grow, radius + grow)
        c = _rgba(t["glass_shadow"])
        c.setAlphaF(c.alphaF() * alpha)
        p.fillPath(shadow, c)
    if fill is not None:
        p.fillPath(path, QColor(fill))
    elif t["solid_glass"]:
        p.fillPath(path, QColor(t["glass_solid"]))
    else:
        if not backdrop.isNull():
            p.save()
            p.setClipPath(path)
            p.drawImage(origin, backdrop)
            p.restore()
        p.fillPath(path, _rgba(t["glass"]))
    p.setPen(QPen(_rgba(t["glass_edge"]), 1 if not t["solid_glass"] else 1.5))
    p.drawPath(path)
    if fill is None and not t["solid_glass"]:
        inner = QPainterPath()
        inner.addRoundedRect(r.adjusted(1, 1, -1, -1), radius - 1, radius - 1)
        p.setPen(QPen(_rgba(t["glass_highlight"]), 1))
        p.drawPath(inner)


class PrimaryCapsule(QPushButton):
    """The one tinted control: Remove Watermarks. While cleaning it shows
    progress in place ("Cleaning 2 of 5…")."""

    def __init__(self, text: str, t: dict, bar: GlassBar):
        super().__init__(text)
        self.t = t
        self.bar = bar
        self.base_text = text
        self.fraction = None
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(font(13, QFont.DemiBold))
        self.setObjectName("primaryCapsule")
        self.setFixedHeight(40 + 2 * Capsule.PAD)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def sizeHint(self) -> QSize:
        w = QFontMetrics(self.font()).horizontalAdvance("Cleaning 88 of 88…") + 40
        return QSize(max(w, QFontMetrics(self.font()).horizontalAdvance(self.text()) + 44) + 2 * Capsule.PAD,
                     40 + 2 * Capsule.PAD)

    def paintEvent(self, event) -> None:
        t = self.t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(Capsule.PAD, Capsule.PAD, -Capsule.PAD, -Capsule.PAD)
        enabled = self.isEnabled() or self.fraction is not None
        if not enabled:
            paint_glass(p, r, t, self.bar.backdrop, self.bar.backdrop_origin(self))
            p.setPen(QColor(t["disabled"]))
        else:
            color = t["accent_pressed"] if self.isDown() else t["accent_hover"] if self.underMouse() else t["accent"]
            paint_glass(p, r, t, fill=color)
            if self.fraction is not None:
                done = QRectF(r)
                done.setWidth(r.width() * self.fraction)
                path = QPainterPath()
                path.addRoundedRect(r, r.height() / 2, r.height() / 2)
                p.save()
                p.setClipRect(done)
                p.fillPath(path, QColor(t["progress"]))
                p.restore()
            p.setPen(QColor(t["on_accent"]))
        p.setFont(self.font())
        p.drawText(r, Qt.AlignCenter, self.text())
        if self.hasFocus():
            p.setPen(QPen(QColor(t["focus"]), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(-2, -2, 2, 2), r.height() / 2 + 2, r.height() / 2 + 2)

    def set_progress(self, done: int, total: int) -> None:
        self.fraction = done / total if total else 0
        self.setText(f"Cleaning {min(done + 1, total)} of {total}…" if done < total else "Finishing…")
        self.update()

    def reset(self) -> None:
        self.fraction = None
        self.setText(self.base_text)
        self.update()


class Toast(Capsule):
    """A glass message under the bar, with an optional action and a close
    button. It stays until dismissed or the next action."""

    def __init__(self, bar: GlassBar, t: dict, parent=None):
        super().__init__(bar, t, parent)
        self.row.setContentsMargins(self.PAD + 14, self.PAD + 4, self.PAD + 6, self.PAD + 4)
        self.row.setSpacing(8)
        self.icon = QLabel()
        self.icon.setStyleSheet("background: transparent;")
        self.text = QLabel(objectName="toastText")
        self.text.setMaximumWidth(460)
        self.action = QPushButton(objectName="toastAction")
        self.action.setCursor(Qt.PointingHandCursor)
        self._target = None
        self.action.clicked.connect(lambda: self._target and self._target())
        self.close_button = icon_button(icon("x", t["secondary"], 14), "Dismiss", 26)
        for w in (self.icon, self.text, self.action, self.close_button):
            self.row.addWidget(w)
        self.hide()

    def backdrop(self) -> tuple[QImage, QPoint]:
        if self.t["solid_glass"]:
            return QImage(), QPoint()
        return self.bar.capture(self), QPoint(0, 0)

    def show_message(self, text: str, icon_name: str, role: str, action_text: str = "", target=None) -> None:
        self.icon.setPixmap(pixmap(icon_name, self.t[role], 16, 2))
        self.text.setText(text)
        self.text.setAccessibleName(text)
        self.action.setText(action_text)
        self.action.setVisible(bool(action_text))
        self._target = target
        self.show()
        self.raise_()


class _Rows(RowDelegate):
    height = 64

    def __init__(self, view: FileListView, t: dict):
        super().__init__(view)
        self.t = t
        self.name_font = font(14, QFont.Medium)
        self.small_font = font(12)
        self.status_font = font(12, QFont.DemiBold)

    def paint_row(self, p: QPainter, rect: QRect, job: FileJob, row: int, st: dict) -> None:
        t = self.t
        card = QRectF(rect).adjusted(20, 4, -20, -4)
        on_accent = st["selected"] and st["focused"]
        fill = t["accent"] if on_accent else t["select_inactive"] if st["selected"] else \
            t["hover"] if st["hover"] else t["surface"]
        path = QPainterPath()
        path.addRoundedRect(card, 12, 12)
        p.fillPath(path, QColor(fill))
        if not st["selected"]:
            p.setPen(QPen(QColor(t["border"]), 1))
            p.drawPath(path)

        def ink(role: str) -> QColor:
            return QColor(t["on_accent"] if on_accent else t[role])

        tile = QRectF(card.left() + 12, card.center().y() - 18, 36, 36)
        tile_path = QPainterPath()
        tile_path.addRoundedRect(tile, 9, 9)
        p.fillPath(tile_path, QColor(255, 255, 255, 40) if on_accent else QColor(t["accent_tint"]))
        p.drawPixmap(int(tile.left()) + 8, int(tile.top()) + 8,
                     pixmap("file-text", t["on_accent"] if on_accent else t["accent_text"], 20, 1.75))

        status, extra = job.status_text()
        icon_name, role = status_icon(job)
        fm_status, fm_small = QFontMetrics(self.status_font), QFontMetrics(self.small_font)
        status_w = max(fm_status.horizontalAdvance(status) + (20 if icon_name else 0),
                       fm_small.horizontalAdvance(extra))
        right = int(card.right()) - 16
        left = int(tile.right()) + 12
        text_right = right - status_w - 16
        top = int(card.center().y()) - 18

        p.setFont(self.name_font)
        p.setPen(ink("label"))
        p.drawText(QRect(left, top, text_right - left, 19), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(self.name_font).elidedText(job.name, Qt.ElideRight, text_right - left))
        line, is_error = second_line(job)
        mode = Qt.ElideRight if is_error or job.status is Status.UNCHANGED else Qt.ElideMiddle
        p.setFont(self.small_font)
        p.setPen(ink("danger" if is_error else "secondary"))
        p.drawText(QRect(left, top + 21, text_right - left, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   fm_small.elidedText(line, mode, text_right - left))

        p.setFont(self.status_font)
        p.setPen(ink(role))
        status_top = top + (0 if extra else 9)
        p.drawText(QRect(right - status_w, status_top, status_w, 19), Qt.AlignRight | Qt.AlignVCenter, status)
        if icon_name:
            p.drawPixmap(right - fm_status.horizontalAdvance(status) - 20, status_top + 2,
                         pixmap(icon_name, ink(role).name(), 15, 2))
        if extra:
            p.setFont(self.small_font)
            p.setPen(ink("secondary"))
            p.drawText(QRect(right - status_w, top + 21, status_w, 16), Qt.AlignRight | Qt.AlignVCenter, extra)


class DropWell(QWidget):
    """The empty state: a dashed well that lights up while PDFs are dragged
    over the window."""

    def __init__(self, t: dict, inner: QWidget):
        super().__init__()
        self.t = t
        self.active = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(inner)
        self.setMinimumSize(420, 280)
        self.setMaximumSize(600, 340)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        if self.active:
            p.setBrush(QColor(self.t["accent_tint"]))
            p.setPen(QPen(QColor(self.t["accent"]), 2))
        else:
            p.setBrush(QColor(self.t["surface"]))
            pen = QPen(QColor(self.t["secondary"]), 1.5)
            pen.setDashPattern([4, 4])
            p.setPen(pen)
        p.drawRoundedRect(r, 20, 20)


class AppleGlassWindow(BaseWindow):
    NAME = "Apple Liquid Glass"
    TITLE_CASE = True
    DEFAULT_SIZE = (800, 580)

    def build(self) -> None:
        t = self.t = tokens(self.prefs)
        L = self.labels
        set_palette(self, t)
        self.setStyleSheet(stylesheet(t))
        self.fill_menu_bar()
        self.menuBar().hide()  # tap Alt to show it, as in other Windows apps
        QApplication.instance().installEventFilter(self)
        self._alt_alone = False

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        grid = QGridLayout(root)
        grid.setContentsMargins(0, 0, 0, 0)

        # Content layer.
        self.stack = QStackedWidget()
        choose = QPushButton(L.choose_files)
        bind(choose, self.act_add_files)
        inner = EmptyState(pixmap("upload", t["accent_text"], 40, 1.75), "Drop PDFs Here",
                           "Or choose files to clean. Each cleaned copy is saved as name_clean.pdf; "
                           "the originals stay unchanged.", choose, width=360)
        self.well = DropWell(t, inner)
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.setContentsMargins(24, BAR_HEIGHT + 8, 24, 24)
        empty_layout.addWidget(self.well, 0, Qt.AlignCenter)
        self.list_view = FileListView(self.controller.model)
        self.list_view.top_inset = BAR_HEIGHT + 4
        self.list_view.bottom_inset = 16
        self.list_view.setItemDelegate(_Rows(self.list_view, t))
        self.stack.addWidget(empty_page)
        self.stack.addWidget(self.list_view)
        grid.addWidget(self.stack, 0, 0)

        # Functional layer: the glass bar and its capsules.
        self.bar = GlassBar(t, lambda: self.stack.currentWidget() if self.stack.currentIndex() == 0
                            else self.list_view.viewport())
        bar_row = QHBoxLayout(self.bar)
        bar_row.setContentsMargins(11, 11, 11, 11)
        bar_row.setSpacing(4)
        tools = Capsule(self.bar, t)
        for name, act in (("file-plus", self.act_add_files), ("folder-plus", self.act_add_folder)):
            button = icon_button(icon(name, t["label"], 18, 1.75, t["disabled"]), act.toolTip(), 32)
            bind(button, act)
            tools.row.addWidget(button)
        more = icon_button(icon("ellipsis", t["label"], 18, 2), "More", 32)
        more_menu = QMenu(self)
        more_menu.addActions([self.act_open_pdf, self.act_show])
        more_menu.addSeparator()
        more_menu.addActions([self.act_remove, self.act_clear])
        more_menu.addSeparator()
        designs = more_menu.addMenu("Prototype")
        designs.addActions(self.act_designs)
        more_menu.addAction(self.act_about)
        more.setMenu(more_menu)
        more.setPopupMode(QToolButton.InstantPopup)
        tools.row.addWidget(more)
        bar_row.addWidget(tools)
        bar_row.addStretch(1)
        output = Capsule(self.bar, t)
        output.row.setContentsMargins(Capsule.PAD + 14, Capsule.PAD + 4, Capsule.PAD + 4, Capsule.PAD + 4)
        output.row.addWidget(QLabel("Save To", objectName="glassLabel"))
        output.row.addWidget(OutputPicker(self.controller, L))
        bar_row.addWidget(output)
        self.primary = PrimaryCapsule(L.run, t, self.bar)
        bind(self.primary, self.act_run)
        bar_row.addWidget(self.primary)
        grid.addWidget(self.bar, 0, 0, Qt.AlignTop)

        # The message floats just under the bar; placed by hand so it never
        # covers (and blocks clicks on) the bar itself.
        self.toast = Toast(self.bar, t, root)
        self.toast.close_button.clicked.connect(self._hide_toast)
        self.bar.raise_()

        self.list_view.verticalScrollBar().valueChanged.connect(self.bar.update)
        self.stack.currentChanged.connect(lambda *_: self.bar.update())

    # The menu bar appears when Alt is tapped on its own.
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not self.isActiveWindow():
            return False
        if event.type() == QEvent.KeyPress:
            self._alt_alone = event.key() == Qt.Key_Alt and not event.isAutoRepeat()
        elif event.type() == QEvent.KeyRelease and event.key() == Qt.Key_Alt and self._alt_alone:
            self._alt_alone = False
            self.menuBar().setVisible(not self.menuBar().isVisible())
        elif event.type() == QEvent.MouseButtonPress and self.menuBar().isVisible() \
                and isinstance(obj, QWidget) and obj.window() is self and not self.menuBar().isAncestorOf(obj) \
                and obj is not self.menuBar():
            self.menuBar().hide()
        return False

    def update_view(self) -> None:
        self.stack.setCurrentIndex(1 if self.controller.jobs else 0)
        if not self.controller.running:
            self.primary.reset()
        self.bar.update()

    def on_progress(self, done: int, total: int) -> None:
        self._hide_toast()
        self.primary.set_progress(done, total)

    def on_finished(self, summary: RunSummary) -> None:
        self.primary.reset()
        if summary.failed:
            kind = ("circle-x", "danger") if not summary.cleaned else ("triangle-alert", "warning")
        else:
            kind = ("circle-check", "success")
        action = self.labels.show if summary.outputs else ""
        self.toast.show_message(summary.text(), *kind, action,
                                lambda: self.controller.show_outputs(self.list_view.selected_rows()))
        self._place_toast()

    def notify(self, text: str, kind: str = "info") -> None:
        names = {"success": ("circle-check", "success"), "warning": ("triangle-alert", "warning"),
                 "error": ("circle-x", "danger"), "info": ("info", "accent_text")}
        self.toast.show_message(text, *names.get(kind, names["info"]))
        self._place_toast()

    def add_paths(self, paths) -> None:
        self._hide_toast()
        super().add_paths(paths)

    def set_drop_active(self, active: bool) -> None:
        self.well.active = active
        self.well.update()

    def _place_toast(self) -> None:
        self.toast.adjustSize()
        width = min(self.toast.sizeHint().width(), self.centralWidget().width() - 32)
        height = self.toast.sizeHint().height()
        self.toast.resize(width, height)
        self.toast.move((self.centralWidget().width() - width) // 2, BAR_HEIGHT - 8)
        self.toast.raise_()
        # Keep the resting content clear of the message.
        self._set_inset(BAR_HEIGHT - 8 + height)

    def _hide_toast(self) -> None:
        self.toast.hide()
        self._set_inset(BAR_HEIGHT + 4)

    def _set_inset(self, inset: int) -> None:
        if self.list_view.top_inset != inset:
            self.list_view.top_inset = inset
            self.list_view.doItemsLayout()
            self.list_view.viewport().update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.bar.update()
        if self.toast.isVisible():
            self._place_toast()

    def closeEvent(self, event) -> None:
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)
