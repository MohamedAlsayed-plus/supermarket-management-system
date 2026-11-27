"""لوحة التحكم: بطاقات مؤشرات قابلة للنقر + ملخص المبيعات والمخزون."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app import repository as repo
from app.db import friendly_error
from app.formatting import money
from app.icons import icon
from app.rtl import apply_rtl, show_error
from app.tabs.table_utils import fill, make_table


class KpiCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("KpiCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(190, 110)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, 28).pixmap(28, 28))
        header.addWidget(icon_label)
        header.addWidget(QLabel(title))
        header.addStretch(1)
        layout.addLayout(header)
        self.value_label = QLabel("0")
        self.value_label.setObjectName("KpiValue")
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001 - توقيع Qt
        self.clicked.emit()
        super().mousePressEvent(event)


class DashboardTab(QWidget):
    """on_navigate(page_index): انتقال إلى تبويب عند النقر على بطاقة."""

    def __init__(
        self, database, on_navigate: Callable[[int], None], user=None, parent=None  # noqa: ANN001
    ) -> None:
        super().__init__(parent)
        self.db = database
        self.user = user or {}
        self.on_navigate = on_navigate
        self._build_ui()
        apply_rtl(self)
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        title = QLabel("نظرة عامة على النظام")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        self.cards: dict[str, KpiCard] = {}
        specs = [
            ("today", "مبيعات اليوم", "money", 1),
            ("products", "المنتجات", "products", 2),
            ("low", "مخزون منخفض", "warning", 2),
            ("customers", "العملاء", "customers", 4),
            ("revenue", "إجمالي المبيعات", "reports", 10),
            ("suppliers", "الموردون", "suppliers", 5),
        ]
        grid = QGridLayout()
        for position, (key, label, icon_name, page) in enumerate(specs):
            card = KpiCard(label, icon_name)
            card.clicked.connect(lambda _checked=False, p=page: self.on_navigate(p))
            self.cards[key] = card
            grid.addWidget(card, position // 3, position % 3)
        root.addLayout(grid)

        panels = QHBoxLayout()
        self.sales_table, self.sales_model = make_table(
            ["الفاتورة", "العميل", "الإجمالي"]
        )
        self.stock_table, self.stock_model = make_table(
            ["المنتج", "الكمية", "حد الطلب"]
        )
        panels.addWidget(self.sales_table, 1)
        panels.addWidget(self.stock_table, 1)
        root.addLayout(panels, 1)

    def refresh(self) -> None:
        try:
            numbers = repo.dashboard_numbers(self.db)
            sales = repo.list_sales(self.db)[:6]
            stock = [row for row in repo.stock_report(self.db, True)][:6]
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.cards["today"].set_value(money(numbers.get("TodayRevenue", 0)))
        self.cards["products"].set_value(str(numbers.get("Products", 0)))
        self.cards["low"].set_value(str(numbers.get("LowStock", 0)))
        self.cards["customers"].set_value(str(numbers.get("Customers", 0)))
        self.cards["revenue"].set_value(money(numbers.get("Revenue", 0)))
        self.cards["suppliers"].set_value(str(numbers.get("Suppliers", 0)))
        fill(
            self.sales_model,
            [[row["SaleID"], row["CustomerName"], row["Total"]] for row in sales],
        )
        fill(
            self.stock_model,
            [[row["ProductName"], row["Quantity"], row["MinQuantity"]] for row in stock],
        )
