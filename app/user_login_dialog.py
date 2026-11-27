"""تسجيل دخول مستخدم التطبيق (بعد الاتصال بقاعدة البيانات)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QVBoxLayout,
)

from app import repository as repo
from app.db import Database, friendly_error
from app.rtl import apply_rtl, show_error, show_warning
from app.theme import make_button


class UserLoginDialog(QDialog):
    """يتحقق من كلمة المرور عبر PBKDF2 المخزنة في SQL Server."""

    def __init__(self, database: Database, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.db = database
        self.user: dict[str, Any] | None = None
        self._users: list[dict[str, Any]] = []

        self.setWindowTitle("تسجيل دخول المستخدم")
        form = QFormLayout()
        self.user_combo = QComboBox()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("المستخدم:", self.user_combo)
        form.addRow("كلمة المرور:", self.password_edit)

        buttons = QHBoxLayout()
        self.login_button = make_button(
            self, "دخول", "key", self.accept, size=22
        )
        self.login_button.setDefault(True)
        cancel_button = make_button(self, "إلغاء", "close", self.reject, size=22)
        buttons.addWidget(self.login_button)
        buttons.addWidget(cancel_button)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addLayout(buttons)
        apply_rtl(self)
        self._load_users()

    def _load_users(self) -> None:
        try:
            self._users = [
                row for row in repo.list_users(self.db) if row["IsActive"]
            ]
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.user_combo.clear()
        for row in self._users:
            self.user_combo.addItem(
                f"{row['FullName']} ({row['UserName']})", int(row["UserID"])
            )

    def accept(self) -> None:  # noqa: D102 - Qt slot
        if self.user_combo.count() == 0:
            show_warning(self, "لا يوجد مستخدمون مفعّلون. راجع قاعدة البيانات.")
            return
        selected = self._users[self.user_combo.currentIndex()]
        try:
            user = repo.authenticate(
                self.db, str(selected["UserName"]), self.password_edit.text()
            )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        if user is None:
            show_warning(self, "كلمة المرور غير صحيحة.")
            return
        self.user = user
        super().accept()
