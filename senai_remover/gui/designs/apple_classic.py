"""Theme 1, Apple Classic: a Mac-style window following Apple's Human
Interface Guidelines.

- A menu bar that holds every command (the-menu-bar.md, toolbars.md).
- A toolbar of symbol buttons, with one prominent action, Remove
  Watermarks, on its trailing side (toolbars.md › Actions; buttons.md › Style).
- An inset list whose selected row takes the accent colour when the list
  has focus and grey when it doesn't (focus-and-selection.md).
- A bottom status bar holding only a count and progress, never actions
  (windows.md › Desktop).
- 13 px body text, 28 px controls, title-style capitalisation on buttons
  and menu items (typography.md, accessibility.md, buttons.md › Content).
- Light and dark colours from Apple's system palette, each text pair at
  4.5:1 or more; no app-specific appearance switch (dark-mode.md).
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..model import FileJob, RunSummary, Status, plural
from ..theme import Prefs, icon, icon_file, pixmap
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
    "bg": "#F5F5F7", "chrome": "#ECECEE", "surface": "#FFFFFF",
    "border": "#D2D2D7", "separator": "#E5E5EA",
    "label": "#1D1D1F", "secondary": "#636366", "disabled": "#A1A1A6",
    "accent": "#0071E3", "accent_hover": "#0068D1", "accent_pressed": "#005BB8", "on_accent": "#FFFFFF",
    "accent_text": "#0066CC", "accent_tint": "#E8F1FC",
    "success": "#1F7A35", "warning": "#C93400", "danger": "#D70015",
    "select_inactive": "#E3E3E8", "hover": "#F0F0F3", "chrome_hover": "#DEDEE2", "chrome_pressed": "#D2D2D7",
    "focus": "#7AB6F2", "scroll": "rgba(0,0,0,0.28)",
}
DARK = {
    "bg": "#1C1C1E", "chrome": "#262628", "surface": "#2C2C2E",
    "border": "#3A3A3C", "separator": "#38383A",
    "label": "#F5F5F7", "secondary": "#AEAEB2", "disabled": "#636366",
    "accent": "#0071E3", "accent_hover": "#0A7CF0", "accent_pressed": "#0062C4", "on_accent": "#FFFFFF",
    "accent_text": "#409CFF", "accent_tint": "#13304F",
    "success": "#30D158", "warning": "#FF9F0A", "danger": "#FF6961",
    "select_inactive": "#3A3A3C", "hover": "#323234", "chrome_hover": "#343437", "chrome_pressed": "#3E3E41",
    "focus": "#2E86E8", "scroll": "rgba(255,255,255,0.30)",
}
# (text, background, minimum ratio) pairs the tests check in both appearances.
CONTRAST = [
    ("label", "surface", 4.5), ("label", "bg", 4.5), ("label", "chrome", 4.5),
    ("secondary", "surface", 4.5), ("secondary", "bg", 4.5), ("secondary", "chrome", 4.5),
    ("secondary", "hover", 4.5), ("secondary", "select_inactive", 4.5),
    ("label", "select_inactive", 4.5), ("on_accent", "accent", 4.5),
    ("accent_text", "surface", 4.5), ("success", "surface", 4.5),
    ("warning", "surface", 4.5), ("danger", "surface", 4.5), ("danger", "hover", 4.5),
    ("label", "accent_tint", 4.5), ("secondary", "accent_tint", 4.5),
]


def tokens(prefs: Prefs) -> dict:
    t = dict(DARK if prefs.dark else LIGHT)
    if prefs.high_contrast:
        t.update(secondary=t["label"], border=t["label"], separator=t["secondary"])
    return t


def stylesheet(t: dict) -> str:
    chevrons = icon_file("chevrons-up-down", t["secondary"], 12)
    return f"""
    * {{ font-family: Inter; font-size: 13px; color: {t['label']}; }}
    QMainWindow, #root {{ background: {t['bg']}; }}
    QMenuBar {{ background: {t['chrome']}; padding: 2px 4px; }}
    QMenuBar::item {{ background: transparent; padding: 4px 10px; border-radius: 5px; }}
    QMenuBar::item:selected {{ background: {t['chrome_hover']}; }}
    QMenu {{ background: {t['surface']}; border: 1px solid {t['border']}; padding: 5px; }}
    QMenu::item {{ padding: 5px 28px 5px 14px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {t['accent']}; color: {t['on_accent']}; }}
    QMenu::item:disabled {{ color: {t['disabled']}; }}
    QMenu::separator {{ height: 1px; background: {t['separator']}; margin: 5px 8px; }}
    QMenu::indicator {{ width: 14px; height: 14px; left: 6px; }}
    #toolbar {{ background: {t['chrome']}; border-bottom: 1px solid {t['border']}; }}
    #statusbar {{ background: {t['chrome']}; border-top: 1px solid {t['border']}; }}
    #statusText {{ color: {t['secondary']}; font-size: 12px; }}
    #saveLabel {{ color: {t['secondary']}; }}
    QToolButton {{ background: transparent; border: 2px solid transparent; border-radius: 6px; }}
    QToolButton:hover {{ background: {t['chrome_hover']}; }}
    QToolButton:pressed {{ background: {t['chrome_pressed']}; }}
    QToolButton:focus {{ border-color: {t['focus']}; }}
    QPushButton {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 6px;
                   padding: 0 14px; min-height: 26px; max-height: 26px; }}
    QPushButton:hover {{ background: {t['hover']}; }}
    QPushButton:pressed {{ background: {t['select_inactive']}; }}
    QPushButton:focus {{ border: 2px solid {t['focus']}; padding: 0 13px; min-height: 24px; max-height: 24px; }}
    QPushButton:disabled {{ color: {t['disabled']}; }}
    QPushButton#primary {{ background: {t['accent']}; color: {t['on_accent']}; border: 1px solid {t['accent']};
                           font-weight: 600; }}
    QPushButton#primary:hover {{ background: {t['accent_hover']}; }}
    QPushButton#primary:pressed {{ background: {t['accent_pressed']}; }}
    QPushButton#primary:focus {{ border: 2px solid {t['focus']}; }}
    QPushButton#primary:disabled {{ background: {t['select_inactive']}; border-color: {t['select_inactive']};
                                    color: {t['disabled']}; }}
    QComboBox {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 6px;
                 padding: 0 26px 0 10px; min-height: 26px; max-height: 26px; }}
    QComboBox:hover {{ background: {t['hover']}; }}
    QComboBox:focus {{ border: 2px solid {t['focus']}; padding: 0 25px 0 9px; min-height: 24px; max-height: 24px; }}
    QComboBox::drop-down {{ border: none; width: 22px; subcontrol-position: center right; }}
    QComboBox::down-arrow {{ image: url({chevrons}); width: 12px; height: 12px; }}
    QComboBox QAbstractItemView {{ background: {t['surface']}; border: 1px solid {t['border']}; padding: 4px;
                                   outline: 0; selection-background-color: {t['accent']};
                                   selection-color: {t['on_accent']}; }}
    #well {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px; }}
    #well[drop="true"] {{ background: {t['accent_tint']}; border: 2px solid {t['accent']}; }}
    QListView {{ background: transparent; border: none; outline: 0; }}
    #emptyTitle {{ font-size: 17px; font-weight: 600; }}
    #emptyBody {{ color: {t['secondary']}; }}
    #emptyState, #emptyIcon, #emptyTitle, #emptyBody {{ background: transparent; }}
    QProgressBar {{ background: {t['separator']}; border: none; border-radius: 3px;
                    min-height: 6px; max-height: 6px; }}
    QProgressBar::chunk {{ background: {t['accent']}; border-radius: 3px; }}
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 4px 2px; }}
    QScrollBar::handle:vertical {{ background: {t['scroll']}; border-radius: 4px; min-height: 32px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """


class _Rows(RowDelegate):
    height = 48

    def __init__(self, view: FileListView, t: dict):
        super().__init__(view)
        self.t = t
        self.name_font = font(13, QFont.Medium)
        self.small_font = font(12)
        self.status_font = font(12, QFont.Medium)

    def paint_row(self, p: QPainter, rect: QRect, job: FileJob, row: int, st: dict) -> None:
        t = self.t
        r = rect.adjusted(6, 1, -6, -1)
        on_accent = st["selected"] and st["focused"]
        if st["selected"]:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(t["accent"] if on_accent else t["select_inactive"]))
            p.drawRoundedRect(r, 6, 6)
        elif st["hover"]:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(t["hover"]))
            p.drawRoundedRect(r, 6, 6)
        elif not st["last"]:
            p.setPen(QPen(QColor(t["separator"]), 1))
            p.drawLine(r.left() + 40, rect.bottom(), r.right() - 6, rect.bottom())

        def ink(role: str) -> QColor:
            return QColor(t["on_accent"] if on_accent else t[role])

        p.drawPixmap(r.left() + 10, r.center().y() - 10,
                     pixmap("file-text", t["on_accent"] if on_accent else t["secondary"], 20, 1.75))

        status, extra = job.status_text()
        icon_name, role = status_icon(job)
        p.setFont(self.status_font)
        status_w = max(QFontMetrics(self.status_font).horizontalAdvance(status),
                       QFontMetrics(self.small_font).horizontalAdvance(extra)) + (20 if icon_name else 0)
        right = r.right() - 12
        top = r.center().y() - 17
        text_right = right - status_w - 16

        p.setFont(self.name_font)
        p.setPen(ink("label"))
        name = QFontMetrics(self.name_font).elidedText(job.name, Qt.ElideRight, text_right - (r.left() + 40))
        p.drawText(QRect(r.left() + 40, top, text_right - r.left() - 40, 17), Qt.AlignLeft | Qt.AlignVCenter, name)
        line, is_error = second_line(job)
        p.setFont(self.small_font)
        p.setPen(ink("danger" if is_error else "secondary"))
        mode = Qt.ElideRight if is_error or job.status is Status.UNCHANGED else Qt.ElideMiddle
        line = QFontMetrics(self.small_font).elidedText(line, mode, text_right - (r.left() + 40))
        p.drawText(QRect(r.left() + 40, top + 18, text_right - r.left() - 40, 16), Qt.AlignLeft | Qt.AlignVCenter, line)

        status_rect = QRect(right - status_w, top, status_w, 17)
        p.setFont(self.status_font)
        p.setPen(ink(role))
        p.drawText(status_rect, Qt.AlignRight | Qt.AlignVCenter, status)
        if icon_name:
            text_w = QFontMetrics(self.status_font).horizontalAdvance(status)
            p.drawPixmap(right - text_w - 20, top + 1, pixmap(icon_name, ink(role).name(), 15, 2))
        if extra:
            p.setFont(self.small_font)
            p.setPen(ink("secondary"))
            p.drawText(QRect(right - status_w, top + 18, status_w, 16), Qt.AlignRight | Qt.AlignVCenter, extra)


class AppleClassicWindow(BaseWindow):
    ID = "apple-classic"
    NAME = "Apple Classic"
    DESCRIPTION = "Toolbar, inset list and status bar"
    TITLE_CASE = True

    def build(self) -> None:
        t = self.t = tokens(self.prefs)
        L = self.labels
        set_palette(self, t)
        self.setStyleSheet(stylesheet(t))
        self.fill_menu_bar()

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        column = QVBoxLayout(root)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        # Toolbar: add · manage · output and the one prominent action.
        bar = QFrame(objectName="toolbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 9, 12, 9)
        row.setSpacing(2)
        for name, act in (("file-plus", self.act_add_files), ("folder-plus", self.act_add_folder)):
            button = icon_button(icon(name, t["label"], 18, 1.75, t["disabled"]), act.toolTip())
            bind(button, act)
            row.addWidget(button)
        row.addSpacing(14)
        for name, act in (("trash-2", self.act_remove), ("folder-open", self.act_show)):
            button = icon_button(icon(name, t["label"], 18, 1.75, t["disabled"]), act.toolTip())
            bind(button, act)
            row.addWidget(button)
        row.addWidget(self.settings_button(t["label"]))
        row.addStretch(1)
        row.addWidget(QLabel(L.save_to, objectName="saveLabel"))
        row.addSpacing(6)
        row.addWidget(OutputPicker(self.controller, L))
        row.addSpacing(14)
        self.primary = QPushButton(L.run, objectName="primary")
        self.primary.setCursor(Qt.PointingHandCursor)
        bind(self.primary, self.act_run)
        row.addWidget(self.primary)
        column.addWidget(bar)

        # Content: an inset well holding either the empty state or the list.
        content = QWidget()
        pad = QVBoxLayout(content)
        pad.setContentsMargins(20, 20, 20, 20)
        self.well = QFrame(objectName="well")
        well_layout = QVBoxLayout(self.well)
        well_layout.setContentsMargins(4, 4, 4, 4)
        self.stack = QStackedWidget()
        choose = QPushButton(L.choose_files)
        bind(choose, self.act_add_files)
        self.empty = EmptyState(
            pixmap("file-plus", t["secondary"], 44, 1.5), "Drop PDFs Here",
            "Or choose files to clean. Cleaned copies are saved as name_clean.pdf, "
            "and the originals stay unchanged.", choose)
        self.list_view = FileListView(self.controller.model)
        self.list_view.setItemDelegate(_Rows(self.list_view, t))
        self.list_view.setSpacing(0)
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.list_view)
        well_layout.addWidget(self.stack)
        pad.addWidget(self.well)
        column.addWidget(content, 1)

        # Status bar: information only.
        status = QFrame(objectName="statusbar")
        srow = QHBoxLayout(status)
        srow.setContentsMargins(14, 5, 14, 5)
        self.note_icon = QLabel()
        self.status_text = QLabel(objectName="statusText")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(140)
        self.progress.hide()
        srow.addWidget(self.note_icon)
        srow.addWidget(self.status_text, 1)
        srow.addWidget(self.progress)
        column.addWidget(status)
        self._note = ("", "")

    def update_view(self) -> None:
        jobs = self.controller.jobs
        self.stack.setCurrentIndex(1 if jobs else 0)
        running = self.controller.running
        self.progress.setVisible(running)
        summary = self.controller.last_summary
        if running:
            text, kind = self.status_text.text(), ""
        elif self._note[0]:
            text, kind = self._note
        elif summary is not None:
            text = summary.text()
            kind = ("danger" if not summary.cleaned else "warning") if summary.failed else "success"
        else:
            text, kind = (plural(len(jobs), "PDF") if jobs else "No PDFs added"), ""
        self.status_text.setText(text)
        names = {"success": "circle-check", "danger": "circle-x", "warning": "triangle-alert", "info": "info"}
        if kind in names:
            role = {"info": "secondary"}.get(kind, kind)
            self.note_icon.setPixmap(pixmap(names[kind], self.t[role], 14, 2))
            self.note_icon.show()
        else:
            self.note_icon.hide()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Start on the content, not on a toolbar button.
        (self.list_view if self.controller.jobs else self.empty.findChild(QPushButton)).setFocus()

    def on_progress(self, done: int, total: int) -> None:
        self._note = ("", "")
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        self.status_text.setText(f"Cleaning {min(done + 1, total)} of {total}…" if done < total else "Finishing…")
        self.note_icon.hide()

    def on_finished(self, summary: RunSummary) -> None:
        self.update_view()

    def notify(self, text: str, kind: str = "info") -> None:
        self._note = (text, "danger" if kind == "error" else kind)
        self.update_view()

    def add_paths(self, paths) -> None:
        self._note = ("", "")
        super().add_paths(paths)

    def set_drop_active(self, active: bool) -> None:
        self.well.setProperty("drop", "true" if active else "false")
        self.well.style().unpolish(self.well)
        self.well.style().polish(self.well)
