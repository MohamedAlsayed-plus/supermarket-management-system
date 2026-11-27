"""عمليات CRUD والتقارير على جداول SupermarketDB.

كل الدوال تستقبل كائن Database، ودوال الفاتورة تستخدم معاملة واحدة بحيث
لا تُحفظ الفاتورة إلا إذا نجح كل شيء (إدخال + تفاصيل + خصم المخزون).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from app import db as db_module


# ---------------------------------------------------------------------------
# الأصناف
# ---------------------------------------------------------------------------

def list_categories(db: db_module.Database) -> list[dict[str, Any]]:
    return db.fetchall(
        "SELECT CategoryID, CategoryName FROM dbo.Categories ORDER BY CategoryName"
    )


def get_category(db: db_module.Database, category_id: int) -> dict[str, Any] | None:
    return db.fetchone(
        "SELECT CategoryID, CategoryName FROM dbo.Categories WHERE CategoryID = ?",
        (category_id,),
    )


def add_category(db: db_module.Database, name: str) -> int:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم الصنف مطلوب.")
    return int(
        db.scalar(
            "INSERT INTO dbo.Categories (CategoryName) OUTPUT INSERTED.CategoryID VALUES (?)",
            (name,),
        )
    )


def update_category(db: db_module.Database, category_id: int, name: str) -> None:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم الصنف مطلوب.")
    db.execute(
        "UPDATE dbo.Categories SET CategoryName = ? WHERE CategoryID = ?",
        (name, category_id),
    )


def delete_category(db: db_module.Database, category_id: int) -> None:
    count = int(
        db.scalar("SELECT COUNT(*) FROM dbo.Products WHERE CategoryID = ?", (category_id,))
        or 0
    )
    if count:
        raise ValueError(
            f"لا يمكن حذف هذا الصنف لأنه مستخدم في {count} منتج. "
            "انقل المنتجات إلى صنف آخر أولًا."
        )
    db.execute("DELETE FROM dbo.Categories WHERE CategoryID = ?", (category_id,))


# ---------------------------------------------------------------------------
# المنتجات
# ---------------------------------------------------------------------------

def list_products(db: db_module.Database, search: str = "") -> list[dict[str, Any]]:
    sql = """
        SELECT p.ProductID, p.ProductName, p.CategoryID,
               ISNULL(c.CategoryName, N'') AS CategoryName,
               p.Price, p.Quantity, ISNULL(p.Barcode, N'') AS Barcode
        FROM dbo.Products AS p
        LEFT JOIN dbo.Categories AS c ON c.CategoryID = p.CategoryID
        WHERE ? = N''
           OR p.ProductName LIKE N'%' + ? + N'%'
           OR p.Barcode LIKE N'%' + ? + N'%'
           OR c.CategoryName LIKE N'%' + ? + N'%'
        ORDER BY p.ProductID
    """
    return db.fetchall(sql, (search, search, search, search))


def get_product(db: db_module.Database, product_id: int) -> dict[str, Any] | None:
    return db.fetchone(
        "SELECT ProductID, ProductName, CategoryID, Price, Quantity, Barcode "
        "FROM dbo.Products WHERE ProductID = ?",
        (product_id,),
    )


def get_product_by_barcode(db: db_module.Database, barcode: str) -> dict[str, Any] | None:
    return db.fetchone(
        "SELECT ProductID, ProductName, Price, Quantity, Barcode "
        "FROM dbo.Products WHERE Barcode = ?",
        (barcode.strip(),),
    )


def _barcode_taken(
    db: db_module.Database, barcode: str, exclude_id: int | None = None
) -> bool:
    if not barcode:
        return False
    count = int(
        db.scalar(
            "SELECT COUNT(*) FROM dbo.Products WHERE Barcode = ? AND ProductID <> ?",
            (barcode, exclude_id or 0),
        )
        or 0
    )
    return count > 0


def _normalize_product(
    name: str, price: Any, quantity: Any, barcode: str
) -> tuple[str, Decimal, int, str]:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم المنتج مطلوب.")
    try:
        price_value = Decimal(str(price))
    except (InvalidOperation, ValueError):
        raise ValueError("السعر غير صالح.") from None
    if price_value < 0:
        raise ValueError("لا يمكن أن يكون السعر سالبًا.")
    try:
        quantity_value = int(quantity)
    except (TypeError, ValueError):
        raise ValueError("الكمية غير صالحة.") from None
    if quantity_value < 0:
        raise ValueError("لا يمكن أن تكون الكمية سالبة.")
    return name, price_value, quantity_value, barcode.strip()


def add_product(
    db: db_module.Database,
    name: str,
    category_id: int | None,
    price: Any,
    quantity: Any,
    barcode: str,
) -> int:
    name, price_value, quantity_value, barcode_value = _normalize_product(
        name, price, quantity, barcode
    )
    if _barcode_taken(db, barcode_value):
        raise ValueError("هذا الباركود مستخدم لمنتج آخر.")
    return int(
        db.scalar(
            "INSERT INTO dbo.Products (ProductName, CategoryID, Price, Quantity, Barcode) "
            "OUTPUT INSERTED.ProductID VALUES (?, ?, ?, ?, ?)",
            (name, category_id, price_value, quantity_value, barcode_value or None),
        )
    )


def update_product(
    db: db_module.Database,
    product_id: int,
    name: str,
    category_id: int | None,
    price: Any,
    quantity: Any,
    barcode: str,
) -> None:
    name, price_value, quantity_value, barcode_value = _normalize_product(
        name, price, quantity, barcode
    )
    if _barcode_taken(db, barcode_value, product_id):
        raise ValueError("هذا الباركود مستخدم لمنتج آخر.")
    db.execute(
        "UPDATE dbo.Products SET ProductName = ?, CategoryID = ?, Price = ?, "
        "Quantity = ?, Barcode = ? WHERE ProductID = ?",
        (
            name,
            category_id,
            price_value,
            quantity_value,
            barcode_value or None,
            product_id,
        ),
    )


def delete_product(db: db_module.Database, product_id: int) -> None:
    count = int(
        db.scalar(
            "SELECT COUNT(*) FROM dbo.SaleDetails WHERE ProductID = ?", (product_id,)
        )
        or 0
    )
    if count:
        raise ValueError(
            f"لا يمكن حذف هذا المنتج لأنه موجود في {count} سطر مبيعات."
        )
    db.execute("DELETE FROM dbo.Products WHERE ProductID = ?", (product_id,))


# ---------------------------------------------------------------------------
# العملاء
# ---------------------------------------------------------------------------

def list_customers(db: db_module.Database) -> list[dict[str, Any]]:
    return db.fetchall(
        "SELECT CustomerID, CustomerName, ISNULL(Phone, N'') AS Phone "
        "FROM dbo.Customers ORDER BY CustomerID"
    )


def get_customer(db: db_module.Database, customer_id: int) -> dict[str, Any] | None:
    return db.fetchone(
        "SELECT CustomerID, CustomerName, ISNULL(Phone, N'') AS Phone "
        "FROM dbo.Customers WHERE CustomerID = ?",
        (customer_id,),
    )


def add_customer(db: db_module.Database, name: str, phone: str) -> int:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم العميل مطلوب.")
    phone = str(phone).strip()
    return int(
        db.scalar(
            "INSERT INTO dbo.Customers (CustomerName, Phone) OUTPUT INSERTED.CustomerID "
            "VALUES (?, ?)",
            (name, phone or None),
        )
    )


def update_customer(db: db_module.Database, customer_id: int, name: str, phone: str) -> None:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم العميل مطلوب.")
    phone = str(phone).strip()
    db.execute(
        "UPDATE dbo.Customers SET CustomerName = ?, Phone = ? WHERE CustomerID = ?",
        (name, phone or None, customer_id),
    )


def delete_customer(db: db_module.Database, customer_id: int) -> None:
    count = int(
        db.scalar("SELECT COUNT(*) FROM dbo.Sales WHERE CustomerID = ?", (customer_id,))
        or 0
    )
    if count:
        raise ValueError(
            f"لا يمكن حذف هذا العميل لأنه مرتبط بـ {count} فاتورة."
        )
    db.execute("DELETE FROM dbo.Customers WHERE CustomerID = ?", (customer_id,))


# ---------------------------------------------------------------------------
# المبيعات
# ---------------------------------------------------------------------------

SALES_SELECT = """
    SELECT s.SaleID, s.SaleDate,
           ISNULL(c.CustomerName, N'') AS CustomerName,
           ISNULL((SELECT SUM(sd.QuantitySold * sd.UnitPrice)
                   FROM dbo.SaleDetails AS sd WHERE sd.SaleID = s.SaleID), 0) AS Total
    FROM dbo.Sales AS s
    LEFT JOIN dbo.Customers AS c ON c.CustomerID = s.CustomerID
"""


def list_sales(
    db: db_module.Database,
    customer_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if customer_id:
        conditions.append("s.CustomerID = ?")
        params.append(customer_id)
    if date_from is not None:
        conditions.append("CAST(s.SaleDate AS DATE) >= ?")
        params.append(date_from.isoformat())
    if date_to is not None:
        conditions.append("CAST(s.SaleDate AS DATE) <= ?")
        params.append(date_to.isoformat())
    sql = SALES_SELECT
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY s.SaleID DESC"
    return db.fetchall(sql, tuple(params))


def get_sale_details(db: db_module.Database, sale_id: int) -> list[dict[str, Any]]:
    return db.fetchall(
        """
        SELECT sd.SaleDetailID, sd.ProductID, p.ProductName,
               sd.QuantitySold, sd.UnitPrice,
               CAST(sd.QuantitySold * sd.UnitPrice AS DECIMAL(12,2)) AS LineTotal
        FROM dbo.SaleDetails AS sd
        JOIN dbo.Products AS p ON p.ProductID = sd.ProductID
        WHERE sd.SaleID = ?
        ORDER BY sd.SaleDetailID
        """,
        (sale_id,),
    )


def create_sale(
    db: db_module.Database,
    customer_id: int | None,
    items: Sequence[Mapping[str, Any]],
) -> int:
    """إنشاء فاتورة كاملة في معاملة واحدة مع خصم الكميات من المخزون."""
    if not items:
        raise ValueError("أضف منتجًا واحدًا على الأقل إلى الفاتورة.")

    aggregated: dict[int, dict[str, Any]] = {}
    normalized: list[tuple[int, int, Decimal]] = []
    for item in items:
        product_id = int(item["product_id"])
        quantity = int(item["quantity"])
        try:
            unit_price = Decimal(str(item["unit_price"]))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("سعر الوحدة غير صالح.") from None
        if quantity <= 0:
            raise ValueError("كمية البيع يجب أن تكون أكبر من صفر.")
        if unit_price < 0:
            raise ValueError("سعر الوحدة لا يمكن أن يكون سالبًا.")
        entry = aggregated.setdefault(product_id, {"quantity": 0, "name": ""})
        entry["quantity"] += quantity
        normalized.append((product_id, quantity, unit_price))

    with db.transaction():
        for product_id, info in aggregated.items():
            row = db.fetchone(
                "SELECT ProductName, Quantity FROM dbo.Products WITH (UPDLOCK) "
                "WHERE ProductID = ?",
                (product_id,),
            )
            if row is None:
                raise ValueError(f"المنتج رقم {product_id} غير موجود.")
            info["name"] = str(row["ProductName"])
            if info["quantity"] > int(row["Quantity"]):
                raise ValueError(
                    f"الكمية المتوفرة من «{info['name']}» هي {row['Quantity']} فقط."
                )

        sale_id = int(
            db.scalar(
                "INSERT INTO dbo.Sales (CustomerID) OUTPUT INSERTED.SaleID VALUES (?)",
                (customer_id,),
            )
        )
        for product_id, quantity, unit_price in normalized:
            db.execute(
                "INSERT INTO dbo.SaleDetails (SaleID, ProductID, QuantitySold, UnitPrice) "
                "VALUES (?, ?, ?, ?)",
                (sale_id, product_id, quantity, unit_price),
            )
        for product_id, info in aggregated.items():
            db.execute(
                "UPDATE dbo.Products SET Quantity = Quantity - ? WHERE ProductID = ?",
                (info["quantity"], product_id),
            )
    return sale_id


def delete_sale(db: db_module.Database, sale_id: int) -> None:
    """حذف فاتورة وإعادة الكميات إلى المخزون، في معاملة واحدة."""
    details = get_sale_details(db, sale_id)
    with db.transaction():
        db.execute("DELETE FROM dbo.SaleDetails WHERE SaleID = ?", (sale_id,))
        db.execute("DELETE FROM dbo.Sales WHERE SaleID = ?", (sale_id,))
        for line in details:
            db.execute(
                "UPDATE dbo.Products SET Quantity = Quantity + ? WHERE ProductID = ?",
                (int(line["QuantitySold"]), int(line["ProductID"])),
            )


# ---------------------------------------------------------------------------
# التقارير
# ---------------------------------------------------------------------------

def stock_report(
    db: db_module.Database, low_stock_only: bool = False, threshold: int = 10
) -> list[dict[str, Any]]:
    sql = """
        SELECT p.ProductID, p.ProductName,
               ISNULL(c.CategoryName, N'') AS CategoryName,
               p.Price, p.Quantity, ISNULL(p.Barcode, N'') AS Barcode
        FROM dbo.Products AS p
        LEFT JOIN dbo.Categories AS c ON c.CategoryID = p.CategoryID
    """
    params: tuple[Any, ...] = ()
    if low_stock_only:
        sql += " WHERE p.Quantity <= ?"
        params = (threshold,)
    sql += " ORDER BY p.Quantity, p.ProductID"
    return db.fetchall(sql, params)
