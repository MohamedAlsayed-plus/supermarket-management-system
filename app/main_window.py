"""النافذة الرئيسية: تنقل جانبي بأيقونات ولوحة تحكم ومظهر قابل للتبديل."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from app.config import load_config, save_config
from app.db import Database
from app.login_dialog import LoginDialog
from app.rtl import apply_rtl
from app.tabs.categories_tab import CategoriesTab
from app.tabs.customers_tab import CustomersTab
from app.tabs.dashboard_tab import DashboardTab
from app.tabs.movements_tab import MovementsTab
from app.tabs.products_tab import ProductsTab
from app.tabs.purchases_tab import PurchasesTab
from app.tabs.reports_tab import ReportsTab
from app.tabs.returns_tab import ReturnsTab
from app.tabs.sales_tab import SalesTab
from app.tabs.suppliers_tab import SuppliersTab
from app.tabs.users_tab import UsersTab
from app.theme import apply_theme, make_action, refresh_icons
from app.user_login_dialog import UserLoginDialog

PAGES = (
    ("لوحة التحكم", "dashboard"),
    ("المبيعات", "sales"),
    ("المنتجات", "products"),
    ("الأصناف", "categories"),
    ("العملاء", "customers"),
    ("الموردون", "suppliers"),
    ("المشتريات", "purchases"),
    ("المرتجعات", "returns"),
    ("حركات المخزون", "movements"),
    ("المستخدمون", "users"),
    ("التقارير", "reports"),
)


class MainWindow(QMainWindow):
    def __init__(self, database: Database, user: dict[str, Any]) -> None:
        super().__init__()
        self.db = database
        self.user = user
        self.setWindowTitle("نظام إدارة السوبر ماركت")
        self.resize(1400, 850)

        config = load_config()
        self.dark_mode = str(config.get("theme", "light")) == "dark"
        apply_theme(QApplication.instance(), self.dark_mode)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFixedWidth(200)
        self.nav.setIconSize(QSize(26, 26))
        self.pages = QStackedWidget()
        root.addWidget(self.nav)
        root.addWidget(self.pages, 1)

        toolbar = self.addToolBar("الأدوات")
        self.theme_action = make_action(
            self,
            "مظهر فاتح" if self.dark_mode else "مظهر داكن",
            "sun" if self.dark_mode else "moon",
            self.toggle_theme,
        )
        toolbar.addAction(
            make_action(self, "تغيير الاتصال", "database", self.change_connection)
        )
        toolbar.addAction(make_action(self, "تغيير المستخدم", "users", self.change_user))
        toolbar.addAction(self.theme_action)
        toolbar.addAction(make_action(self, "خروج", "logout", self.close))

        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self._build_pages()
        self._load_nav_icons()
        self.nav.setCurrentRow(0)
        apply_rtl(self)
        self._update_status()

    # ------------------------------------------------------------------
    def _build_pages(self) -> None:
        self.dashboard = DashboardTab(
            self.db, self.nav.setCurrentRow, self.user, self
        )
        self.reports_tab = ReportsTab(self.db, self.user, self)

        def after_sale() -> None:
            self.dashboard.refresh()
            self.reports_tab.refresh()

        self.sales_tab = SalesTab(
            self.db, on_saved=after_sale, user=self.user, parent=self
        )
        page_widgets = [
            self.dashboard,
            self.sales_tab,
            ProductsTab(self.db, self.user, self),
            CategoriesTab(self.db, self.user, self),
            CustomersTab(self.db, self.user, self),
            SuppliersTab(self.db, self.user, self),
            PurchasesTab(self.db, self.user, self),
            ReturnsTab(self.db, self.user, self),
            MovementsTab(self.db, self.user, self),
            UsersTab(self.db, self.user, self),
            self.reports_tab,
        ]
        while self.pages.count():
            old = self.pages.widget(0)
            self.pages.removeWidget(old)
            old.deleteLater()
        for widget in page_widgets:
            self.pages.addWidget(widget)
        self.pages.setCurrentIndex(self.nav.currentRow())

    def _load_nav_icons(self) -> None:
        self.nav.clear()
        from app.icons import icon

        for label, icon_name in PAGES:
            from PySide6.QtWidgets import QListWidgetItem

            item = QListWidgetItem(icon(icon_name, 26), label)
            item.setSizeHint(QSize(180, 42))
            self.nav.addItem(item)

    def _update_status(self) -> None:
        config = load_config()
        self.statusBar().showMessage(
            f"متصل بـ: {config['server']} / {config['database']} "
            f"| المستخدم: {self.user.get('FullName', '')} "
            f"({self.user.get('Role', '')})"
        )

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        apply_theme(QApplication.instance(), self.dark_mode)
        self.theme_action.setText("مظهر فاتح" if self.dark_mode else "مظهر داكن")
        self.theme_action.setProperty("icon_name", "sun" if self.dark_mode else "moon")
        refresh_icons(self)
        from app.icons import icon

        for row, (_label, icon_name) in enumerate(PAGES):
            item = self.nav.item(row)
            if item is not None:
                item.setIcon(icon(icon_name, 26))
        config = load_config()
        config["theme"] = "dark" if self.dark_mode else "light"
        save_config(config)

    def change_user(self) -> None:
        dialog = UserLoginDialog(self.db, self)
        if dialog.exec() != QDialog.Accepted or dialog.user is None:
            return
        self.user = dialog.user
        self._build_pages()
        self._update_status()

    def change_connection(self) -> None:
        dialog = LoginDialog(load_config(), self)
        if dialog.exec() != QDialog.Accepted or dialog.database is None:
            return
        user_dialog = UserLoginDialog(dialog.database, self)
        if user_dialog.exec() != QDialog.Accepted or user_dialog.user is None:
            dialog.database.close()
            return
        previous = self.db
        self.db = dialog.database
        self.user = user_dialog.user
        previous.close()
        self._build_pages()
        self._update_status()

    def closeEvent(self, event) -> None:  # noqa: ANN001 - توقيع Qt
        self.db.close()
        super().closeEvent(event)
