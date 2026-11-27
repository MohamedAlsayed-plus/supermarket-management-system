"""مساعدات الاتجاه من اليمين إلى اليسار والخط العربي."

كل نوافذ البرنامج تمر على apply_rtl قبل عرضها.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QMessageBox, QWidget

FONT_FAMILIES = ("Tahoma", "Segoe UI", "Noto Sans Arabic", "Arial")


def arabic_font(point_size: int = 10, bold: bool = False) -> QFont:
    font = QFont()
    font.setFamilies(list(FONT_FAMILIES))
    font.setPointSize(point_size)
    font.setBold(bold)
    return font


def set_rtl(widget: QWidget) -> QWidget:
    widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    widget.setFont(arabic_font())
    return widget


def apply_rtl(widget: QWidget) -> QWidget:
    """تطبيق الاتجاه والخط على الواجهة وكل عناصرها التابعة."""
    for item in [widget, *widget.findChildren(QWidget)]:
        item.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        item.setFont(arabic_font())
    widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    return widget


def keep_numbers_ltr(widget: QWidget) -> QWidget:
    """حقول الأرقام تبقى من اليسار إلى اليمين مع محاذاة نصية لليمين."""
    widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    widget.setFont(arabic_font())
    return widget


def _message(
    parent: QWidget | None,
    title: str,
    text: str,
    icon: QMessageBox.Icon,
    buttons: QMessageBox.StandardButton,
) -> int:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setStandardButtons(buttons)
    apply_rtl(box)
    return box.exec()


def show_info(parent: QWidget | None, text: str, title: str = "معلومة") -> None:
    _message(parent, title, text, QMessageBox.Icon.Information, QMessageBox.StandardButton.Ok)


def show_warning(parent: QWidget | None, text: str, title: str = "تنبيه") -> None:
    _message(parent, title, text, QMessageBox.Icon.Warning, QMessageBox.StandardButton.Ok)


def show_error(parent: QWidget | None, text: str, title: str = "خطأ") -> None:
    _message(parent, title, text, QMessageBox.Icon.Critical, QMessageBox.StandardButton.Ok)


def ask_confirm(parent: QWidget | None, text: str, title: str = "تأكيد") -> bool:
    result = _message(
        parent,
        title,
        text,
        QMessageBox.Icon.Question,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes
