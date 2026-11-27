"""مظهر فاتح/داكن وتوليد عناصر بواجهة أيقونية."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QPushButton, QWidget

from app.icons import icon, set_icon_color

LIGHT_STYLE = """
QMainWindow, QDialog { background: #f4f6fa; }
QWidget { color: #1f2937; }
QToolBar { background: #ffffff; border: 0; padding: 6px; spacing: 6px; }
QToolBar QToolButton { background: #ffffff; border: 1px solid #d8dee9; border-radius: 8px; padding: 6px 10px; }
QToolBar QToolButton:hover { background: #e8f0fe; border-color: #4a90d9; }
QPushButton { background: #ffffff; border: 1px solid #d8dee9; border-radius: 8px; padding: 7px 13px; }
QPushButton:hover { background: #eef4ff; border-color: #4a90d9; }
QPushButton:default { background: #2f6fdb; color: #ffffff; border-color: #2f6fdb; }
QListWidget#NavList { background: #ffffff; border: 0; border-left: 1px solid #e1e6ee; }
QListWidget#NavList::item { padding: 9px; border-radius: 8px; margin: 2px 6px; }
QListWidget#NavList::item:selected { background: #e3edff; color: #1f4f9c; font-weight: bold; }
QTableView { background: #ffffff; alternate-background-color: #f8fafc; gridline-color: #e5e9f0; border: 1px solid #e1e6ee; border-radius: 8px; }
QHeaderView::section { background: #eef2f7; border: 0; padding: 6px; font-weight: bold; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit { background: #ffffff; border: 1px solid #d8dee9; border-radius: 6px; padding: 5px 8px; }
QGroupBox { border: 1px solid #d8dee9; border-radius: 10px; margin-top: 12px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; right: 12px; }
QFrame#KpiCard { background: #ffffff; border: 1px solid #e1e6ee; border-radius: 12px; }
QLabel#KpiValue { font-size: 22px; font-weight: bold; color: #2f6fdb; }
QStatusBar { background: #ffffff; }
"""

DARK_STYLE = """
QMainWindow, QDialog { background: #171b24; }
QWidget { color: #e5e7eb; }
QToolBar { background: #202634; border: 0; padding: 6px; spacing: 6px; }
QToolBar QToolButton { background: #2a3140; border: 1px solid #3a4354; border-radius: 8px; padding: 6px 10px; }
QToolBar QToolButton:hover { background: #34425c; border-color: #7aa5ff; }
QPushButton { background: #2a3140; border: 1px solid #3a4354; border-radius: 8px; padding: 7px 13px; }
QPushButton:hover { background: #34425c; border-color: #7aa5ff; }
QPushButton:default { background: #4c86e8; color: #ffffff; border-color: #4c86e8; }
QListWidget#NavList { background: #202634; border: 0; border-left: 1px solid #30384a; }
QListWidget#NavList::item { padding: 9px; border-radius: 8px; margin: 2px 6px; }
QListWidget#NavList::item:selected { background: #34425c; color: #a9c8ff; font-weight: bold; }
QTableView { background: #202634; alternate-background-color: #252c3a; gridline-color: #30384a; border: 1px solid #30384a; border-radius: 8px; }
QHeaderView::section { background: #2a3140; border: 0; padding: 6px; font-weight: bold; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit { background: #252c3a; border: 1px solid #3a4354; border-radius: 6px; padding: 5px 8px; }
QGroupBox { border: 1px solid #3a4354; border-radius: 10px; margin-top: 12px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; right: 12px; }
QFrame#KpiCard { background: #202634; border: 1px solid #30384a; border-radius: 12px; }
QLabel#KpiValue { font-size: 22px; font-weight: bold; color: #9fc0ff; }
QStatusBar { background: #202634; }
"""


def apply_theme(application, dark: bool) -> None:  # noqa: ANN001 - QApplication
    set_icon_color("#e5e7eb" if dark else "#1f2937")
    application.setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)


def refresh_icons(root: QWidget) -> None:
    """إعادة رسم الأيقونات بلون المظهر الجديد."""
    for widget in [root, *root.findChildren(QWidget)]:
        name = widget.property("icon_name")
        if name and hasattr(widget, "setIcon"):
            widget.setIcon(icon(str(name), int(widget.property("icon_size") or 20)))
    for action in root.findChildren(QAction):
        name = action.property("icon_name")
        if name:
            action.setIcon(icon(str(name), int(action.property("icon_size") or 20)))


def make_action(
    parent, text: str, icon_name: str, callback=None, size: int = 20  # noqa: ANN001
) -> QAction:
    action = QAction(icon(icon_name, size), text, parent)
    action.setProperty("icon_name", icon_name)
    action.setProperty("icon_size", size)
    if callback is not None:
        action.triggered.connect(callback)
    return action


def make_button(
    parent, text: str, icon_name: str, callback=None, size: int = 20  # noqa: ANN001
) -> QPushButton:
    button = QPushButton(icon(icon_name, size), text, parent)
    button.setProperty("icon_name", icon_name)
    button.setProperty("icon_size", size)
    if callback is not None:
        button.clicked.connect(callback)
    return button
