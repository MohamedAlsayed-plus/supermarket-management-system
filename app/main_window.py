"""النافذة الرئيسية للبرنامج."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDialog, QMainWindow, QTabWidget, QToolBar

from app.config import load_config
from app.db import Database
from app.login_dialog import LoginDialog
from app.rtl import apply_rtl
from app.tabs.categories_tab import CategoriesTab
from app.tabs.customers_tab import CustomersTab
from app.tabs.products_tab import ProductsTab
from app.tabs.reports_tab import ReportsTab
from app.tabs.sales_tab import SalesTab


class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.db = database
        self.setWindowTitle("نظام إدارة السوبر ماركت")
        self.resize(1200, 760)

        self._build_tabs()
        toolbar = QToolBar("الأدوات")
        self.addToolBar(toolbar)
        reconnect_action = QAction("تغيير الاتصال", self)
        reconnect_action.triggered.connect(self.change_connection)
        quit_action = QAction("خروج", self)
        quit_action.triggered.connect(self.close)
        toolbar.addAction(reconnect_action)
        toolbar.addAction(quit_action)

        apply_rtl(self)
        self._update_status()

    def _build_tabs(self) -> None:
        self.reports_tab = ReportsTab(self.db)
        self.sales_tab = SalesTab(self.db, on_saved=self.reports_tab.refresh)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.sales_tab, "المبيعات")
        self.tabs.addTab(ProductsTab(self.db), "المنتجات")
        self.tabs.addTab(CategoriesTab(self.db), "الأصناف")
        self.tabs.addTab(CustomersTab(self.db), "العملاء")
        self.tabs.addTab(self.reports_tab, "التقارير")
        self.setCentralWidget(self.tabs)

    def _update_status(self) -> None:
        config = load_config()
        self.statusBar().showMessage(
            f"متصل بـ: {config['server']} / {config['database']}"
        )

    def change_connection(self) -> None:
        dialog = LoginDialog(load_config(), self)
        if dialog.exec() != QDialog.Accepted or dialog.database is None:
            return
        previous = self.db
        self.db = dialog.database
        previous.close()
        self._build_tabs()
        apply_rtl(self)
        self._update_status()

    def closeEvent(self, event) -> None:  # noqa: ANN001 - توقيع Qt
        self.db.close()
        super().closeEvent(event)
