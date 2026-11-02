"""Widgets every design shares, styled differently by each."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QEasingCurve, QModelIndex, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QGraphicsOpacityEffect,
    QLabel,
    QListView,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .controller import JOB_ROLE, Controller
from .model import FileJob, Status
from .theme import pixmap


class Labels:
    """Every visible label, in title case (Apple) or sentence case."""

    def __init__(self, title_case: bool):
        t = (lambda title, sentence: title) if title_case else (lambda title, sentence: sentence)
        self.add_files = t("Add Files…", "Add files…")
        self.add_folder = t("Add Folder…", "Add folder…")
        self.remove = t("Remove from List", "Remove from list")
        self.clear = t("Clear List", "Clear list")
        self.run = t("Remove Watermarks", "Remove watermarks")
        self.show = t("Show in Folder", "Show in folder")
        self.open_pdf = t("Open Cleaned PDF", "Open cleaned PDF")
        self.next_to = t("Next to Originals", "Next to the originals")
        self.choose_folder = t("Choose Folder…", "Choose folder…")
        self.choose_files = t("Choose Files…", "Choose files…")
        self.save_to = t("Save To:", "Save to")
        self.settings = "Settings…"
        self.exit = "Exit"
        self.about = t("About SenAI Watermark Remover", "About SenAI Watermark Remover")
        self.title_case = title_case


class FileListView(QListView):
    """The list of PDFs. ``top_inset`` leaves room for a floating toolbar
    while still letting rows scroll beneath it."""

    def __init__(self, model, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setModel(model)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QListView.NoFrame)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAccessibleName("PDFs to clean")
        self.setUniformItemSizes(False)
        self.viewport().setAutoFillBackground(False)
        self.top_inset = 0
        self.bottom_inset = 0
        # Paints behind the rows; given (painter, viewport rect, scroll offset).
        self.backdrop: Optional[Callable[[QPainter, QRect, int], None]] = None

    def selected_rows(self) -> list[int]:
        return sorted(index.row() for index in self.selectionModel().selectedRows())

    def paintEvent(self, event) -> None:
        if self.backdrop is not None:
            painter = QPainter(self.viewport())
            self.backdrop(painter, self.viewport().rect(), self.verticalScrollBar().value())
            painter.end()
        super().paintEvent(event)

    def mousePressEvent(self, event) -> None:
        # Clicks in the inset above the first row (under a floating bar)
        # or below the last shouldn't select anything.
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and not self._row_body(index).contains(event.position().toPoint()):
            self.clearSelection()
            return
        super().mousePressEvent(event)

    def _row_body(self, index: QModelIndex) -> QRect:
        rect = self.visualRect(index)
        if index.row() == 0:
            rect.setTop(rect.top() + self.top_inset)
        if index.row() == self.model().rowCount() - 1:
            rect.setBottom(rect.bottom() - self.bottom_inset)
        return rect


class RowDelegate(QStyledItemDelegate):
    """Base for each design's row painter: handles the insets and hands the
    design the job, its body rectangle and the row's state."""

    height = 48

    def __init__(self, view: FileListView):
        super().__init__(view)
        self.view = view

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        h = self.height
        if index.row() == 0:
            h += self.view.top_inset
        if index.row() == index.model().rowCount() - 1:
            h += self.view.bottom_inset
        return QSize(max(option.rect.width(), 200), h)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        job: FileJob = index.data(JOB_ROLE)
        if job is None:
            return
        rect = QRect(option.rect)
        if index.row() == 0:
            rect.setTop(rect.top() + self.view.top_inset)
        if index.row() == index.model().rowCount() - 1:
            rect.setBottom(rect.bottom() - self.view.bottom_inset)
        state = option.state
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        self.paint_row(painter, rect, job, index.row(), {
            "selected": bool(state & QStyle.StateFlag.State_Selected),
            "focused": self.view.hasFocus() and self.view.isActiveWindow(),
            "hover": bool(state & QStyle.StateFlag.State_MouseOver),
            "last": index.row() == index.model().rowCount() - 1,
        })
        painter.restore()

    def paint_row(self, painter: QPainter, rect: QRect, job: FileJob, row: int, state: dict) -> None:
        raise NotImplementedError


def status_icon(job: FileJob) -> tuple[str, str]:
    """(icon name, colour role) for a job's status."""
    if job.status is Status.CLEANED:
        return ("triangle-alert", "warning") if job.warnings else ("circle-check", "success")
    if job.status is Status.FAILED:
        return "circle-x", "danger"
    if job.status is Status.UNCHANGED:
        return "check", "secondary"
    if job.status is Status.WORKING:
        return "loader-circle", "accent_text"
    return "", "secondary"


def second_line(job: FileJob) -> tuple[str, bool]:
    """Text under the file name: the failure reason, or else its folder.
    The flag says whether it's an error."""
    if job.status is Status.FAILED:
        return job.message, True
    if job.status is Status.UNCHANGED:
        return job.message, False
    return str(job.folder), False


def font(size: float, weight: QFont.Weight = QFont.Normal, family: str = "Inter",
         families: Optional[list[str]] = None) -> QFont:
    f = QFont(family)
    if families:
        f.setFamilies(families)
    f.setPixelSize(round(size))
    f.setWeight(weight)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


class OutputPicker(QComboBox):
    """Pop-up button for where cleaned copies go: next to the originals, a
    folder chosen earlier, or Choose Folder…"""

    CHOOSE = "__choose__"

    def __init__(self, controller: Controller, labels: Labels, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.controller = controller
        self.labels = labels
        self.setAccessibleName("Save cleaned copies to")
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.setMaximumWidth(280)
        self.activated.connect(self._chosen)
        controller.output_changed.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        self.blockSignals(True)
        self.clear()
        self.addItem(self.labels.next_to, None)
        self.setItemData(0, "Save each cleaned copy in the same folder as its original", Qt.ToolTipRole)
        folder = self.controller.output_dir
        if folder is not None:
            self.addItem(folder.name or str(folder), str(folder))
            self.setItemData(1, str(folder), Qt.ToolTipRole)
        self.insertSeparator(self.count())
        self.addItem(self.labels.choose_folder, self.CHOOSE)
        self.setCurrentIndex(1 if folder is not None else 0)
        self.setToolTip(str(folder) if folder is not None else self.itemData(0, Qt.ToolTipRole))
        self.blockSignals(False)

    def _chosen(self, index: int) -> None:
        data = self.itemData(index)
        if data == self.CHOOSE:
            start = self.controller.output_dir or self.controller.last_dir
            folder = QFileDialog.getExistingDirectory(
                self.window(), "Choose where to save cleaned PDFs", str(start)
            )
            if folder:
                self.controller.set_output_dir(Path(folder))
            else:
                self._sync()
        elif data is None:
            self.controller.set_output_dir(None)
        else:
            self.controller.set_output_dir(Path(data))


class EmptyState(QWidget):
    """Shown instead of the list until PDFs are added."""

    def __init__(self, icon_pixmap, title: str, body: str, button: Optional[QPushButton] = None,
                 parent: Optional[QWidget] = None, width: int = 340):
        super().__init__(parent)
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        self.icon = QLabel()
        self.icon.setObjectName("emptyIcon")
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setPixmap(icon_pixmap)
        self.title = QLabel(title)
        self.title.setObjectName("emptyTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.body = QLabel(body)
        self.body.setObjectName("emptyBody")
        self.body.setAlignment(Qt.AlignCenter)
        self.body.setWordWrap(True)
        self.body.setFixedWidth(width)
        layout.addWidget(self.icon, 0, Qt.AlignHCenter)
        layout.addSpacing(14)
        layout.addWidget(self.title, 0, Qt.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(self.body, 0, Qt.AlignHCenter)
        if button is not None:
            layout.addSpacing(18)
            layout.addWidget(button, 0, Qt.AlignHCenter)


def icon_button(icon, tooltip: str, size: int = 28, parent: Optional[QWidget] = None) -> QToolButton:
    """A borderless, icon-only button with a tooltip and accessible name."""
    button = QToolButton(parent)
    button.setIcon(icon)
    button.setIconSize(QSize(18, 18))
    button.setFixedSize(size, size)
    button.setToolTip(tooltip)
    button.setAccessibleName(tooltip.split(" (")[0])
    button.setAutoRaise(True)
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.StrongFocus)
    return button


def set_palette(widget: QWidget, colors: dict) -> None:
    """Fill the standard palette roles from a design's tokens so native
    parts (scroll bars, menus, text selection) match."""
    palette = widget.palette()
    pairs = {
        QPalette.Window: colors["bg"],
        QPalette.WindowText: colors["label"],
        QPalette.Base: colors["surface"],
        QPalette.AlternateBase: colors["surface"],
        QPalette.Text: colors["label"],
        QPalette.Button: colors["surface"],
        QPalette.ButtonText: colors["label"],
        QPalette.Highlight: colors["accent"],
        QPalette.HighlightedText: colors["on_accent"],
        QPalette.ToolTipBase: colors["surface"],
        QPalette.ToolTipText: colors["label"],
        QPalette.PlaceholderText: colors["secondary"],
        QPalette.Link: colors["accent_text"],
    }
    for role, value in pairs.items():
        palette.setColor(role, QColor(value))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        palette.setColor(QPalette.Disabled, role, QColor(colors["disabled"]))
    widget.setPalette(palette)


class DropVeil(QWidget):
    """Full-window hint while PDFs are dragged over any theme.

    Mouse events pass through, so the window still receives the drop.
    With motion off it appears and disappears at once.
    """

    def __init__(self, window):
        super().__init__(window.centralWidget())
        self._window = window
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._anim = None
        self.hide()

    def present(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setGeometry(parent.rect())
        self.raise_()
        self.show()
        self._fade(1.0)

    def dismiss(self) -> None:
        if not self.isVisible():
            return
        self._fade(0.0, hide=True)

    def _fade(self, end: float, hide: bool = False) -> None:
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        if not self._window.prefs.animations:
            self._effect.setOpacity(end)
            if hide:
                self.hide()
            return
        anim = QPropertyAnimation(self._effect, b"opacity", self)
        anim.setDuration(160)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(self._effect.opacity())
        anim.setEndValue(end)
        if hide:
            anim.finished.connect(self._hide_if_faded)
        anim.start()
        self._anim = anim

    def _hide_if_faded(self) -> None:
        if self._effect.opacity() < 0.05:
            self.hide()

    def paintEvent(self, event) -> None:
        t = self._window.t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        shade = QColor(t["bg"])
        shade.setAlpha(214)
        p.fillRect(self.rect(), shade)

        card = QRectF(0, 0, min(440, self.width() - 48), 188)
        card.moveCenter(QPointF(self.rect().center()))
        path = QPainterPath()
        path.addRoundedRect(card, 20, 20)
        p.fillPath(path, QColor(t["surface"]))
        p.setPen(QPen(QColor(t["accent"]), 2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        icon = pixmap("upload", t["accent_text"], 36, 1.75)
        p.drawPixmap(int(card.center().x() - 18), int(card.top() + 26), icon)
        p.setPen(QColor(t["label"]))
        p.setFont(font(20, QFont.DemiBold))
        p.drawText(QRectF(card.left() + 24, card.top() + 76, card.width() - 48, 30),
                   Qt.AlignHCenter | Qt.AlignVCenter, "Drop PDFs here")
        p.setPen(QColor(t["secondary"]))
        p.setFont(font(13))
        p.drawText(QRectF(card.left() + 28, card.top() + 112, card.width() - 56, 52),
                   Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                   "Files and folders join the list. Nothing is cleaned until you ask.")


def bind(button, action: QAction) -> None:
    """Make a button run an action and follow its enabled state."""
    button.clicked.connect(action.trigger)
    button.setEnabled(action.isEnabled())
    action.changed.connect(lambda: button.setEnabled(action.isEnabled()))
    if not button.toolTip():
        button.setToolTip(action.toolTip())
