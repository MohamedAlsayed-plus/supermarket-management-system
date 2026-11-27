"""تبويب المشتريات: فواتير شراء تزيد المخزون وتحدّث سعر التكلفة."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app import repository as repo
from app.db import friendly_error
from app.formatting import money
from app.rtl import apply_rtl, ask_confirm, keep_numbers_ltr, show_error, show_info, show_warning
from app.tabs.table_utils import fill, make_table
from app.theme import make_button


class PurchasesTab(QWidget):
    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(parent)
        self.db = database
        self.user = user or {}
        self._lines: list[dict] = []
        self._products: dict[int, dict] = {}
        self._build_ui()
        self._load_suppliers()
        self._load_products()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        group = QGroupBox("فاتورة شراء جديدة")
        form = QFormLayout(group)
        self.supplier_combo = QComboBox()
        self.product_combo = QComboBox()
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 1_000_000)
        self.quantity_spin.setValue(1)
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setDecimals(2)
        self.cost_spin.setRange(0, 1_000_000)
        form.addRow("المورد:", self.supplier_combo)
        form.addRow("المنتج:", self.product_combo)
        form.addRow("الكمية:", self.quantity_spin)
        form.addRow("سعر التكلفة:", self.cost_spin)
        add_button = make_button(self, "إضافة للفاتورة", "add", self._add_item)
        form.addRow(add_button)
        root.addWidget(group)

        self.items_table, self.items_model = make_table(
            ["المنتج", "الكمية", "سعر التكلفة", "الإجمالي"]
        )
        root.addWidget(self.items_table, 2)

        actions = QHBoxLayout()
        self.total_label = QLabel("الإجمالي: 0.00")
        remove_button = make_button(self, "إزالة الصنف", "delete", self._remove_item)
        clear_button = make_button(self, "جديدة", "refresh", self._clear)
        save_button = make_button(self, "حفظ الشراء", "save", self._save)
        save_button.setDefault(True)
        actions.addWidget(self.total_label)
        actions.addStretch(1)
        actions.addWidget(remove_button)
        actions.addWidget(clear_button)
        actions.addWidget(save_button)
        root.addLayout(actions)

        root.addWidget(QLabel("فواتير الشراء السابقة:"))
        self.table, self.model = make_table(
            ["الرقم", "التاريخ", "المورد", "المستخدم", "الإجمالي"]
        )
        self.table.clicked.connect(self._load_details)
        root.addWidget(self.table, 2)
        self.details_table, self.details_model = make_table(
            ["المنتج", "الكمية", "سعر التكلفة", "الإجمالي"]
        )
        root.addWidget(self.details_table, 1)
        delete_button = make_button(self, "إلغاء الشراء المحدد", "delete", self._delete)
        root.addWidget(delete_button)

        apply_rtl(self)
        keep_numbers_ltr(self.quantity_spin)
        keep_numbers_ltr(self.cost_spin)

    def _load_suppliers(self) -> None:
        try:
            suppliers = repo.list_suppliers(self.db)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.supplier_combo.clear()
        self.supplier_combo.addItem("بدون مورد", None)
        for row in suppliers:
            self.supplier_combo.addItem(str(row["SupplierName"]), int(row["SupplierID"]))

    def _load_products(self) -> None:
        try:
            products = repo.list_products(self.db)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self._products = {int(row["ProductID"]): row for row in products}
        self.product_combo.clear()
        for product_id, row in self._products.items():
            self.product_combo.addItem(str(row["ProductName"]), product_id)
        self.product_combo.currentIndexChanged.connect(self._on_product_changed)
        self._on_product_changed()

    def _on_product_changed(self, *_args) -> None:
        product = self._products.get(self.product_combo.currentData())
        if product is not None:
            self.cost_spin.setValue(float(product["CostPrice"]))

    def _add_item(self) -> None:
        product_id = self.product_combo.currentData()
        product = self._products.get(product_id)
        if product is None:
            show_warning(self, "اختر منتجًا أولًا.")
            return
        self._lines.append(
            {
                "product_id": product_id,
                "name": str(product["ProductName"]),
                "quantity": self.quantity_spin.value(),
                "unit_cost": Decimal(str(self.cost_spin.value())),
            }
        )
        self._refresh_items()

    def _remove_item(self) -> None:
        index = self.items_table.currentIndex()
        if not index.isValid():
            show_warning(self, "اختر صنفًا من الفاتورة أولًا.")
            return
        del self._lines[index.row()]
        self._refresh_items()

    def _refresh_items(self) -> None:
        total = Decimal("0")
        rows = []
        for line in self._lines:
            line_total = line["unit_cost"] * line["quantity"]
            total += line_total
            rows.append(
                [line["name"], line["quantity"], money(line["unit_cost"]), money(line_total)]
            )
        fill(self.items_model, rows)
        self.total_label.setText(f"الإجمالي: {money(total)}")

    def _clear(self) -> None:
        self._lines = []
        self._refresh_items()
        self.quantity_spin.setValue(1)

    def _save(self) -> None:
        if not self._lines:
            show_warning(self, "أضف منتجًا واحدًا على الأقل.")
            return
        try:
            purchase_id = repo.create_purchase(
                self.db,
                self.supplier_combo.currentData(),
                self.user.get("UserID"),
                "",
                self._lines,
            )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, f"تم حفظ فاتورة الشراء رقم {purchase_id}.")
        self._clear()
        self.refresh()

    def refresh(self) -> None:
        try:
            rows = repo.list_purchases(self.db)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        fill(
            self.model,
            [
                [row["PurchaseID"], row["PurchaseDate"], row["SupplierName"],
                 row["UserName"], row["Total"]]
                for row in rows
            ],
        )
        self.details_model.setRowCount(0)

    def _load_details(self, index) -> None:  # noqa: ANN001
        if not index.isValid():
            return
        purchase_id = int(self.model.item(index.row(), 0).text())
        try:
            lines = repo.get_purchase_details(self.db, purchase_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        fill(
            self.details_model,
            [
                [line["ProductName"], line["QuantityPurchased"],
                 line["UnitCost"], line["LineTotal"]]
                for line in lines
            ],
        )

    def _delete(self) -> None:
        index = self.table.currentIndex()
        if not index.isValid():
            show_warning(self, "اختر فاتورة شراء أولًا.")
            return
        if not ask_confirm(
            self, "سيتم خصم الكميات المشتراة من المخزون. هل تريد إلغاء الفاتورة؟"
        ):
            return
        purchase_id = int(self.model.item(index.row(), 0).text())
        try:
            repo.delete_purchase(self.db, purchase_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, "تم إلغاء فاتورة الشراء.")
        self.refresh()
