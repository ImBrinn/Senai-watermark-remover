"""Theme 4, Windows 11 Fluent: built to feel native on Windows 11, where
the app runs, without Apple's rules as a constraint.

- Mica-like base colour with content on cards: 8 px corners, 1 px strokes.
- Segoe UI Variable, the Windows 11 type ramp (28 px title, 14 px body,
  12 px caption), with Inter as the fallback where Segoe isn't installed.
- A command bar of subtle icon-and-text buttons, with less-used commands
  under "See more" (⋯), as Windows 11 apps do.
- An InfoBar for results and notes, in the Windows severity colours; it
  stays until closed or the next action.
- The accent button, "Remove watermarks", sits bottom-right where Windows
  dialogs put their commit button. Light accent #005FB8 with white text;
  dark accent #60CDFF with black text, as Windows 11 does.
- Fluent list selection: a subtle fill plus a short accent pill on the
  selected row's leading edge.
- Sentence-case labels, as Windows uses.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
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

from ..model import FileJob, RunSummary, Status
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

TEXT_FONTS = ["Segoe UI Variable Text", "Segoe UI", "Inter"]
DISPLAY_FONTS = ["Segoe UI Variable Display", "Segoe UI", "Inter Display", "Inter"]

LIGHT = {
    "bg": "#F3F3F3", "surface": "#FFFFFF", "border": "#E5E5E5", "control_border": "#D6D6D6",
    "control_bottom": "#B5B5B5", "separator": "#E5E5E5",
    "label": "#1A1A1A", "secondary": "#5C5C5C", "disabled": "#A0A0A0",
    "accent": "#005FB8", "accent_hover": "#196EBF", "accent_pressed": "#0A5AA8", "on_accent": "#FFFFFF",
    "accent_disabled": "#C8C8C8", "on_accent_disabled": "#FFFFFF",
    "accent_text": "#005FB8", "accent_tint": "#E8F1FA",
    "success": "#0F7B0F", "warning": "#9D5D00", "danger": "#C42B1C",
    "success_bg": "#DFF6DD", "warning_bg": "#FFF4CE", "danger_bg": "#FDE7E9", "info_bg": "#F6F6F6",
    "hover": "#F5F5F5", "selected": "#F0F0F0", "control": "#FBFBFB", "control_hover": "#F6F6F6",
    "control_pressed": "#F0F0F0", "cmd_hover": "#EAEAEA", "cmd_pressed": "#E5E5E5",
    "focus": "#1A1A1A", "scroll": "rgba(0,0,0,0.35)",
}
DARK = {
    "bg": "#202020", "surface": "#2B2B2B", "border": "#383838", "control_border": "#3D3D3D",
    "control_bottom": "#4A4A4A", "separator": "#3A3A3A",
    "label": "#FFFFFF", "secondary": "#C8C8C8", "disabled": "#7A7A7A",
    "accent": "#60CDFF", "accent_hover": "#5AB9E6", "accent_pressed": "#52A6CE", "on_accent": "#000000",
    "accent_disabled": "#474747", "on_accent_disabled": "#A7A7A7",
    "accent_text": "#60CDFF", "accent_tint": "#1F3A4A",
    "success": "#6CCB5F", "warning": "#FCE100", "danger": "#FF99A4",
    "success_bg": "#393D1B", "warning_bg": "#433519", "danger_bg": "#442726", "info_bg": "#2D2D2D",
    "hover": "#323232", "selected": "#383838", "control": "#2D2D2D", "control_hover": "#323232",
    "control_pressed": "#272727", "cmd_hover": "#2D2D2D", "cmd_pressed": "#292929",
    "focus": "#FFFFFF", "scroll": "rgba(255,255,255,0.40)",
}
# (text, background, minimum ratio). Status icons on InfoBars are graphics,
# so they need 3:1; everything that's text needs 4.5:1.
CONTRAST = [
    ("label", "bg", 4.5), ("label", "surface", 4.5), ("secondary", "bg", 4.5), ("secondary", "surface", 4.5),
    ("secondary", "hover", 4.5), ("secondary", "selected", 4.5), ("secondary", "cmd_hover", 4.5),
    ("label", "control", 4.5), ("label", "control_hover", 4.5), ("label", "selected", 4.5),
    ("on_accent", "accent", 4.5), ("on_accent", "accent_hover", 4.5), ("on_accent", "accent_pressed", 4.5),
    ("accent_text", "surface", 4.5), ("accent_text", "accent_tint", 4.5), ("accent_text", "bg", 4.5),
    ("success", "surface", 4.5), ("warning", "surface", 4.5), ("danger", "surface", 4.5),
    ("danger", "hover", 4.5), ("danger", "selected", 4.5),
    ("label", "success_bg", 4.5), ("label", "warning_bg", 4.5), ("label", "danger_bg", 4.5),
    ("label", "info_bg", 4.5),
    ("success", "success_bg", 3.0), ("warning", "warning_bg", 3.0), ("danger", "danger_bg", 3.0),
    ("accent_text", "info_bg", 3.0),
]
SEVERITY = {
    "success": ("circle-check", "success", "success_bg"),
    "warning": ("triangle-alert", "warning", "warning_bg"),
    "error": ("circle-x", "danger", "danger_bg"),
    "info": ("info", "accent_text", "info_bg"),
}


def tokens(prefs: Prefs) -> dict:
    t = dict(DARK if prefs.dark else LIGHT)
    if prefs.high_contrast:
        t.update(secondary=t["label"], border=t["label"], control_border=t["label"],
                 control_bottom=t["label"], separator=t["label"])
    return t


def stylesheet(t: dict) -> str:
    chevron = icon_file("chevron-down", t["secondary"], 12)
    return f"""
    QMainWindow, #root {{ background: {t['bg']}; }}
    QWidget {{ color: {t['label']}; }}
    #subtitle, #caption, #orLabel {{ color: {t['secondary']}; background: transparent; }}
    #title {{ background: transparent; }}
    QMenu {{ background: {t['surface']}; border: 1px solid {t['border']}; padding: 4px; }}
    QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {t['cmd_hover']}; color: {t['label']}; }}
    QMenu::item:disabled {{ color: {t['disabled']}; }}
    QMenu::separator {{ height: 1px; background: {t['separator']}; margin: 4px 0; }}
    QMenu::indicator {{ width: 12px; height: 12px; left: 6px; }}

    QToolButton#command {{ background: transparent; border: 2px solid transparent; border-radius: 4px;
                           padding: 0 9px; min-height: 28px; max-height: 28px; }}
    QToolButton#command:hover {{ background: {t['cmd_hover']}; }}
    QToolButton#command:pressed {{ background: {t['cmd_pressed']}; color: {t['secondary']}; }}
    QToolButton#command:disabled {{ color: {t['disabled']}; }}
    QToolButton#command:focus {{ border-color: {t['focus']}; }}
    QToolButton#command::menu-indicator {{ image: none; width: 0; }}
    QToolButton {{ background: transparent; border: 2px solid transparent; border-radius: 4px; }}
    QToolButton:hover {{ background: {t['cmd_hover']}; }}
    QToolButton:focus {{ border-color: {t['focus']}; }}
    #commandSeparator {{ background: {t['separator']}; }}

    QPushButton {{ background: {t['control']}; border: 1px solid {t['control_border']};
                   border-bottom-color: {t['control_bottom']}; border-radius: 4px;
                   padding: 0 12px; min-height: 30px; max-height: 30px; }}
    QPushButton:hover {{ background: {t['control_hover']}; }}
    QPushButton:pressed {{ background: {t['control_pressed']}; color: {t['secondary']};
                           border-bottom-color: {t['control_border']}; }}
    QPushButton:disabled {{ color: {t['disabled']}; }}
    QPushButton:focus {{ border: 2px solid {t['focus']}; padding: 0 11px; min-height: 28px; max-height: 28px; }}
    QPushButton#primary {{ background: {t['accent']}; color: {t['on_accent']}; border: 1px solid {t['accent']};
                           padding: 0 20px; min-width: 128px; }}
    QPushButton#primary:hover {{ background: {t['accent_hover']}; border-color: {t['accent_hover']}; }}
    QPushButton#primary:pressed {{ background: {t['accent_pressed']}; border-color: {t['accent_pressed']};
                                   color: {t['on_accent']}; }}
    QPushButton#primary:focus {{ border: 2px solid {t['focus']}; padding: 0 19px; }}
    QPushButton#primary:disabled {{ background: {t['accent_disabled']}; border-color: {t['accent_disabled']};
                                    color: {t['on_accent_disabled']}; }}
    QPushButton#link {{ background: transparent; border: 2px solid transparent; color: {t['accent_text']};
                        padding: 0 4px; min-height: 26px; max-height: 26px; }}
    QPushButton#link:hover {{ text-decoration: underline; }}
    QPushButton#link:pressed {{ color: {t['secondary']}; }}
    QPushButton#link:focus {{ border-color: {t['focus']}; padding: 0 4px; }}

    QComboBox {{ background: {t['control']}; border: 1px solid {t['control_border']};
                 border-bottom-color: {t['control_bottom']}; border-radius: 4px;
                 padding: 0 32px 0 11px; min-height: 30px; max-height: 30px; min-width: 150px; }}
    QComboBox:hover {{ background: {t['control_hover']}; }}
    QComboBox:focus {{ border: 2px solid {t['focus']}; padding: 0 31px 0 10px; min-height: 28px; max-height: 28px; }}
    QComboBox::drop-down {{ border: none; width: 30px; subcontrol-position: center right; }}
    QComboBox::down-arrow {{ image: url({chevron}); width: 12px; height: 12px; }}
    QComboBox QAbstractItemView {{ background: {t['surface']}; border: 1px solid {t['border']}; padding: 4px;
                                   outline: 0; selection-background-color: {t['cmd_hover']};
                                   selection-color: {t['label']}; }}

    #card {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px; }}
    #card[drop="true"] {{ border: 2px solid {t['accent']}; }}
    #infoBar {{ border: 1px solid {t['border']}; border-radius: 6px; }}
    #infoBar[severity="success"] {{ background: {t['success_bg']}; }}
    #infoBar[severity="warning"] {{ background: {t['warning_bg']}; }}
    #infoBar[severity="error"] {{ background: {t['danger_bg']}; }}
    #infoBar[severity="info"] {{ background: {t['info_bg']}; }}
    #infoBar QLabel {{ background: transparent; }}
    QListView {{ background: transparent; border: none; outline: 0; }}
    #emptyState, #emptyIcon, #emptyTitle, #emptyBody {{ background: transparent; }}
    #emptyBody {{ color: {t['secondary']}; }}
    QProgressBar {{ background: {t['separator']}; border: none; border-radius: 1px;
                    min-height: 3px; max-height: 3px; }}
    QProgressBar::chunk {{ background: {t['accent']}; border-radius: 1px; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 6px 2px; }}
    QScrollBar::handle:vertical {{ background: {t['scroll']}; border-radius: 3px; min-height: 32px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """


class _Rows(RowDelegate):
    height = 58

    def __init__(self, view: FileListView, t: dict):
        super().__init__(view)
        self.t = t
        self.name_font = font(14, QFont.DemiBold, families=TEXT_FONTS)
        self.small_font = font(12, families=TEXT_FONTS)
        self.status_font = font(12, QFont.DemiBold, families=TEXT_FONTS)

    def paint_row(self, p: QPainter, rect: QRect, job: FileJob, row: int, st: dict) -> None:
        t = self.t
        r = QRectF(rect).adjusted(4, 2, -4, -2)
        if st["selected"] or st["hover"]:
            path = QPainterPath()
            path.addRoundedRect(r, 4, 4)
            p.fillPath(path, QColor(t["selected"] if st["selected"] else t["hover"]))
        if st["selected"]:
            pill = QRectF(r.left(), r.center().y() - 8, 3, 16)
            path = QPainterPath()
            path.addRoundedRect(pill, 1.5, 1.5)
            p.fillPath(path, QColor(t["accent"] if st["focused"] else t["secondary"]))

        tile = QRectF(r.left() + 14, r.center().y() - 18, 36, 36)
        tile_path = QPainterPath()
        tile_path.addRoundedRect(tile, 6, 6)
        p.fillPath(tile_path, QColor(t["accent_tint"]))
        p.drawPixmap(int(tile.left()) + 8, int(tile.top()) + 8, pixmap("file-text", t["accent_text"], 20, 1.75))

        status, extra = job.status_text()
        icon_name, role = status_icon(job)
        fm_status, fm_small, fm_name = (QFontMetrics(self.status_font), QFontMetrics(self.small_font),
                                        QFontMetrics(self.name_font))
        status_w = max(fm_status.horizontalAdvance(status) + (22 if icon_name else 0),
                       fm_small.horizontalAdvance(extra))
        right = int(r.right()) - 16
        left = int(tile.right()) + 14
        text_right = right - status_w - 20
        line_h = fm_name.height()
        small_h = fm_small.height()
        top = int(r.center().y() - (line_h + 2 + small_h) / 2)

        p.setFont(self.name_font)
        p.setPen(QColor(t["label"]))
        p.drawText(QRect(left, top, text_right - left, line_h), Qt.AlignLeft | Qt.AlignVCenter,
                   fm_name.elidedText(job.name, Qt.ElideRight, text_right - left))
        line, is_error = second_line(job)
        mode = Qt.ElideRight if is_error or job.status is Status.UNCHANGED else Qt.ElideMiddle
        p.setFont(self.small_font)
        p.setPen(QColor(t["danger" if is_error else "secondary"]))
        p.drawText(QRect(left, top + line_h + 2, text_right - left, small_h), Qt.AlignLeft | Qt.AlignVCenter,
                   fm_small.elidedText(line, mode, text_right - left))

        status_h = fm_status.height()
        status_top = top if extra else int(r.center().y() - status_h / 2)
        p.setFont(self.status_font)
        p.setPen(QColor(t[role]))
        p.drawText(QRect(right - status_w, status_top, status_w, status_h), Qt.AlignRight | Qt.AlignVCenter, status)
        if icon_name:
            p.drawPixmap(right - fm_status.horizontalAdvance(status) - 22,
                         status_top + (status_h - 16) // 2, pixmap(icon_name, t[role], 16, 2))
        if extra:
            p.setFont(self.small_font)
            p.setPen(QColor(t["secondary"]))
            p.drawText(QRect(right - status_w, top + line_h + 2, status_w, small_h),
                       Qt.AlignRight | Qt.AlignVCenter, extra)


class DropZone(QWidget):
    """The empty card: a dashed drop target that turns accent while PDFs
    are dragged over the window. It takes focus first, without drawing a
    ring until it's reached with the keyboard (as Windows does); Enter or
    Space then opens the file picker."""

    def __init__(self, t: dict, inner: QWidget, on_activate):
        super().__init__()
        self.t = t
        self.active = False
        self.keyboard_focus = False
        self.on_activate = on_activate
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName("Drop PDFs here")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
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
        r = QRectF(self.rect()).adjusted(12, 12, -12, -12)
        if self.active:
            p.setBrush(QColor(self.t["accent_tint"]))
            p.setPen(QPen(QColor(self.t["accent"]), 2))
        else:
            p.setBrush(Qt.NoBrush)
            pen = QPen(QColor(self.t["control_bottom"]), 1.5)
            pen.setDashPattern([4, 3])
            p.setPen(pen)
        p.drawRoundedRect(r, 6, 6)
        if self.keyboard_focus:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(self.t["focus"]), 2))
            p.drawRoundedRect(r.adjusted(-4, -4, 4, 4), 8, 8)


class InfoBar(QFrame):
    """A Windows 11 InfoBar: severity icon, message, optional action and a
    close button. Stays until closed or the next action."""

    def __init__(self, t: dict, labels):
        super().__init__(objectName="infoBar")
        self.t = t
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 8, 8, 8)
        row.setSpacing(12)
        self.icon = QLabel()
        self.icon.setFixedSize(18, 18)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setFont(font(14, families=TEXT_FONTS))
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.action = QPushButton(labels.show)
        self.action.setCursor(Qt.PointingHandCursor)
        self.action.setFont(font(14, families=TEXT_FONTS))
        self.close_button = icon_button(icon("x", t["label"], 16), "Close", 30)
        self.close_button.clicked.connect(self.hide)
        row.addWidget(self.icon, 0, Qt.AlignVCenter)
        row.addWidget(self.text, 1)
        row.addWidget(self.action, 0, Qt.AlignVCenter)
        row.addWidget(self.close_button, 0, Qt.AlignVCenter)
        self._slot = None
        self.hide()

    def show_message(self, text: str, severity: str, action=None) -> None:
        icon_name, role, _ = SEVERITY[severity]
        self.setProperty("severity", severity)
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon.setPixmap(pixmap(icon_name, self.t[role], 18, 2))
        self.text.setText(text)
        self.setAccessibleName(text)
        if self._slot is not None:
            self.action.clicked.disconnect(self._slot)
        self._slot = action
        self.action.setVisible(action is not None)
        if action is not None:
            self.action.clicked.connect(action)
        self.show()


def _command(icon_name: str, text: str, t: dict) -> QToolButton:
    button = QToolButton(objectName="command")
    button.setIcon(icon(icon_name, t["label"], 16, 1.75, t["disabled"]))
    # A leading space puts Fluent's gap between the icon and the label.
    button.setText(f" {text}" if text else "")
    button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setFont(font(14, families=TEXT_FONTS))
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.StrongFocus)
    button.setAccessibleName(text.rstrip("…"))
    return button


class FluentWindow(BaseWindow):
    ID = "fluent"
    NAME = "Windows 11 Fluent"
    DESCRIPTION = "Native Windows 11 look"
    TITLE_CASE = False
    DEFAULT_SIZE = (820, 620)
    MIN_SIZE = (600, 480)

    def build(self) -> None:
        t = self.t = tokens(self.prefs)
        L = self.labels
        set_palette(self, t)
        self.setFont(font(14, families=TEXT_FONTS))
        self.setStyleSheet(stylesheet(t))

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(32, 26, 32, 24)
        page.setSpacing(0)

        title = QLabel(L.run, objectName="title")
        title.setFont(font(28, QFont.DemiBold, families=DISPLAY_FONTS))
        title.setAccessibleName(L.run)
        page.addWidget(title)
        page.addSpacing(4)
        subtitle = QLabel("Removes the SenAI title and senai.uk footer from your PDFs. "
                          "Your originals aren't changed.", objectName="subtitle")
        subtitle.setWordWrap(True)
        subtitle.setFont(font(14, families=TEXT_FONTS))
        page.addWidget(subtitle)
        page.addSpacing(16)

        # Command bar.
        commands = QHBoxLayout()
        commands.setSpacing(2)
        for name, text, act in (("file-plus", L.add_files, self.act_add_files),
                                ("folder-plus", L.add_folder, self.act_add_folder)):
            button = _command(name, text, t)
            bind(button, act)
            commands.addWidget(button)
        separator = QFrame(objectName="commandSeparator")
        separator.setFixedSize(1, 20)
        commands.addSpacing(6)
        commands.addWidget(separator, 0, Qt.AlignVCenter)
        commands.addSpacing(6)
        for name, text, act in (("trash-2", L.remove, self.act_remove), ("x", L.clear, self.act_clear)):
            button = _command(name, text, t)
            bind(button, act)
            commands.addWidget(button)
        commands.addStretch(1)
        more = _command("ellipsis", "", t)
        more.setToolTip("See more")
        more.setAccessibleName("See more")
        more.setToolButtonStyle(Qt.ToolButtonIconOnly)
        more_menu = QMenu(self)
        more_menu.setFont(font(14, families=TEXT_FONTS))
        more_menu.addActions([self.act_open_pdf, self.act_show])
        more_menu.addSeparator()
        self.more_menu_items(more_menu)
        more_menu.addAction(self.act_about)
        more_menu.addSeparator()
        more_menu.addAction(self.act_exit)
        more.setMenu(more_menu)
        more.setPopupMode(QToolButton.InstantPopup)
        gear = _command("settings", "", t)
        gear.setToolTip(self.act_settings.toolTip())
        gear.setAccessibleName("Settings")
        gear.setToolButtonStyle(Qt.ToolButtonIconOnly)
        bind(gear, self.act_settings)
        commands.addWidget(gear)
        commands.addWidget(more)
        page.addLayout(commands)
        page.addSpacing(12)

        self.info = InfoBar(t, L)
        self.info.close_button.clicked.connect(self._info_closed)
        page.addWidget(self.info)
        self.info_gap = QWidget()
        self.info_gap.setFixedHeight(12)
        self.info_gap.hide()
        page.addWidget(self.info_gap)

        # The card: drop zone when empty, otherwise the list.
        self.card = QFrame(objectName="card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(4, 4, 4, 4)
        self.stack = QStackedWidget()
        browse = QPushButton(L.choose_files, objectName="link")
        browse.setCursor(Qt.PointingHandCursor)
        browse.setFont(font(14, families=TEXT_FONTS))
        bind(browse, self.act_add_files)
        inner = EmptyState(pixmap("upload", t["accent_text"], 36, 1.75), "Drag and drop PDFs here", "or",
                           browse, width=300)
        inner.title.setFont(font(16, QFont.DemiBold, families=TEXT_FONTS))
        inner.body.setFont(font(14, families=TEXT_FONTS))
        caption = QLabel("Folders work too. Cleaned copies are saved as name_clean.pdf.", objectName="caption")
        caption.setFont(font(12, families=TEXT_FONTS))
        caption.setAlignment(Qt.AlignCenter)
        inner.layout().addSpacing(14)
        inner.layout().addWidget(caption, 0, Qt.AlignHCenter)
        self.drop_zone = DropZone(t, inner, self.act_add_files.trigger)
        self.list_view = FileListView(self.controller.model)
        self.list_view.setItemDelegate(_Rows(self.list_view, t))
        self.list_view.setFont(font(14, families=TEXT_FONTS))
        self.stack.addWidget(self.drop_zone)
        self.stack.addWidget(self.list_view)
        card_layout.addWidget(self.stack)
        page.addWidget(self.card, 1)

        page.addSpacing(10)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        keep = self.progress.sizePolicy()
        keep.setRetainSizeWhenHidden(True)
        self.progress.setSizePolicy(keep)
        self.progress.hide()
        page.addWidget(self.progress)
        page.addSpacing(12)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        save_label = QLabel(L.save_to)
        save_label.setFont(font(14, families=TEXT_FONTS))
        footer.addWidget(save_label)
        picker = OutputPicker(self.controller, L)
        picker.setFont(font(14, families=TEXT_FONTS))
        picker.view().setFont(font(14, families=TEXT_FONTS))
        footer.addWidget(picker)
        footer.addStretch(1)
        self.primary = QPushButton(L.run, objectName="primary")
        self.primary.setCursor(Qt.PointingHandCursor)
        self.primary.setFont(font(14, families=TEXT_FONTS))
        bind(self.primary, self.act_run)
        footer.addWidget(self.primary)
        page.addLayout(footer)

    def _info_closed(self) -> None:
        self.info.hide()
        self.info_gap.hide()

    def _show_info(self, text: str, severity: str, action=None) -> None:
        self.info.show_message(text, severity, action)
        self.info_gap.show()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Start on the content rather than the first command.
        if self.controller.jobs:
            self.list_view.setFocus()
        else:
            self.drop_zone.setFocus()

    def update_view(self) -> None:
        self.stack.setCurrentIndex(1 if self.controller.jobs else 0)
        self.progress.setVisible(self.controller.running)

    def on_progress(self, done: int, total: int) -> None:
        self._info_closed()
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        self.progress.show()

    def on_finished(self, summary: RunSummary) -> None:
        self.progress.hide()
        if summary.failed:
            severity = "warning" if summary.cleaned else "error"
        elif summary.cleaned:
            severity = "success"
        else:
            severity = "info"
        action = (lambda: self.controller.show_outputs(self.list_view.selected_rows())) if summary.outputs else None
        self._show_info(summary.text() + ".", severity, action)

    def notify(self, text: str, kind: str = "info") -> None:
        self._show_info(text[:1].upper() + text[1:] + ".", kind if kind in SEVERITY else "info")

    def add_paths(self, paths) -> None:
        self._info_closed()
        super().add_paths(paths)

    def set_drop_active(self, active: bool) -> None:
        self.drop_zone.active = active
        self.drop_zone.update()
        self.card.setProperty("drop", "true" if active and self.controller.jobs else "false")
        self.card.style().unpolish(self.card)
        self.card.style().polish(self.card)
