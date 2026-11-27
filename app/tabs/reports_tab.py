"""تبويب التقارير: المبيعات، المخزون، ورسوم بيانية."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import repository as repo
from app.db import friendly_error
from app.formatting import money
from app.rtl import apply_rtl, ask_confirm, show_error, show_info, show_warning
from app.tabs.table_utils import fill, make_table
from app.theme import make_button

PAYMENT_LABELS = {"cash": "نقدي", "card": "بطاقة", "credit": "آجل"}


class ReportsTab(QTabWidget):
    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(parent)
        self.db = database
        self.user = user or {}
        self._sale_ids: list[int] = []
        self.addTab(self._build_sales_tab(), "المبيعات")
        self.addTab(self._build_stock_tab(), "المخزون")
        self.addTab(self._build_charts_tab(), "الرسوم البيانية")
        self.currentChanged.connect(self._on_tab_changed)
        apply_rtl(self)
        self.refresh()

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
        refresh_button = make_button(self, "تحديث", "refresh", self.refresh)
        delete_button = make_button(self, "حذف الفاتورة", "delete", self._delete_sale)
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
        self.sales_table, self.sales_model = make_table(
            ["رقم الفاتورة", "التاريخ", "العميل", "الدفع", "المستخدم", "الإجمالي"]
        )
        self.sales_table.clicked.connect(self._load_sale_details)
        layout.addWidget(self.sales_table, 2)
        layout.addWidget(QLabel("تفاصيل الفاتورة المحددة:"))
        self.details_table, self.details_model = make_table(
            ["المنتج", "الكمية", "سعر الوحدة", "الإجمالي", "المُرجَع"]
        )
        layout.addWidget(self.details_table, 1)
        return widget

    def _build_stock_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        controls = QHBoxLayout()
        self.low_stock_check = QCheckBox("المنتجات التي وصلت لحد إعادة الطلب")
        self.low_stock_check.stateChanged.connect(self.refresh_stock)
        controls.addWidget(self.low_stock_check)
        controls.addStretch(1)
        controls.addWidget(make_button(self, "تحديث المخزون", "refresh", self.refresh_stock))
        layout.addLayout(controls)
        self.stock_table, self.stock_model = make_table(
            ["الرقم", "المنتج", "الصنف", "السعر", "التكلفة", "الكمية", "حد الطلب", "الباركود"]
        )
        layout.addWidget(self.stock_table)
        return widget

    def _build_charts_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.sales_chart_view = QChartView()
        self.sales_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.products_chart_view = QChartView()
        self.products_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(QLabel("مبيعات آخر 7 أيام"))
        layout.addWidget(self.sales_chart_view, 1)
        layout.addWidget(QLabel("المنتجات الأكثر مبيعًا"))
        layout.addWidget(self.products_chart_view, 1)
        return widget

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self.refresh()
        elif index == 1:
            self.refresh_stock()
        elif index == 2:
            self.refresh_charts()

    def showEvent(self, event) -> None:  # noqa: ANN001 - توقيع Qt
        super().showEvent(event)
        self.refresh()
        if self.currentIndex() == 2:
            self.refresh_charts()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        try:
            customers = repo.list_customers(self.db)
            current_customer = self.customer_filter.currentData()
            self.customer_filter.clear()
            self.customer_filter.addItem("كل العملاء", None)
            for row in customers:
                self.customer_filter.addItem(str(row["CustomerName"]), int(row["CustomerID"]))
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
        fill(
            self.sales_model,
            [
                [
                    row["SaleID"], row["SaleDate"], row["CustomerName"],
                    PAYMENT_LABELS.get(str(row["PaymentMethod"]), row["PaymentMethod"]),
                    row["UserName"], row["Total"],
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
        fill(
            self.stock_model,
            [
                [
                    row["ProductID"], row["ProductName"], row["CategoryName"],
                    row["Price"], row["CostPrice"], row["Quantity"],
                    row["MinQuantity"], row["Barcode"],
                ]
                for row in rows
            ],
        )

    def refresh_charts(self) -> None:
        try:
            by_day = repo.sales_by_day(self.db, 7)
            top = repo.top_products(self.db, 5)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.sales_chart_view.setChart(
            self._bar_chart(
                "مبيعات آخر 7 أيام",
                [str(row["SaleDay"]) for row in by_day],
                [float(row["Total"]) for row in by_day],
                "القيمة",
            )
        )
        self.products_chart_view.setChart(
            self._bar_chart(
                "المنتجات الأكثر مبيعًا",
                [str(row["ProductName"]) for row in top],
                [float(row["QuantitySold"]) for row in top],
                "الكمية",
            )
        )

    @staticmethod
    def _bar_chart(title: str, categories: list[str], values: list[float], axis: str) -> QChart:
        series = QBarSeries()
        bar_set = QBarSet(axis)
        for value in values:
            bar_set.append(value)
        series.append(bar_set)
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(title)
        chart.setAnimationEnabled(True)
        chart.legend().setVisible(False)
        names = QBarCategoryAxis()
        names.append(categories)
        chart.addAxis(names, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(names)
        numbers = QValueAxis()
        numbers.setMin(0)
        chart.addAxis(numbers, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(numbers)
        return chart

    def _load_sale_details(self, index) -> None:  # noqa: ANN001
        if not index.isValid() or index.row() >= len(self._sale_ids):
            return
        try:
            lines = repo.get_sale_details(self.db, self._sale_ids[index.row()])
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        fill(
            self.details_model,
            [
                [
                    line["ProductName"], line["QuantitySold"], line["UnitPrice"],
                    line["LineTotal"], line["ReturnedQty"],
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
