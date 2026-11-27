"""نافذة الاتصال: إعدادات السيرفر ونوع المصادقة وتهيئة قاعدة البيانات."""

from __future__ import annotations

from typing import Any, Mapping

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.config import load_config, save_config
from app.db import (
    Database,
    friendly_error,
    initialize_database,
    missing_tables,
    test_connection,
)
from app.rtl import apply_rtl, ask_confirm, show_error, show_info, show_warning


class LoginDialog(QDialog):
    """يخزّن الاتصال الناجح في self.database بعد accept()."""

    def __init__(
        self, config: Mapping[str, Any] | None = None, parent=None
    ) -> None:  # noqa: ANN001 - توقيع Qt
        super().__init__(parent)
        self.initial_config = dict(config or load_config())
        self.database: Database | None = None
        self.saved_config: dict[str, Any] = dict(self.initial_config)
        self._build_ui()
        self._auth_changed()
        apply_rtl(self)

    def _build_ui(self) -> None:
        self.setWindowTitle("الاتصال بقاعدة البيانات")

        form = QFormLayout()
        self.server_edit = QLineEdit(str(self.initial_config.get("server") or ""))
        self.server_edit.setPlaceholderText("مثال: localhost\\SQLEXPRESS")
        self.database_edit = QLineEdit(str(self.initial_config.get("database") or ""))
        self.database_edit.setPlaceholderText("SupermarketDB")

        self.auth_combo = QComboBox()
        self.auth_combo.addItem("مصادقة Windows (الحساب الحالي)", "windows")
        self.auth_combo.addItem("مصادقة SQL Server (اسم مستخدم وكلمة مرور)", "sql")
        auth_index = self.auth_combo.findData(
            self.initial_config.get("auth", "windows")
        )
        if auth_index >= 0:
            self.auth_combo.setCurrentIndex(auth_index)
        self.auth_combo.currentIndexChanged.connect(self._auth_changed)

        self.username_edit = QLineEdit(str(self.initial_config.get("username") or ""))
        self.password_edit = QLineEdit(str(self.initial_config.get("password") or ""))
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.save_password_check = QCheckBox("حفظ كلمة المرور في هذا الجهاز")
        self.save_password_check.setChecked(
            bool(self.initial_config.get("save_password", False))
        )

        form.addRow("اسم السيرفر:", self.server_edit)
        form.addRow("قاعدة البيانات:", self.database_edit)
        form.addRow("طريقة المصادقة:", self.auth_combo)
        form.addRow("اسم المستخدم:", self.username_edit)
        form.addRow("كلمة المرور:", self.password_edit)
        form.addRow(self.save_password_check)

        buttons = QHBoxLayout()
        test_button = QPushButton("اختبار الاتصال")
        test_button.clicked.connect(self._test_connection)
        init_button = QPushButton("تهيئة قاعدة البيانات")
        init_button.clicked.connect(self._initialize_database)
        ok_button = QPushButton("اتصال")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("إلغاء")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(test_button)
        buttons.addWidget(init_button)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addLayout(buttons)

    def _auth_changed(self, *_args: Any) -> None:
        sql_auth = self.auth_combo.currentData() == "sql"
        self.username_edit.setEnabled(sql_auth)
        self.password_edit.setEnabled(sql_auth)
        self.save_password_check.setEnabled(sql_auth)

    def values(self) -> tuple[dict[str, Any], str]:
        auth = self.auth_combo.currentData()
        password = self.password_edit.text() if auth == "sql" else ""
        config: dict[str, Any] = {
            "server": self.server_edit.text().strip(),
            "database": self.database_edit.text().strip() or "SupermarketDB",
            "auth": auth,
            "username": self.username_edit.text().strip(),
            "save_password": self.save_password_check.isChecked(),
            "password": password,
        }
        return config, password

    def _test_connection(self) -> None:
        config, password = self.values()
        try:
            missing = test_connection(config, password)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        if missing:
            show_warning(
                self,
                "تم الاتصال بنجاح، لكن الجداول التالية مفقودة:\n"
                + "، ".join(missing)
                + "\nيمكنك الضغط على «تهيئة قاعدة البيانات».",
            )
        else:
            show_info(self, "تم الاتصال بنجاح، وقاعدة البيانات جاهزة.")

    def _initialize_database(self) -> None:
        if not ask_confirm(
            self,
            "تحذير: سيتم حذف الجداول الخمسة وإعادة إنشائها بالبيانات التجريبية.\n"
            "أي بيانات موجودة حاليًا ستُحذف. هل تريد المتابعة؟",
            "تهيئة قاعدة البيانات",
        ):
            return
        config, password = self.values()
        try:
            initialize_database(config, password)
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        show_info(self, "تم تهيئة قاعدة البيانات بنجاح.")

    def accept(self) -> None:  # noqa: D102 - overriding Qt slot
        config, password = self.values()
        if not config["server"]:
            show_warning(self, "اكتب اسم السيرفر أولًا.")
            return
        if not config["database"]:
            show_warning(self, "اكتب اسم قاعدة البيانات أولًا.")
            return

        database: Database | None = None
        success = False
        try:
            database = Database(config, password).connect()
            missing = missing_tables(database)
            if missing:
                database.close()
                database = None
                if not ask_confirm(
                    self,
                    "الجداول المطلوبة غير موجودة:\n"
                    + "، ".join(missing)
                    + "\nهل تريد تهيئة قاعدة البيانات الآن؟",
                ):
                    return
                initialize_database(config, password)
                database = Database(config, password).connect()
                missing = missing_tables(database)
                if missing:
                    show_error(
                        self,
                        "لم يتم العثور على الجداول المطلوبة بعد التهيئة:\n"
                        + "، ".join(missing),
                    )
                    return
            success = True
        except Exception as exc:
            show_error(self, friendly_error(exc))
            return
        finally:
            if not success and database is not None:
                database.close()

        self.database = database
        self.saved_config = dict(config)
        self.saved_config["password"] = password if config["save_password"] else ""
        save_config(self.saved_config)
        super().accept()
