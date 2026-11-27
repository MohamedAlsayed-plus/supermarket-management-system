"""أساس مشترك لتبويبات الجداول (عرض + أزرار إضافة/تعديل/حذف)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.db import Database, friendly_error
from app.formatting import money
from app.rtl import apply_rtl, show_error
from app.theme import make_button


class TableTab(QWidget):
    headers: Sequence[str] = ()

    def __init__(
        self,
        database: Database,
        user: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = database
        self.user = user or {}

        layout = QVBoxLayout(self)
        self.toolbar = QHBoxLayout()
        layout.addLayout(self.toolbar)

        self.model = QStandardItemModel(0, len(self.headers))
        self.model.setHorizontalHeaderLabels(list(self.headers))
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if self.headers:
            header.setSectionResizeMode(
                len(self.headers) - 1, QHeaderView.ResizeMode.Stretch
            )
        layout.addWidget(self.table)

        self.count_label = QLabel("")
        layout.addWidget(self.count_label)

        self._add_default_buttons()
        self._build_toolbar(self.toolbar)
        apply_rtl(self)
        self.refresh()

    def _add_default_buttons(self) -> None:
        self.add_button = make_button(self, "إضافة", "add", self.add_item)
        self.edit_button = make_button(self, "تعديل", "edit", self.edit_item)
        self.delete_button = make_button(self, "حذف", "delete", self.delete_item)
        self.refresh_button = make_button(self, "تحديث", "refresh", self.refresh)
        for button in (
            self.add_button,
            self.edit_button,
            self.delete_button,
            self.refresh_button,
        ):
            self.toolbar.addWidget(button)

    def _build_toolbar(self, toolbar: QHBoxLayout) -> None:
        """نقطة توسعة للتبويبات التي تحتاج بحثًا أو فلاتر."""

    def rows(self) -> list[Sequence[Any]]:
        raise NotImplementedError

    def refresh(self) -> None:
        try:
            data = self.rows()
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        self.model.setRowCount(0)
        for row in data:
            items: list[QStandardItem] = []
            for value in row:
                if isinstance(value, Decimal):
                    text = money(value)
                elif isinstance(value, float):
                    text = money(value)
                else:
                    text = str(value or "")
                item = QStandardItem(text)
                item.setEditable(False)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                items.append(item)
            self.model.appendRow(items)
        self.count_label.setText(f"عدد السجلات: {len(data)}")

    def current_id(self) -> int | None:
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        item = self.model.item(index.row(), 0)
        if item is None:
            return None
        try:
            return int(item.text().replace(",", ""))
        except ValueError:
            return None

    def require_selection(self) -> int | None:
        selected = self.current_id()
        if selected is None:
            from app.rtl import show_warning

            show_warning(self, "اختر سجلًا أولًا من الجدول.")
        return selected

    def add_item(self) -> None:
        raise NotImplementedError

    def edit_item(self) -> None:
        raise NotImplementedError

    def delete_item(self) -> None:
        raise NotImplementedError
