"""تبويب المستخدمين: حسابات التطبيق والصلاحيات (للمدير فقط)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
)

from app import repository as repo
from app.db import friendly_error
from app.rtl import apply_rtl, ask_confirm, show_error, show_warning
from app.tabs.base import TableTab


ROLE_LABELS = {"admin": "مدير", "cashier": "كاشير"}


class UsersTab(TableTab):
    headers = ("الرقم", "اسم المستخدم", "الاسم الكامل", "الصلاحية", "مفعّل")

    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(database, user, parent)
        if self.user.get("Role") != "admin":
            self.add_button.setEnabled(False)
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def rows(self):
        return [
            [
                row["UserID"],
                row["UserName"],
                row["FullName"],
                ROLE_LABELS.get(str(row["Role"]), str(row["Role"])),
                "نعم" if row["IsActive"] else "لا",
            ]
            for row in repo.list_users(self.db)
        ]

    def add_item(self) -> None:
        self._open_form(None)

    def edit_item(self) -> None:
        user_id = self.require_selection()
        if user_id is None:
            return
        row = repo.get_user(self.db, user_id)
        if row is None:
            show_warning(self, "لم يتم العثور على المستخدم.")
            return
        self._open_form(user_id, row)

    def delete_item(self) -> None:
        user_id = self.require_selection()
        if user_id is None:
            return
        if user_id == self.user.get("UserID"):
            show_warning(self, "لا يمكنك حذف حسابك الحالي.")
            return
        if not ask_confirm(self, "هل تريد حذف هذا المستخدم؟"):
            return
        try:
            repo.delete_user(self.db, user_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()

    def _open_form(self, user_id: int | None, row: dict | None = None) -> None:
        row = row or {}
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة مستخدم" if user_id is None else "تعديل مستخدم")
        form = QFormLayout(dialog)

        username_edit = QLineEdit(str(row.get("UserName") or ""))
        username_edit.setReadOnly(user_id is not None)
        full_name_edit = QLineEdit(str(row.get("FullName") or ""))
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        password_edit.setPlaceholderText(
            "كلمة المرور" if user_id is None else "اتركه فارغًا للاحتفاظ بكلمة المرور"
        )
        role_combo = QComboBox()
        role_combo.addItem("مدير", "admin")
        role_combo.addItem("كاشير", "cashier")
        index = role_combo.findData(row.get("Role") or "cashier")
        if index >= 0:
            role_combo.setCurrentIndex(index)
        active_check = QCheckBox("مفعّل")
        active_check.setChecked(bool(row.get("IsActive", True)))

        form.addRow("اسم المستخدم:", username_edit)
        form.addRow("الاسم الكامل:", full_name_edit)
        form.addRow("كلمة المرور:", password_edit)
        form.addRow("الصلاحية:", role_combo)
        form.addRow(active_check)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        apply_rtl(dialog)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            if user_id is None:
                repo.add_user(
                    self.db,
                    username_edit.text(),
                    full_name_edit.text(),
                    password_edit.text(),
                    role_combo.currentData(),
                    active_check.isChecked(),
                )
            else:
                repo.update_user(
                    self.db,
                    user_id,
                    full_name_edit.text(),
                    role_combo.currentData(),
                    active_check.isChecked(),
                    password_edit.text(),
                )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()
