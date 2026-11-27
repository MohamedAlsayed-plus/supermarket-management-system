"""تبويب العملاء: إضافة وتعديل وحذف العملاء."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
)

from app import repository as repo
from app.db import Database, friendly_error
from app.rtl import apply_rtl, ask_confirm, show_error, show_warning
from app.tabs.base import TableTab


class CustomersTab(TableTab):
    headers = ("الرقم", "اسم العميل", "الهاتف")

    def rows(self):
        return [
            [row["CustomerID"], row["CustomerName"], row["Phone"]]
            for row in repo.list_customers(self.db)
        ]

    def add_item(self) -> None:
        self._open_form(None, "", "")

    def edit_item(self) -> None:
        customer_id = self.require_selection()
        if customer_id is None:
            return
        row = repo.get_customer(self.db, customer_id)
        if row is None:
            show_warning(self, "لم يتم العثور على العميل.")
            return
        self._open_form(
            customer_id, str(row["CustomerName"]), str(row["Phone"] or "")
        )

    def delete_item(self) -> None:
        customer_id = self.require_selection()
        if customer_id is None:
            return
        if not ask_confirm(self, "هل تريد حذف هذا العميل؟"):
            return
        try:
            repo.delete_customer(self.db, customer_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()

    def _open_form(self, customer_id: int | None, name: str, phone: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة عميل" if customer_id is None else "تعديل عميل")
        form = QFormLayout(dialog)
        name_edit = QLineEdit(name)
        phone_edit = QLineEdit(phone)
        phone_edit.setPlaceholderText("اختياري")
        form.addRow("اسم العميل:", name_edit)
        form.addRow("الهاتف:", phone_edit)
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
            if customer_id is None:
                repo.add_customer(self.db, name_edit.text(), phone_edit.text())
            else:
                repo.update_customer(
                    self.db, customer_id, name_edit.text(), phone_edit.text()
                )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()
