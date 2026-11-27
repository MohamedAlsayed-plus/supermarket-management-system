"""تبويب المنتجات: CRUD + بحث + حد إعادة الطلب وسعر التكلفة."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
)

from app import repository as repo
from app.db import friendly_error
from app.rtl import apply_rtl, ask_confirm, keep_numbers_ltr, show_error, show_warning
from app.tabs.base import TableTab


class ProductsTab(TableTab):
    headers = (
        "الرقم", "اسم المنتج", "الصنف", "السعر", "التكلفة",
        "الكمية", "حد الطلب", "الباركود",
    )

    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(database, user, parent)

    def _build_toolbar(self, toolbar: QHBoxLayout) -> None:
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث بالاسم / الصنف / الباركود")
        self.search_edit.setMinimumWidth(240)
        self.search_edit.textChanged.connect(self.refresh)
        toolbar.addStretch(1)
        toolbar.addWidget(self.search_edit)

    def rows(self):
        return [
            [
                row["ProductID"], row["ProductName"], row["CategoryName"],
                row["Price"], row["CostPrice"], row["Quantity"],
                row["MinQuantity"], row["Barcode"],
            ]
            for row in repo.list_products(self.db, self.search_edit.text().strip())
        ]

    def add_item(self) -> None:
        self._open_form(None)

    def edit_item(self) -> None:
        product_id = self.require_selection()
        if product_id is None:
            return
        row = repo.get_product(self.db, product_id)
        if row is None:
            show_warning(self, "لم يتم العثور على المنتج.")
            return
        self._open_form(product_id, row)

    def delete_item(self) -> None:
        product_id = self.require_selection()
        if product_id is None:
            return
        if not ask_confirm(self, "هل تريد حذف هذا المنتج؟"):
            return
        try:
            repo.delete_product(self.db, product_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()

    def _category_combo(self, selected_id: int | None) -> QComboBox:
        combo = QComboBox()
        combo.addItem("بدون صنف", None)
        try:
            categories = repo.list_categories(self.db)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            categories = []
        for row in categories:
            combo.addItem(str(row["CategoryName"]), int(row["CategoryID"]))
        index = combo.findData(selected_id)
        if index >= 0:
            combo.setCurrentIndex(index)
        return combo

    def _open_form(self, product_id: int | None, row: dict | None = None) -> None:
        row = row or {}
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة منتج" if product_id is None else "تعديل منتج")
        form = QFormLayout(dialog)

        name_edit = QLineEdit(str(row.get("ProductName") or ""))
        category_combo = self._category_combo(row.get("CategoryID"))

        price_edit = QDoubleSpinBox()
        price_edit.setDecimals(2)
        price_edit.setRange(0, 1_000_000)
        price_edit.setValue(float(row.get("Price") or 0))
        keep_numbers_ltr(price_edit)

        cost_edit = QDoubleSpinBox()
        cost_edit.setDecimals(2)
        cost_edit.setRange(0, 1_000_000)
        cost_edit.setValue(float(row.get("CostPrice") or 0))
        keep_numbers_ltr(cost_edit)

        quantity_edit = QSpinBox()
        quantity_edit.setRange(0, 1_000_000)
        quantity_edit.setValue(int(row.get("Quantity") or 0))
        keep_numbers_ltr(quantity_edit)

        min_edit = QSpinBox()
        min_edit.setRange(0, 1_000_000)
        min_edit.setValue(int(row.get("MinQuantity") or 0))
        keep_numbers_ltr(min_edit)

        barcode_edit = QLineEdit(str(row.get("Barcode") or ""))
        barcode_edit.setPlaceholderText("اختياري - يجب أن يكون فريدًا")

        form.addRow("اسم المنتج:", name_edit)
        form.addRow("الصنف:", category_combo)
        form.addRow("سعر البيع:", price_edit)
        form.addRow("سعر التكلفة:", cost_edit)
        form.addRow("الكمية:", quantity_edit)
        form.addRow("حد إعادة الطلب:", min_edit)
        form.addRow("الباركود:", barcode_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        apply_rtl(dialog)

        if dialog.exec() != QDialog.Accepted:
            return
        values = (
            name_edit.text(),
            category_combo.currentData(),
            price_edit.value(),
            cost_edit.value(),
            quantity_edit.value(),
            min_edit.value(),
            barcode_edit.text(),
        )
        try:
            if product_id is None:
                repo.add_product(self.db, *values)
            else:
                repo.update_product(self.db, product_id, *values)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.refresh()
