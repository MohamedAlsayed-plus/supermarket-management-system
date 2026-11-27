"""تبويب الأصناف: إضافة وتعديل وحذف أصناف المنتجات."""

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


class CategoriesTab(TableTab):
    headers = ("الرقم", "اسم الصنف")

    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(database, user, parent)

    def rows(self):
        return [
            [row["CategoryID"], row["CategoryName"]]
            for row in repo.list_categories(self.db)
        ]

    def add_item(self) -> None:
        self._open_form(None, "")

    def edit_item(self) -> None:
        category_id = self.require_selection()
        if category_id is None:
            return
        row = repo.get_category(self.db, category_id)
        if row is None:
            show_warning(self, "لم يتم العثور على الصنف.")
            return
        self._open_form(category_id, str(row["CategoryName"]))

    def delete_item(self) -> None:
        category_id = self.require_selection()
        if category_id is None:
            return
        if not ask_confirm(self, "هل تريد حذف هذا الصنف؟"):
            return
        try:
            repo.delete_category(self.db, category_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()

    def _open_form(self, category_id: int | None, name: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة صنف" if category_id is None else "تعديل صنف")
        form = QFormLayout(dialog)
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("اكتب اسم الصنف")
        form.addRow("اسم الصنف:", name_edit)
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
            if category_id is None:
                repo.add_category(self.db, name_edit.text())
            else:
                repo.update_category(self.db, category_id, name_edit.text())
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()
