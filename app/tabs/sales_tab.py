"""تبويب المبيعات: بناء فاتورة، خصم المخزون، وحفظ المعاملة كاملة."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app import repository as repo
from app.db import Database, friendly_error
from app.formatting import money
from app.rtl import apply_rtl, keep_numbers_ltr, show_error, show_info, show_warning


class SalesTab(QWidget):
    """شاشة إنشاء الفواتير.

    on_saved: دالة اختيارية تُستدعى بعد حفظ فاتورة لتحديث تبويب التقارير.
    """

    def __init__(
        self,
        database: Database,
        on_saved: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = database
        self.on_saved = on_saved
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

        barcode_row = QHBoxLayout()
        self.barcode_edit = QLineEdit()
        self.barcode_edit.setPlaceholderText("امسح الباركود أو اكتبه ثم اضغط Enter")
        barcode_button = QPushButton("بحث")
        barcode_button.clicked.connect(self._on_barcode)
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

        self.add_item_button = QPushButton("إضافة إلى الفاتورة")
        self.add_item_button.clicked.connect(self._add_item)

        form.addRow("العميل:", self.customer_combo)
        form.addRow("الباركود:", barcode_row)
        form.addRow("المنتج:", self.product_combo)
        form.addRow("المخزون:", self.stock_label)
        form.addRow("الكمية:", self.quantity_spin)
        form.addRow("سعر الوحدة:", self.price_spin)
        form.addRow(self.add_item_button)
        layout.addWidget(invoice_group)

        self.model = QStandardItemModel(0, 4)
        self.model.setHorizontalHeaderLabels(
            ["المنتج", "الكمية", "سعر الوحدة", "الإجمالي"]
        )
        self.items_table = QTableView()
        self.items_table.setModel(self.model)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.verticalHeader().setVisible(False)
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.items_table)

        actions = QHBoxLayout()
        self.remove_item_button = QPushButton("إزالة المنتج")
        self.remove_item_button.clicked.connect(self._remove_item)
        self.new_button = QPushButton("فاتورة جديدة")
        self.new_button.clicked.connect(self._clear_invoice)
        actions.addWidget(self.remove_item_button)
        actions.addWidget(self.new_button)
        layout.addLayout(actions)

        self.total_label = QLabel("الإجمالي: 0.00")
        save_row = QHBoxLayout()
        self.save_button = QPushButton("حفظ الفاتورة")
        self.save_button.clicked.connect(self._save)
        save_row.addWidget(self.total_label)
        save_row.addStretch(1)
        save_row.addWidget(self.save_button)
        layout.addLayout(save_row)

        apply_rtl(self)
        keep_numbers_ltr(self.quantity_spin)
        keep_numbers_ltr(self.price_spin)

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
            self.product_combo.addItem(
                f"{row['ProductName']} ({barcode})", product_id
            )
        self._on_product_changed()

    def _on_product_changed(self, *_args: Any) -> None:
        product = self._products.get(self.product_combo.currentData())
        if product is None:
            self.stock_label.setText("المتوفر: -")
            return
        self.price_spin.setValue(float(product["Price"]))
        self.stock_label.setText(f"المتوفر: {product['Quantity']}")

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
        self.model.setRowCount(0)
        total = Decimal("0")
        for item in self._items:
            line_total = item["unit_price"] * item["quantity"]
            total += line_total
            row = [
                item["name"],
                str(item["quantity"]),
                money(item["unit_price"]),
                money(line_total),
            ]
            cells = []
            for value in row:
                cell = QStandardItem(value)
                cell.setEditable(False)
                cell.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                cells.append(cell)
            self.model.appendRow(cells)
        self.total_label.setText(f"الإجمالي: {money(total)}")

    def _clear_invoice(self) -> None:
        self._items = []
        self.model.setRowCount(0)
        self.total_label.setText("الإجمالي: 0.00")
        if self.customer_combo.count():
            self.customer_combo.setCurrentIndex(0)
        self.quantity_spin.setValue(1)
        self.barcode_edit.clear()

    def _save(self) -> None:
        if not self._items:
            show_warning(self, "أضف منتجًا واحدًا على الأقل قبل حفظ الفاتورة.")
            return
        try:
            sale_id = repo.create_sale(
                self.db, self.customer_combo.currentData(), self._items
            )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, f"تم حفظ الفاتورة رقم {sale_id} بنجاح.")
        self._clear_invoice()
        self._load_products()
        if self.on_saved is not None:
            self.on_saved()
