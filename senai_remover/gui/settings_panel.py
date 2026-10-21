"""The settings bar: slides in from the right of any theme, with the four
themes as preview cards and the appearance choice. Picking a theme
restyles the window straight away and keeps the bar open, so people can
compare themes; the file list and results carry over."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .theme import ASSETS, icon, mix, pixmap
from .widgets import font, icon_button

if TYPE_CHECKING:
    from .designs.base import BaseWindow

PANEL_WIDTH = 368
CARD_WIDTH = 156
PREVIEW_HEIGHT = 106  # the screenshots' 880 x 600 aspect ratio


def preview(theme_id: str, dark: bool) -> QPixmap:
    """The theme's preview image, or an empty pixmap if it's missing."""
    path = ASSETS / "previews" / f"{theme_id}-{'dark' if dark else 'light'}.png"
    pm = QPixmap(str(path))
    if not pm.isNull():
        pm.setDevicePixelRatio(pm.width() / CARD_WIDTH)
    return pm


class ThemeCard(QAbstractButton):
    def __init__(self, design, image: QPixmap, t: dict, parent=None):
        super().__init__(parent)
        self.t = t
        self.image = image
        self.name = design.NAME
        self.description = design.DESCRIPTION
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName(f"{self.name} theme")
        self.setAccessibleDescription(self.description)
        self.setToolTip(self.description)
        self.setFixedSize(self.sizeHint())
        self.name_font = font(13, QFont.DemiBold)
        self.text_font = font(12)

    def sizeHint(self) -> QSize:
        return QSize(CARD_WIDTH + 4, PREVIEW_HEIGHT + 66)

    def paintEvent(self, event) -> None:
        t = self.t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if not self.isEnabled():
            p.setOpacity(0.45)
        card = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(card, 10, 10)
        hovered = self.underMouse() and self.isEnabled()
        p.fillPath(path, QColor(mix(t["label"], t["surface"], 0.06 if hovered else 0.03)))
        p.setPen(QPen(QColor(t["accent"]), 2) if self.isChecked() else QPen(QColor(t["border"]), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        shot = QRectF(card.left() + 6, card.top() + 6, card.width() - 12, PREVIEW_HEIGHT - 12 + 4)
        clip = QPainterPath()
        clip.addRoundedRect(shot, 6, 6)
        p.save()
        p.setClipPath(clip)
        if self.image.isNull():
            p.fillRect(shot, QColor(t["bg"]))
        else:
            p.drawPixmap(shot, self.image, QRectF(self.image.rect()))
        p.restore()
        p.setPen(QPen(QColor(t["border"]), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(shot, 6, 6)

        if self.isChecked():
            badge = QRectF(shot.right() - 26, shot.top() + 6, 20, 20)
            p.setPen(QPen(QColor(t["surface"]), 2))
            p.setBrush(QColor(t["accent"]))
            p.drawEllipse(badge)
            p.drawPixmap(int(badge.left()) + 4, int(badge.top()) + 4, pixmap("check", t["on_accent"], 12, 3))

        text = QRect(int(card.left()) + 8, int(shot.bottom()) + 8, int(card.width()) - 16, 18)
        p.setPen(QColor(t["label"]))
        p.setFont(self.name_font)
        p.drawText(text, Qt.AlignLeft | Qt.AlignVCenter, self.name)
        p.setPen(QColor(t["secondary"]))
        p.setFont(self.text_font)
        p.drawText(QRect(text.left(), text.bottom() + 2, text.width(), 32),
                   Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.description)

        if self.hasFocus():
            p.setOpacity(1)
            p.setPen(QPen(QColor(t["accent"]), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(card.adjusted(-1, -1, 1, 1), 11, 11)


class _Scrim(QWidget):
    """Dims the window behind the bar and closes it when clicked. Also
    draws the bar's shadow along its left edge."""

    clicked = Signal()

    def __init__(self, parent: QWidget, dark: bool):
        super().__init__(parent)
        self.dim = QColor(0, 0, 0, 110 if dark else 46)
        self.edge = 0
        self.setAccessibleName("Close settings")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), self.dim)
        shadow = QLinearGradient(self.edge - 18, 0, self.edge, 0)
        shadow.setColorAt(0, QColor(0, 0, 0, 0))
        shadow.setColorAt(1, QColor(0, 0, 0, 60))
        p.fillRect(QRect(self.edge - 18, 0, 18, self.height()), shadow)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()


class SettingsPanel(QFrame):
    def __init__(self, window: "BaseWindow"):
        host = window.centralWidget()
        super().__init__(host)
        self.window_ = window
        self.host = host
        t = window.t
        L = window.labels
        title = (lambda a, b: a) if L.title_case else (lambda a, b: b)
        self.setObjectName("settingsPanel")
        self.setAccessibleName("Settings")
        self.setStyleSheet(_stylesheet(t))
        self.scrim = _Scrim(host, window.prefs.dark)
        self.scrim.clicked.connect(self.close_panel)
        self.scrim.hide()
        self.hide()

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(22, 18, 14, 10)
        heading = QLabel("Settings", objectName="settingsTitle")
        header.addWidget(heading)
        header.addStretch(1)
        close = icon_button(icon("x", t["label"], 16, 2), "Close settings (Esc)", 30)
        close.setObjectName("settingsClose")
        close.clicked.connect(self.close_panel)
        header.addWidget(close)
        self.close_button = close
        column.addLayout(header)

        body = QWidget(objectName="settingsBody")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        column.addWidget(scroll, 1)
        content = QVBoxLayout(body)
        content.setContentsMargins(20, 4, 20, 20)
        content.setSpacing(0)

        content.addWidget(QLabel("Theme", objectName="settingsSection"))
        content.addSpacing(10)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        # Not exclusive: Qt would treat an exclusive group like radio buttons,
        # where Tab skips to the next control. Only one card is ever checked,
        # because picking one rebuilds the window.
        self.cards = QButtonGroup(self)
        self.cards.setExclusive(False)
        shell = window.shell
        for i, design in enumerate(shell.designs):
            card = ThemeCard(design, preview(design.ID, window.prefs.dark), t)
            card.setChecked(i == window.design_index)
            card.clicked.connect(lambda _=False, i=i, card=card: self._pick_theme(i, card))
            self.cards.addButton(card, i)
            grid.addWidget(card, i // 2, i % 2)
        content.addLayout(grid)
        content.addSpacing(6)
        self.busy_note = QLabel("You can change these after cleaning finishes.", objectName="settingsNote")
        self.busy_note.setWordWrap(True)
        content.addWidget(self.busy_note)

        content.addSpacing(18)
        content.addWidget(QLabel("Appearance", objectName="settingsSection"))
        content.addSpacing(10)
        segments = QFrame(objectName="segments")
        seg_row = QHBoxLayout(segments)
        seg_row.setContentsMargins(3, 3, 3, 3)
        seg_row.setSpacing(3)
        self.appearance = QButtonGroup(self)
        self.appearance.setExclusive(False)
        for mode, text in (("system", title("Match System", "Match system")), ("light", "Light"), ("dark", "Dark")):
            button = QPushButton(text, objectName="segment")
            button.setCheckable(True)
            button.setChecked(mode == shell.settings.appearance)
            button.setCursor(Qt.PointingHandCursor)
            button.setAccessibleName(f"Appearance: {text}")
            button.clicked.connect(lambda _=False, mode=mode, button=button: self._pick_appearance(mode, button))
            self.appearance.addButton(button)
            seg_row.addWidget(button, 1)
        content.addWidget(segments)
        content.addSpacing(8)
        note = QLabel("Match system follows Windows' light or dark setting.", objectName="settingsNote")
        note.setWordWrap(True)
        content.addWidget(note)
        content.addStretch(1)
        saved = QLabel("Your choices are saved for next time.", objectName="settingsNote")
        saved.setWordWrap(True)
        content.addSpacing(16)
        content.addWidget(saved)

        escape = QShortcut(QKeySequence(Qt.Key_Escape), self)
        escape.setContext(Qt.WidgetWithChildrenShortcut)
        escape.activated.connect(self.close_panel)
        host.installEventFilter(self)
        window.controller.running_changed.connect(self._sync_enabled)
        self._sync_enabled()
        self._animation = None

    # Showing and hiding ------------------------------------------------------

    def open(self, animate: bool = True, focus: str = "theme") -> None:
        self._place()
        self.scrim.show()
        self.scrim.raise_()
        self.show()
        self.raise_()
        if animate and self.window_.prefs.animations:
            end = self.pos()
            self._animation = QPropertyAnimation(self, b"pos", self)
            self._animation.setDuration(170)
            self._animation.setEasingCurve(QEasingCurve.OutCubic)
            self._animation.setStartValue(QPoint(end.x() + 40, end.y()))
            self._animation.setEndValue(end)
            self._animation.start()
        target = self.checked(self.appearance if focus == "appearance" else self.cards)
        (target or self).setFocus(Qt.OtherFocusReason)

    @staticmethod
    def checked(group: QButtonGroup):
        """The checked button (QButtonGroup only tracks it when exclusive)."""
        return next((b for b in group.buttons() if b.isChecked()), None)

    def close_panel(self) -> None:
        self.hide()
        self.scrim.hide()
        self.window_.list_view.setFocus(Qt.OtherFocusReason)

    @property
    def is_open(self) -> bool:
        return self.isVisible()

    def _place(self) -> None:
        width = min(PANEL_WIDTH, max(self.host.width() - 40, 240))
        self.setGeometry(self.host.width() - width, 0, width, self.host.height())
        self.scrim.setGeometry(self.host.rect())
        self.scrim.edge = self.host.width() - width

    def eventFilter(self, obj, event) -> bool:
        if obj is self.host and event.type() == QEvent.Resize and self.isVisible():
            self._place()
        return False

    # Choices -----------------------------------------------------------------

    def _sync_enabled(self, *_) -> None:
        running = self.window_.controller.running
        for button in self.cards.buttons() + self.appearance.buttons():
            button.setEnabled(not running)
        self.busy_note.setVisible(running)

    def _pick_theme(self, index: int, card: QAbstractButton) -> None:
        if index == self.window_.design_index:
            card.setChecked(True)  # clicking the current theme keeps it chosen
        else:
            self.window_.shell.switch(index, settings_open=True)

    def _pick_appearance(self, mode: str, button: QAbstractButton) -> None:
        if mode == self.window_.shell.settings.appearance:
            button.setChecked(True)
        else:
            self.window_.shell.set_appearance(mode)

    # Keyboard: Tab and Shift+Tab cycle through the bar and never leave it
    # for the dimmed window behind.

    def focus_chain(self) -> list:
        chain = [self.close_button, *self.cards.buttons(), *self.appearance.buttons()]
        return [w for w in chain if w.isEnabled() and w.isVisibleTo(self)]

    def focusNextPrevChild(self, next: bool) -> bool:
        chain = self.focus_chain()
        if not chain:
            return super().focusNextPrevChild(next)
        current = QApplication.focusWidget()
        index = chain.index(current) if current in chain else -1
        target = chain[(index + (1 if next else -1)) % len(chain)]
        target.setFocus(Qt.TabFocusReason if next else Qt.BacktabFocusReason)
        return True


def _stylesheet(t: dict) -> str:
    return f"""
    #settingsPanel {{ background: {t['surface']}; border: none; border-left: 1px solid {t['border']}; }}
    #settingsBody, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {t['surface']}; }}
    #settingsPanel QLabel {{ background: transparent; font-family: Inter; }}
    #settingsTitle {{ color: {t['label']}; font-size: 18px; font-weight: 600; }}
    #settingsSection {{ color: {t['label']}; font-size: 13px; font-weight: 600; }}
    #settingsNote {{ color: {t['secondary']}; font-size: 12px; }}
    #settingsClose {{ background: transparent; border: 2px solid transparent; border-radius: 15px; }}
    #settingsClose:hover {{ background: {mix(t['label'], t['surface'], 0.08)}; }}
    #settingsClose:focus {{ border-color: {t['accent']}; }}
    #segments {{ background: {mix(t['label'], t['surface'], 0.06)}; border: 1px solid {t['border']};
                 border-radius: 8px; }}
    QPushButton#segment {{ background: transparent; color: {t['label']}; border: 2px solid transparent;
                           border-radius: 6px; padding: 5px 4px; font-family: Inter; font-size: 13px;
                           min-height: 20px; max-height: 20px; }}
    QPushButton#segment:hover {{ background: {mix(t['label'], t['surface'], 0.08)}; }}
    QPushButton#segment:checked {{ background: {t['accent']}; color: {t['on_accent']}; font-weight: 600; }}
    QPushButton#segment:focus {{ border-color: {mix(t['accent'], t['label'], 0.6)}; }}
    QPushButton#segment:disabled {{ color: {t['disabled']}; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {mix(t['label'], t['surface'], 0.25)}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    """
