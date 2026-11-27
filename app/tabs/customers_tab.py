"""تبويب العملاء: CRUD + سداد رصيد الآجل."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
)

from app import repository as repo
from app.db import friendly_error
from app.formatting import money
from app.rtl import apply_rtl, ask_confirm, keep_numbers_ltr, show_error, show_info, show_warning
from app.theme import make_button
from app.tabs.base import TableTab


class CustomersTab(TableTab):
    headers = ("الرقم", "اسم العميل", "الهاتف", "الرصيد المستحق")

    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(database, user, parent)

    def _build_toolbar(self, toolbar: QHBoxLayout) -> None:
        self.pay_button = make_button(self, "سداد رصيد", "money", self._pay_balance)
        toolbar.addWidget(self.pay_button)

    def rows(self):
        return [
            [row["CustomerID"], row["CustomerName"], row["Phone"], row["Balance"]]
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
        self._open_form(customer_id, str(row["CustomerName"]), str(row["Phone"] or ""))

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

    def _pay_balance(self) -> None:
        customer_id = self.require_selection()
        if customer_id is None:
            return
        customer = repo.get_customer(self.db, customer_id)
        dialog = QDialog(self)
        dialog.setWindowTitle("سداد رصيد")
        form = QFormLayout(dialog)
        form.addRow("العميل:", QLabelReadOnly(str(customer["CustomerName"])))
        form.addRow("الرصيد الحالي:", QLabelReadOnly(money(customer["Balance"])))
        amount_edit = QDoubleSpinBox()
        amount_edit.setDecimals(2)
        amount_edit.setRange(0.01, 1_000_000)
        amount_edit.setValue(float(customer["Balance"] or 0) or 0.01)
        keep_numbers_ltr(amount_edit)
        form.addRow("المبلغ:", amount_edit)
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
            repo.pay_balance(self.db, customer_id, amount_edit.value())
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, "تم تسجيل السداد بنجاح.")
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


class QLabelReadOnly(QLineEdit):
    """حقل للقراءة فقط داخل نماذج العرض."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setReadOnly(True)
