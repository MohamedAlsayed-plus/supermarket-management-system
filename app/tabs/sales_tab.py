"""تبويب المبيعات: فاتورة تفاعلية مع وسيلة دفع وحركات مخزون."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app import repository as repo
from app.db import Database, friendly_error
from app.formatting import money
from app.rtl import apply_rtl, keep_numbers_ltr, show_error, show_info, show_warning
from app.tabs.table_utils import fill, make_table
from app.theme import make_button

PAYMENT_LABELS = {"cash": "نقدي", "card": "بطاقة", "credit": "آجل"}


class SalesTab(QWidget):
    """on_saved: لتحديث التقارير واللوحة بعد كل فاتورة."""

    def __init__(
        self,
        database: Database,
        on_saved: Callable[[], None] | None = None,
        user: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = database
        self.on_saved = on_saved
        self.user = user or {}
        self._items: list[dict[str, Any]] = []
        self._products: dict[int, dict[str, Any]] = {}
        self._build_ui()
        self._load_customers()
        self._load_products()
        self._clear_invoice()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        invoice_group = QGroupBox("بيانات الفاتورة")
        form = QFormLayout(invoice_group)
        self.customer_combo = QComboBox()
        self.customer_combo.addItem("عميل نقدي (بدون اسم)", None)
        self.payment_combo = QComboBox()
        for key, label in PAYMENT_LABELS.items():
            self.payment_combo.addItem(label, key)

        barcode_row = QHBoxLayout()
        self.barcode_edit = QLineEdit()
        self.barcode_edit.setPlaceholderText("امسح الباركود أو اكتبه ثم اضغط Enter")
        barcode_button = make_button(self, "بحث", "barcode", self._on_barcode)
        self.barcode_edit.returnPressed.connect(self._on_barcode)
        barcode_row.addWidget(self.barcode_edit)
        barcode_row.addWidget(barcode_button)

        self.product_combo = QComboBox()
        self.product_combo.currentIndexChanged.connect(self._on_product_changed)
        self.stock_label = QLabel("المتوفر: -")
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 1_000_000)
        self.quantity_spin.setValue(1)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setDecimals(2)
        self.price_spin.setRange(0, 1_000_000)
        keep_numbers_ltr(self.quantity_spin)
        keep_numbers_ltr(self.price_spin)
        add_button = make_button(self, "إضافة إلى الفاتورة", "add", self._add_item)

        form.addRow("العميل:", self.customer_combo)
        form.addRow("طريقة الدفع:", self.payment_combo)
        form.addRow("الباركود:", barcode_row)
        form.addRow("المنتج:", self.product_combo)
        form.addRow("المخزون:", self.stock_label)
        form.addRow("الكمية:", self.quantity_spin)
        form.addRow("سعر الوحدة:", self.price_spin)
        form.addRow(add_button)
        layout.addWidget(invoice_group)

        self.items_table, self.items_model = make_table(
            ["المنتج", "الكمية", "سعر الوحدة", "الإجمالي"]
        )
        layout.addWidget(self.items_table, 1)

        actions = QHBoxLayout()
        remove_button = make_button(self, "إزالة المنتج", "delete", self._remove_item)
        new_button = make_button(self, "فاتورة جديدة", "refresh", self._clear_invoice)
        actions.addWidget(remove_button)
        actions.addWidget(new_button)
        layout.addLayout(actions)

        self.total_label = QLabel("الإجمالي: 0.00")
        save_row = QHBoxLayout()
        save_button = make_button(self, "حفظ الفاتورة", "save", self._save)
        save_button.setDefault(True)
        save_row.addWidget(self.total_label)
        save_row.addStretch(1)
        save_row.addWidget(save_button)
        layout.addLayout(save_row)
        apply_rtl(self)

    def _load_customers(self) -> None:
        try:
            customers = repo.list_customers(self.db)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.customer_combo.clear()
        self.customer_combo.addItem("عميل نقدي (بدون اسم)", None)
        for row in customers:
            self.customer_combo.addItem(str(row["CustomerName"]), int(row["CustomerID"]))

    def _load_products(self) -> None:
        try:
            products = repo.list_products(self.db)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self._products = {int(row["ProductID"]): row for row in products}
        self.product_combo.clear()
        for product_id, row in self._products.items():
            barcode = str(row["Barcode"] or "-")
            self.product_combo.addItem(f"{row['ProductName']} ({barcode})", product_id)
        self._on_product_changed()

    def _on_product_changed(self, *_args: Any) -> None:
        product = self._products.get(self.product_combo.currentData())
        if product is None:
            self.stock_label.setText("المتوفر: -")
            return
        self.price_spin.setValue(float(product["Price"]))
        self.stock_label.setText(
            f"المتوفر: {product['Quantity']} | حد الطلب: {product['MinQuantity']}"
        )

    def _on_barcode(self) -> None:
        barcode = self.barcode_edit.text().strip()
        if not barcode:
            show_warning(self, "اكتب الباركود أولًا.")
            return
        try:
            product = repo.get_product_by_barcode(self.db, barcode)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        if product is None:
            show_warning(self, "لا يوجد منتج بهذا الباركود.")
            return
        index = self.product_combo.findData(int(product["ProductID"]))
        if index >= 0:
            self.product_combo.setCurrentIndex(index)
        self.barcode_edit.clear()
        self.quantity_spin.setFocus()

    def _add_item(self) -> None:
        product_id = self.product_combo.currentData()
        product = self._products.get(product_id)
        if product is None:
            show_warning(self, "اختر منتجًا أولًا.")
            return
        quantity = self.quantity_spin.value()
        already = sum(
            item["quantity"] for item in self._items if item["product_id"] == product_id
        )
        available = int(product["Quantity"])
        if already + quantity > available:
            show_warning(
                self,
                f"الكمية المتوفرة من «{product['ProductName']}» هي {available} فقط.",
            )
            return
        self._items.append(
            {
                "product_id": product_id,
                "name": str(product["ProductName"]),
                "quantity": quantity,
                "unit_price": Decimal(str(self.price_spin.value())),
            }
        )
        self._refresh_items()
        self.quantity_spin.setValue(1)

    def _remove_item(self) -> None:
        index = self.items_table.currentIndex()
        if not index.isValid():
            show_warning(self, "اختر منتجًا من الفاتورة أولًا.")
            return
        del self._items[index.row()]
        self._refresh_items()

    def _refresh_items(self) -> None:
        total = Decimal("0")
        rows = []
        for item in self._items:
            line_total = item["unit_price"] * item["quantity"]
            total += line_total
            rows.append(
                [
                    item["name"],
                    item["quantity"],
                    money(item["unit_price"]),
                    money(line_total),
                ]
            )
        fill(self.items_model, rows)
        self.total_label.setText(f"الإجمالي: {money(total)}")

    def _clear_invoice(self) -> None:
        self._items = []
        self.items_model.setRowCount(0)
        self.total_label.setText("الإجمالي: 0.00")
        if self.customer_combo.count():
            self.customer_combo.setCurrentIndex(0)
        self.payment_combo.setCurrentIndex(0)
        self.quantity_spin.setValue(1)
        self.barcode_edit.clear()

    def _save(self) -> None:
        if not self._items:
            show_warning(self, "أضف منتجًا واحدًا على الأقل قبل حفظ الفاتورة.")
            return
        try:
            sale_id = repo.create_sale(
                self.db,
                self.customer_combo.currentData(),
                self.payment_combo.currentData(),
                self.user.get("UserID"),
                self._items,
            )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, f"تم حفظ الفاتورة رقم {sale_id} بنجاح.")
        self._clear_invoice()
        self._load_products()
        self._load_customers()
        if self.on_saved is not None:
            self.on_saved()
