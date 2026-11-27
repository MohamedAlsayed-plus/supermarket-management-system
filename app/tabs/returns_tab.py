"""تبويب المرتجعات: إرجاع أصناف من فاتورة مع إعادة الكميات للمخزون."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
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
from app.db import friendly_error
from app.rtl import apply_rtl, ask_confirm, keep_numbers_ltr, show_error, show_info, show_warning
from app.tabs.table_utils import fill, make_table
from app.theme import make_button


class ReturnsTab(QWidget):
    def __init__(self, database, user=None, parent=None):  # noqa: ANN001
        super().__init__(parent)
        self.db = database
        self.user = user or {}
        self._sale_line_ids: list[int] = []
        self._return_lines: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        group = QGroupBox("مرتجع جديد")
        form = QFormLayout(group)
        self.sale_combo = QComboBox()
        self.sale_combo.currentIndexChanged.connect(self._load_sale_lines)
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("سبب الإرجاع (اختياري)")
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 100_000)
        keep_numbers_ltr(self.quantity_spin)
        form.addRow("الفاتورة:", self.sale_combo)
        form.addRow("السبب:", self.reason_edit)
        form.addRow("الكمية المرجعة:", self.quantity_spin)
        add_button = make_button(self, "إضافة للمرتجع", "add", self._add_line)
        form.addRow(add_button)
        root.addWidget(group)

        self.sale_table, self.sale_model = make_table(
            ["المنتج", "كمية البيع", "المُرجَع", "المتبقي"]
        )
        self.sale_table.clicked.connect(self._on_sale_line_clicked)
        root.addWidget(self.sale_table, 2)

        self.items_table, self.items_model = make_table(["المنتج", "الكمية المرجعة"])
        root.addWidget(self.items_table, 1)
        actions = QHBoxLayout()
        remove_button = make_button(self, "إزالة", "delete", self._remove_line)
        clear_button = make_button(self, "جديد", "refresh", self._clear)
        save_button = make_button(self, "حفظ المرتجع", "save", self._save)
        save_button.setDefault(True)
        actions.addStretch(1)
        actions.addWidget(remove_button)
        actions.addWidget(clear_button)
        actions.addWidget(save_button)
        root.addLayout(actions)

        root.addWidget(QLabel("المرتجعات المسجلة:"))
        self.table, self.model = make_table(
            ["الرقم", "التاريخ", "رقم الفاتورة", "المستخدم", "السبب", "القيمة"]
        )
        self.table.clicked.connect(self._load_details)
        root.addWidget(self.table, 2)
        self.details_table, self.details_model = make_table(
            ["المنتج", "الكمية", "سعر الوحدة", "القيمة"]
        )
        root.addWidget(self.details_table, 1)
        delete_button = make_button(self, "إلغاء المرتجع المحدد", "delete", self._delete)
        root.addWidget(delete_button)
        apply_rtl(self)

    def refresh(self) -> None:
        current_sale = self.sale_combo.currentData()
        try:
            sales = repo.list_sales(self.db)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.sale_combo.clear()
        for row in sales:
            self.sale_combo.addItem(
                f"#{row['SaleID']} - {row['CustomerName']} - {row['SaleDate']}",
                int(row["SaleID"]),
            )
        index = self.sale_combo.findData(current_sale)
        if index >= 0:
            self.sale_combo.setCurrentIndex(index)
        self._load_sale_lines()
        try:
            returns = repo.list_returns(self.db)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        fill(
            self.model,
            [
                [row["ReturnID"], row["ReturnDate"], row["SaleID"],
                 row["UserName"], row["Reason"], row["Total"]]
                for row in returns
            ],
        )
        self.details_model.setRowCount(0)

    def _load_sale_lines(self, *_args) -> None:
        self._sale_line_ids = []
        self.sale_model.setRowCount(0)
        sale_id = self.sale_combo.currentData()
        if sale_id is None:
            return
        try:
            lines = repo.get_sale_details(self.db, int(sale_id))
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        rows = []
        for line in lines:
            self._sale_line_ids.append(int(line["SaleDetailID"]))
            remaining = int(line["QuantitySold"]) - int(line["ReturnedQty"])
            rows.append(
                [line["ProductName"], line["QuantitySold"], line["ReturnedQty"], remaining]
            )
        fill(self.sale_model, rows)
        self._clear()

    def _on_sale_line_clicked(self, index) -> None:  # noqa: ANN001
        if not index.isValid():
            return
        remaining = int(self.sale_model.item(index.row(), 3).text())
        self.quantity_spin.setMaximum(max(remaining, 1))
        self.quantity_spin.setValue(max(remaining, 1))

    def _add_line(self) -> None:
        index = self.sale_table.currentIndex()
        if not index.isValid():
            show_warning(self, "اختر صنفًا من الفاتورة أولًا.")
            return
        remaining = int(self.sale_model.item(index.row(), 3).text())
        quantity = self.quantity_spin.value()
        if quantity > remaining:
            show_warning(self, f"الكمية القابلة للإرجاع هي {remaining} فقط.")
            return
        name = self.sale_model.item(index.row(), 0).text()
        self._return_lines.append(
            {"sale_detail_id": self._sale_line_ids[index.row()], "quantity": quantity, "name": name}
        )
        self._refresh_items()

    def _remove_line(self) -> None:
        index = self.items_table.currentIndex()
        if not index.isValid():
            show_warning(self, "اختر صنفًا من المرتجع أولًا.")
            return
        del self._return_lines[index.row()]
        self._refresh_items()

    def _refresh_items(self) -> None:
        fill(
            self.items_model,
            [[line["name"], line["quantity"]] for line in self._return_lines],
        )

    def _clear(self) -> None:
        self._return_lines = []
        self._refresh_items()
        self.quantity_spin.setValue(1)

    def _save(self) -> None:
        if self.sale_combo.currentData() is None:
            show_warning(self, "اختر فاتورة أولًا.")
            return
        if not self._return_lines:
            show_warning(self, "أضف صنفًا واحدًا على الأقل.")
            return
        try:
            return_id = repo.create_return(
                self.db,
                int(self.sale_combo.currentData()),
                self.user.get("UserID"),
                self.reason_edit.text(),
                self._return_lines,
            )
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, f"تم حفظ المرتجع رقم {return_id}.")
        self.refresh()

    def _load_details(self, index) -> None:  # noqa: ANN001
        if not index.isValid():
            return
        return_id = int(self.model.item(index.row(), 0).text())
        try:
            lines = repo.get_return_details(self.db, return_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        fill(
            self.details_model,
            [
                [line["ProductName"], line["QuantityReturned"],
                 line["UnitPrice"], line["LineTotal"]]
                for line in lines
            ],
        )

    def _delete(self) -> None:
        index = self.table.currentIndex()
        if not index.isValid():
            show_warning(self, "اختر مرتجعًا أولًا.")
            return
        if not ask_confirm(self, "سيتم خصم الكميات المرجعة من المخزون. هل تريد المتابعة؟"):
            return
        return_id = int(self.model.item(index.row(), 0).text())
        try:
            repo.delete_return(self.db, return_id)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, "تم إلغاء المرتجع.")
        self.refresh()
