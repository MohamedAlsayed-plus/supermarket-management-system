"""تبويب الموردين: إضافة وتعديل وحذف الموردين."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from app import repository as repo
from app.db import friendly_error
from app.rtl import apply_rtl, ask_confirm, show_error, show_warning
from app.tabs.base import TableTab


class SuppliersTab(TableTab):
    headers = ("الرقم", "اسم المورد", "الهاتف", "العنوان")

    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(database, user, parent)

    def rows(self):
        return [
            [row["SupplierID"], row["SupplierName"], row["Phone"], row["Address"]]
            for row in repo.list_suppliers(self.db)
        ]

    def add_item(self) -> None:
        self._open_form(None)

    def edit_item(self) -> None:
        supplier_id = self.require_selection()
        if supplier_id is None:
            return
        row = repo.get_supplier(self.db, supplier_id)
        if row is None:
            show_warning(self, "لم يتم العثور على المورد.")
            return
        self._open_form(supplier_id, row)

    def delete_item(self) -> None:
        supplier_id = self.require_selection()
        if supplier_id is None:
            return
        if not ask_confirm(self, "هل تريد حذف هذا المورد؟"):
            return
        try:
            repo.delete_supplier(self.db, supplier_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()

    def _open_form(self, supplier_id: int | None, row: dict | None = None) -> None:
        row = row or {}
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة مورد" if supplier_id is None else "تعديل مورد")
        form = QFormLayout(dialog)
        name_edit = QLineEdit(str(row.get("SupplierName") or ""))
        phone_edit = QLineEdit(str(row.get("Phone") or ""))
        address_edit = QLineEdit(str(row.get("Address") or ""))
        form.addRow("اسم المورد:", name_edit)
        form.addRow("الهاتف:", phone_edit)
        form.addRow("العنوان:", address_edit)
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
            values = (name_edit.text(), phone_edit.text(), address_edit.text())
            if supplier_id is None:
                repo.add_supplier(self.db, *values)
            else:
                repo.update_supplier(self.db, supplier_id, *values)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()
