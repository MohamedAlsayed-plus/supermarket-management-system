"""أدوات مشتركة لإنشاء جداول العرض وتعبئتها."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from app.formatting import date_time, money


def make_table(headers: Sequence[str]) -> tuple[QTableView, QStandardItemModel]:
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


def display(value: Any) -> str:
    if isinstance(value, (Decimal, float)):
        return money(value)
    if isinstance(value, (datetime, date)):
        return date_time(value)
    return str(value or "")


def fill(model: QStandardItemModel, rows: Sequence[Sequence[Any]]) -> None:
    model.setRowCount(0)
    for row in rows:
        cells = []
        for value in row:
            cell = QStandardItem(display(value))
            cell.setEditable(False)
            cell.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            cells.append(cell)
        model.appendRow(cells)
