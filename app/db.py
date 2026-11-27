"""طبقة الاتصال بقاعدة بيانات SQL Server.

كل الاستعلامات تمر عبر هذه الطبقة، لذلك بقاء التبديل بين قاعدة بيانات حقيقية
وصيغة أخرى (لو لزم يومًا ما) لا يلمس بقية الكود.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Sequence

import pyodbc

from app.config import read_schema_script

PREFERRED_DRIVERS = (
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 16 for SQL Server",
    "SQL Server Native Client 11.0",
)

REQUIRED_TABLES = (
    "Users",
    "Categories",
    "Suppliers",
    "Products",
    "Customers",
    "Sales",
    "SaleDetails",
    "Purchases",
    "PurchaseDetails",
    "SalesReturns",
    "ReturnDetails",
    "StockMovements",
)


class DatabaseError(Exception):
    """خطأ مفهوم من وجهة نظر المستخدم."""


def available_drivers() -> list[str]:
    try:
        return list(pyodbc.drivers())
    except Exception:
        return []


def find_driver() -> str:
    installed = available_drivers()
    for name in PREFERRED_DRIVERS:
        if name in installed:
            return name
    for name in installed:
        if "SQL Server" in name or "sqlsrv" in name.lower():
            return name
    raise DatabaseError(
        "لم يتم العثور على برنامج ODBC الخاص بـ SQL Server.\n"
        "ثبّت ODBC Driver 17 أو 18 for SQL Server ثم أعد تشغيل البرنامج.\n"
        f"برامج ODBC المثبتة: {', '.join(installed) if installed else 'لا يوجد'}"
    )


def build_connection_string(
    config: Mapping[str, Any],
    driver: str | None = None,
    password: str | None = None,
    database: str | None = None,
) -> str:
    driver = driver or find_driver()
    server = str(config.get("server") or "").strip() or "localhost"
    db_name = database or str(config.get("database") or "SupermarketDB").strip()
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={db_name}",
    ]
    if driver.startswith("ODBC Driver") or driver.startswith("Microsoft ODBC Driver"):
        parts.append("TrustServerCertificate=yes")
    if config.get("auth") == "sql":
        parts.append(f"UID={config.get('username') or ''}")
        parts.append(f"PWD={password if password is not None else config.get('password') or ''}")
    else:
        parts.append("Trusted_Connection=yes")
    return ";".join(parts) + ";"


def friendly_error(exc: Exception) -> str:
    """تحويل أخطاء pyodbc إلى رسائل عربية قصيرة."""
    if isinstance(exc, (DatabaseError, ValueError)):
        return str(exc)
    if isinstance(exc, pyodbc.Error):
        text = " ".join(str(part) for part in exc.args)
        rules = (
            ("18456", "فشل تسجيل الدخول: تأكد من اسم المستخدم وكلمة المرور."),
            ("4060", "تعذّر فتح قاعدة البيانات: تأكد من اسم قاعدة البيانات ومن صلاحياتك."),
            ("53", "تعذّر الوصول إلى السيرفر: تأكد من اسم السيرفر وأن خدمة SQL Server تعمل."),
            ("2601", "قيمة مكررة: تأكد من أن الاسم أو الباركود غير مستخدم من قبل."),
            ("2627", "قيمة مكررة: تأكد من أن الاسم أو الباركود غير مستخدم من قبل."),
            ("547", "لا يمكن تنفيذ العملية لأن السجل مرتبط بسجلات أخرى."),
            ("2628", "القيمة المدخلة أطول من الحد المسموح به لحقل واحد أو أكثر."),
        )
        for code, message in rules:
            if code in text:
                return message
        return f"تعذّر تنفيذ العملية على قاعدة البيانات:\n{text[:500]}"
    return f"حدث خطأ غير متوقع:\n{exc}"


def split_go_batches(script: str) -> list[str]:
    """تقسيم سيناريو SSMS إلى دفعات عند أسطر GO."""
    batches: list[str] = []
    current: list[str] = []
    for line in script.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
        else:
            current.append(line)
    tail = "\n".join(current).strip()
    if tail:
        batches.append(tail)
    return batches


def initialize_database(config: Mapping[str, Any], password: str | None = None) -> None:
    """تهيئة قاعدة البيانات بتشغيل sql/SupermarketDB.sql من اتصال بـ master.

    تحذير: السيناريو يسقط الجداول الخمسة ويعيد إنشائها، أي أن البيانات القديمة
    ستُحذف. يجب التنبيه على ذلك في واجهة المستخدم قبل الاستدعاء.
    """
    driver = find_driver()
    master_config = dict(config)
    master_config["database"] = "master"
    db = Database(master_config, password)
    db.connect()
    try:
        db.connection.autocommit = True
        for batch in split_go_batches(read_schema_script()):
            db.execute(batch)
    finally:
        db.close()


def missing_tables(db: "Database") -> list[str]:
    rows = db.fetchall(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo'"
    )
    existing = {str(row["TABLE_NAME"]) for row in rows}
    return [name for name in REQUIRED_TABLES if name not in existing]


def test_connection(config: Mapping[str, Any], password: str | None = None) -> list[str]:
    """فحص الاتصال وإرجاع قائمة الجداول المفقودة."""
    db = Database(config, password)
    db.connect()
    try:
        db.scalar("SELECT 1")
        return missing_tables(db)
    finally:
        db.close()


class Database:
    """غلاف صغير حول اتصال pyodbc مع دعم المعاملات (transactions)."""

    def __init__(self, config: Mapping[str, Any], password: str | None = None) -> None:
        self.config = dict(config)
        self.password = password
        self.connection: pyodbc.Connection | None = None
        self._in_transaction = False

    def connect(self) -> "Database":
        connection_string = build_connection_string(self.config, password=self.password)
        self.connection = pyodbc.connect(connection_string, timeout=10)
        self.connection.autocommit = False
        return self

    def close(self) -> None:
        if self.connection is not None:
            try:
                self.connection.close()
            finally:
                self.connection = None

    def _cursor(self) -> pyodbc.Cursor:
        if self.connection is None:
            raise DatabaseError("لا يوجد اتصال بقاعدة البيانات. أعد الاتصال أولًا.")
        return self.connection.cursor()

    @contextmanager
    def transaction(self) -> Iterator["Database"]:
        if self._in_transaction:
            raise DatabaseError("لا يمكن بدء معاملة داخل معاملة أخرى.")
        self._in_transaction = True
        try:
            yield self
            if self.connection is not None and not self.connection.autocommit:
                self.connection.commit()
        except Exception:
            if self.connection is not None and not self.connection.autocommit:
                self.connection.rollback()
            raise
        finally:
            self._in_transaction = False

    def _finish_write(self) -> None:
        if (
            self.connection is not None
            and not self._in_transaction
            and not self.connection.autocommit
        ):
            self.connection.commit()

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        cursor = self._cursor()
        try:
            cursor.execute(sql, params)
            if not cursor.description:
                return []
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        cursor = self._cursor()
        try:
            cursor.execute(sql, params)
            if not cursor.description:
                return None
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row is not None else None
        finally:
            cursor.close()

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any | None:
        cursor = self._cursor()
        try:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            value = row[0] if row is not None else None
        finally:
            cursor.close()
        self._finish_write()
        return value

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        cursor = self._cursor()
        try:
            cursor.execute(sql, params)
            rowcount = int(cursor.rowcount)
        finally:
            cursor.close()
        self._finish_write()
        return rowcount
