"""تبويب حركات المخزون: سجل كل إضافة وبيع ومرتجع وتعديل."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app import repository as repo
from app.db import friendly_error
from app.rtl import apply_rtl, show_error
from app.tabs.table_utils import fill, make_table
from app.theme import make_button

TYPE_LABELS = {
    "purchase": "شراء",
    "sale": "بيع",
    "return": "مرتجع",
    "adjustment": "تعديل",
}


class MovementsTab(QWidget):
    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(parent)
        self.db = database
        self.user = user or {}

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.product_combo = QComboBox()
        self.type_combo = QComboBox()
        self.type_combo.addItem("كل الحركات", None)
        for key, label in TYPE_LABELS.items():
            self.type_combo.addItem(label, key)
        self.date_from = QDateEdit()
        self.date_to = QDateEdit()
        for edit in (self.date_from, self.date_to):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(self.date_from.date().addDays(-30))
        self.count_label = QLabel("")
        refresh_button = make_button(self, "تحديث", "refresh", self.refresh)
        controls.addWidget(QLabel("المنتج:"))
        controls.addWidget(self.product_combo)
        controls.addWidget(QLabel("النوع:"))
        controls.addWidget(self.type_combo)
        controls.addWidget(QLabel("من:"))
        controls.addWidget(self.date_from)
        controls.addWidget(QLabel("إلى:"))
        controls.addWidget(self.date_to)
        controls.addWidget(refresh_button)
        layout.addLayout(controls)

        self.table, self.model = make_table(
            ["الرقم", "التاريخ", "المنتج", "النوع", "الكمية", "الرصيد بعد", "المستخدم", "ملاحظات"]
        )
        layout.addWidget(self.table)
        layout.addWidget(self.count_label)
        apply_rtl(self)
        self.refresh()

    def refresh(self) -> None:
        try:
            products = repo.list_products(self.db)
            current_product = self.product_combo.currentData()
            self.product_combo.clear()
            self.product_combo.addItem("كل المنتجات", None)
            for row in products:
                self.product_combo.addItem(str(row["ProductName"]), int(row["ProductID"]))
            index = self.product_combo.findData(current_product)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)

            rows = repo.list_movements(
                self.db,
                product_id=self.product_combo.currentData(),
                movement_type=self.type_combo.currentData(),
                date_from=self.date_from.date().toPython(),
                date_to=self.date_to.date().toPython(),
            )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        fill(
            self.model,
            [
                [
                    row["MovementID"], row["MovementDate"], row["ProductName"],
                    TYPE_LABELS.get(str(row["MovementType"]), row["MovementType"]),
                    row["Quantity"], row["BalanceAfter"], row["UserName"], row["Notes"],
                ]
                for row in rows
            ],
        )
        self.count_label.setText(f"عدد الحركات: {len(rows)}")
