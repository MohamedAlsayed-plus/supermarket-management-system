"""تبويب التقارير: المبيعات مع الفلاتر وتفاصيل الفواتير + تقرير المخزون."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import repository as repo
from app.db import Database, friendly_error
from app.formatting import date_time, money
from app.rtl import apply_rtl, ask_confirm, show_error, show_info, show_warning


def _make_table(headers: Sequence[str]) -> tuple[QTableView, QStandardItemModel]:
    model = QStandardItemModel(0, len(headers))
    model.setHorizontalHeaderLabels(list(headers))
    table = QTableView()
    table.setModel(model)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if headers:
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Stretch)
    return table, model


def _display(value: Any) -> str:
    if isinstance(value, (Decimal, float)):
        return money(value)
    if isinstance(value, (datetime, date)):
        return date_time(value)
    return str(value or "")


def _fill(model: QStandardItemModel, rows: Sequence[Sequence[Any]]) -> None:
    model.setRowCount(0)
    for row in rows:
        cells = []
        for value in row:
            cell = QStandardItem(_display(value))
            cell.setEditable(False)
            cell.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            cells.append(cell)
        model.appendRow(cells)


class ReportsTab(QTabWidget):
    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = database
        self._sale_ids: list[int] = []
        self.addTab(self._build_sales_tab(), "المبيعات")
        self.addTab(self._build_stock_tab(), "المخزون")
        self.currentChanged.connect(self._on_tab_changed)
        apply_rtl(self)
        self.refresh()

    # ------------------------------------------------------------------
    # فاتورة/مبيعات
    # ------------------------------------------------------------------
    def _build_sales_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        filters = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_to = QDateEdit()
        for edit in (self.date_from, self.date_to):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(self.date_from.date().addDays(-30))
        self.customer_filter = QComboBox()
        self.customer_filter.addItem("كل العملاء", None)
        refresh_button = QPushButton("تحديث")
        refresh_button.clicked.connect(self.refresh)
        delete_button = QPushButton("حذف الفاتورة")
        delete_button.clicked.connect(self._delete_sale)
        filters.addWidget(QLabel("من:"))
        filters.addWidget(self.date_from)
        filters.addWidget(QLabel("إلى:"))
        filters.addWidget(self.date_to)
        filters.addWidget(QLabel("العميل:"))
        filters.addWidget(self.customer_filter)
        filters.addWidget(refresh_button)
        filters.addWidget(delete_button)
        layout.addLayout(filters)

        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)

        self.sales_table, self.sales_model = _make_table(
            ["رقم الفاتورة", "التاريخ", "العميل", "الإجمالي"]
        )
        self.sales_table.clicked.connect(self._load_sale_details)
        layout.addWidget(self.sales_table, 2)

        layout.addWidget(QLabel("تفاصيل الفاتورة المحددة:"))
        self.details_table, self.details_model = _make_table(
            ["المنتج", "الكمية", "سعر الوحدة", "الإجمالي"]
        )
        layout.addWidget(self.details_table, 1)
        return widget

    def _build_stock_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        self.low_stock_check = QCheckBox("المخزون المنخفض فقط (10 أو أقل)")
        self.low_stock_check.stateChanged.connect(self.refresh_stock)
        stock_refresh = QPushButton("تحديث المخزون")
        stock_refresh.clicked.connect(self.refresh_stock)
        controls.addWidget(self.low_stock_check)
        controls.addStretch(1)
        controls.addWidget(stock_refresh)
        layout.addLayout(controls)
        self.stock_table, self.stock_model = _make_table(
            ["الرقم", "المنتج", "الصنف", "السعر", "الكمية", "الباركود"]
        )
        layout.addWidget(self.stock_table)
        return widget

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self.refresh()
        elif index == 1:
            self.refresh_stock()

    def showEvent(self, event) -> None:  # noqa: ANN001 - توقيع Qt
        super().showEvent(event)
        self.refresh()

    # ------------------------------------------------------------------
    # بيانات
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        try:
            customers = repo.list_customers(self.db)
            current_customer = self.customer_filter.currentData()
            self.customer_filter.clear()
            self.customer_filter.addItem("كل العملاء", None)
            for row in customers:
                self.customer_filter.addItem(
                    str(row["CustomerName"]), int(row["CustomerID"])
                )
            index = self.customer_filter.findData(current_customer)
            if index >= 0:
                self.customer_filter.setCurrentIndex(index)

            sales = repo.list_sales(
                self.db,
                customer_id=self.customer_filter.currentData(),
                date_from=self.date_from.date().toPython(),
                date_to=self.date_to.date().toPython(),
            )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return

        self._sale_ids = [int(row["SaleID"]) for row in sales]
        _fill(
            self.sales_model,
            [
                [
                    row["SaleID"],
                    row["SaleDate"],
                    row["CustomerName"],
                    row["Total"],
                ]
                for row in sales
            ],
        )
        total = sum((Decimal(str(row["Total"])) for row in sales), Decimal("0"))
        self.summary_label.setText(
            f"عدد الفواتير: {len(sales)}    |    إجمالي المبيعات: {money(total)}"
        )
        self.details_model.setRowCount(0)

    def refresh_stock(self) -> None:
        try:
            rows = repo.stock_report(self.db, self.low_stock_check.isChecked())
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        _fill(
            self.stock_model,
            [
                [
                    row["ProductID"],
                    row["ProductName"],
                    row["CategoryName"],
                    row["Price"],
                    row["Quantity"],
                    row["Barcode"],
                ]
                for row in rows
            ],
        )

    def _load_sale_details(self, index) -> None:  # noqa: ANN001 - توقيع Qt
        if not index.isValid() or index.row() >= len(self._sale_ids):
            return
        sale_id = self._sale_ids[index.row()]
        try:
            lines = repo.get_sale_details(self.db, sale_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        _fill(
            self.details_model,
            [
                [
                    line["ProductName"],
                    line["QuantitySold"],
                    line["UnitPrice"],
                    line["LineTotal"],
                ]
                for line in lines
            ],
        )

    def _delete_sale(self) -> None:
        index = self.sales_table.currentIndex()
        if not index.isValid() or index.row() >= len(self._sale_ids):
            show_warning(self, "اختر فاتورة أولًا.")
            return
        if not ask_confirm(
            self,
            "سيتم حذف الفاتورة وإعادة الكميات إلى المخزون. هل تريد المتابعة؟",
        ):
            return
        try:
            repo.delete_sale(self.db, self._sale_ids[index.row()])
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, "تم حذف الفاتورة وإعادة الكميات إلى المخزون.")
        self.refresh()
        self.refresh_stock()
