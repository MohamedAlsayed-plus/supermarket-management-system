"""عمليات CRUD والتقارير على جداول SupermarketDB v2.

كل عملية متعددة الخطوات تتم داخل معاملة واحدة، وتُسجَّل حركة مخزون
مقابلة حتى يبقى سجل حركات المخزون متطابقًا مع رصيد المنتجات.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from app import db as db_module
from app.security import hash_password, verify_password

PAYMENT_METHODS = ("cash", "card", "credit")
MOVEMENT_TYPES = ("purchase", "sale", "return", "adjustment")


# ---------------------------------------------------------------------------
# المستخدمون
# ---------------------------------------------------------------------------

def list_users(db: db_module.Database) -> list[dict[str, Any]]:
    return db.fetchall(
        "SELECT UserID, UserName, FullName, Role, IsActive "
        "FROM dbo.Users ORDER BY UserID"
    )


def get_user(db: db_module.Database, user_id: int) -> dict[str, Any] | None:
    return db.fetchone(
        "SELECT UserID, UserName, FullName, Role, IsActive FROM dbo.Users WHERE UserID = ?",
        (user_id,),
    )


def authenticate(
    db: db_module.Database, username: str, password: str
) -> dict[str, Any] | None:
    row = db.fetchone(
        "SELECT UserID, UserName, FullName, Role, PasswordHash, IsActive "
        "FROM dbo.Users WHERE UserName = ?",
        (username.strip(),),
    )
    if row is None or not row["IsActive"]:
        return None
    if not verify_password(password, str(row["PasswordHash"])):
        return None
    return {key: value for key, value in row.items() if key != "PasswordHash"}


def add_user(
    db: db_module.Database,
    username: str,
    full_name: str,
    password: str,
    role: str,
    is_active: bool = True,
) -> int:
    username = str(username).strip()
    full_name = str(full_name).strip()
    if not username or not full_name:
        raise ValueError("اسم المستخدم والاسم الكامل مطلوبان.")
    if not password:
        raise ValueError("كلمة المرور مطلوبة.")
    if role not in ("admin", "cashier"):
        raise ValueError("الصلاحية غير صالحة.")
    return int(
        db.scalar(
            "INSERT INTO dbo.Users (UserName, FullName, PasswordHash, Role, IsActive) "
            "OUTPUT INSERTED.UserID VALUES (?, ?, ?, ?, ?)",
            (username, full_name, hash_password(password), role, int(bool(is_active))),
        )
    )


def update_user(
    db: db_module.Database,
    user_id: int,
    full_name: str,
    role: str,
    is_active: bool,
    new_password: str = "",
) -> None:
    full_name = str(full_name).strip()
    if not full_name:
        raise ValueError("الاسم الكامل مطلوب.")
    if role not in ("admin", "cashier"):
        raise ValueError("الصلاحية غير صالحة.")
    columns = "FullName = ?, Role = ?, IsActive = ?"
    params: list[Any] = [full_name, role, int(bool(is_active))]
    if new_password:
        columns += ", PasswordHash = ?"
        params.append(hash_password(new_password))
    params.append(user_id)
    db.execute(f"UPDATE dbo.Users SET {columns} WHERE UserID = ?", tuple(params))


def delete_user(db: db_module.Database, user_id: int) -> None:
    used = int(
        db.scalar(
            "SELECT (SELECT COUNT(*) FROM dbo.Sales WHERE UserID = ?) + "
            "(SELECT COUNT(*) FROM dbo.Purchases WHERE UserID = ?) + "
            "(SELECT COUNT(*) FROM dbo.SalesReturns WHERE UserID = ?) + "
            "(SELECT COUNT(*) FROM dbo.StockMovements WHERE UserID = ?)",
            (user_id, user_id, user_id, user_id),
        )
        or 0
    )
    if used:
        raise ValueError("لا يمكن حذف هذا المستخدم لأنه مرتبط بعمليات مسجلة.")
    db.execute("DELETE FROM dbo.Users WHERE UserID = ?", (user_id,))


# ---------------------------------------------------------------------------
# الأصناف والموردون
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
        "UPDATE dbo.Categories SET CategoryName = ?, UpdatedAt = SYSDATETIME() "
        "WHERE CategoryID = ?",
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


def list_suppliers(db: db_module.Database) -> list[dict[str, Any]]:
    return db.fetchall(
        "SELECT SupplierID, SupplierName, ISNULL(Phone, N'') AS Phone, "
        "ISNULL(Address, N'') AS Address FROM dbo.Suppliers ORDER BY SupplierName"
    )


def get_supplier(db: db_module.Database, supplier_id: int) -> dict[str, Any] | None:
    return db.fetchone(
        "SELECT SupplierID, SupplierName, ISNULL(Phone, N'') AS Phone, "
        "ISNULL(Address, N'') AS Address FROM dbo.Suppliers WHERE SupplierID = ?",
        (supplier_id,),
    )


def add_supplier(db: db_module.Database, name: str, phone: str, address: str) -> int:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم المورد مطلوب.")
    return int(
        db.scalar(
            "INSERT INTO dbo.Suppliers (SupplierName, Phone, Address) "
            "OUTPUT INSERTED.SupplierID VALUES (?, ?, ?)",
            (name, str(phone).strip() or None, str(address).strip() or None),
        )
    )


def update_supplier(
    db: db_module.Database, supplier_id: int, name: str, phone: str, address: str
) -> None:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم المورد مطلوب.")
    db.execute(
        "UPDATE dbo.Suppliers SET SupplierName = ?, Phone = ?, Address = ?, "
        "UpdatedAt = SYSDATETIME() WHERE SupplierID = ?",
        (name, str(phone).strip() or None, str(address).strip() or None, supplier_id),
    )


def delete_supplier(db: db_module.Database, supplier_id: int) -> None:
    count = int(
        db.scalar("SELECT COUNT(*) FROM dbo.Purchases WHERE SupplierID = ?", (supplier_id,))
        or 0
    )
    if count:
        raise ValueError(f"لا يمكن حذف هذا المورد لأنه مرتبط بـ {count} فاتورة شراء.")
    db.execute("DELETE FROM dbo.Suppliers WHERE SupplierID = ?", (supplier_id,))


# ---------------------------------------------------------------------------
# المنتجات والمخزون
# ---------------------------------------------------------------------------

def list_products(db: db_module.Database, search: str = "") -> list[dict[str, Any]]:
    sql = """
        SELECT p.ProductID, p.ProductName, p.CategoryID,
               ISNULL(c.CategoryName, N'') AS CategoryName,
               p.Price, p.CostPrice, p.Quantity, p.MinQuantity,
               ISNULL(p.Barcode, N'') AS Barcode
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
        "SELECT ProductID, ProductName, CategoryID, Price, CostPrice, Quantity, "
        "MinQuantity, Barcode FROM dbo.Products WHERE ProductID = ?",
        (product_id,),
    )


def get_product_by_barcode(db: db_module.Database, barcode: str) -> dict[str, Any] | None:
    return db.fetchone(
        "SELECT ProductID, ProductName, Price, CostPrice, Quantity, MinQuantity, Barcode "
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


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field} غير صالح.") from None
    if result < 0:
        raise ValueError(f"{field} لا يمكن أن يكون سالبًا.")
    return result


def _nonnegative_int(value: Any, field: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} غير صالحة.") from None
    if result < 0:
        raise ValueError(f"{field} لا يمكن أن تكون سالبة.")
    return result


def add_product(
    db: db_module.Database,
    name: str,
    category_id: int | None,
    price: Any,
    cost_price: Any,
    quantity: Any,
    min_quantity: Any,
    barcode: str,
) -> int:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم المنتج مطلوب.")
    price_value = _decimal(price, "السعر")
    cost_value = _decimal(cost_price, "سعر التكلفة")
    quantity_value = _nonnegative_int(quantity, "الكمية")
    min_value = _nonnegative_int(min_quantity, "حد إعادة الطلب")
    barcode_value = str(barcode).strip()
    if _barcode_taken(db, barcode_value):
        raise ValueError("هذا الباركود مستخدم لمنتج آخر.")
    return int(
        db.scalar(
            "INSERT INTO dbo.Products "
            "(ProductName, CategoryID, Price, CostPrice, Quantity, MinQuantity, Barcode) "
            "OUTPUT INSERTED.ProductID VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                category_id,
                price_value,
                cost_value,
                quantity_value,
                min_value,
                barcode_value or None,
            ),
        )
    )


def update_product(
    db: db_module.Database,
    product_id: int,
    name: str,
    category_id: int | None,
    price: Any,
    cost_price: Any,
    quantity: Any,
    min_quantity: Any,
    barcode: str,
) -> None:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم المنتج مطلوب.")
    price_value = _decimal(price, "السعر")
    cost_value = _decimal(cost_price, "سعر التكلفة")
    quantity_value = _nonnegative_int(quantity, "الكمية")
    min_value = _nonnegative_int(min_quantity, "حد إعادة الطلب")
    barcode_value = str(barcode).strip()
    if _barcode_taken(db, barcode_value, product_id):
        raise ValueError("هذا الباركود مستخدم لمنتج آخر.")
    db.execute(
        "UPDATE dbo.Products SET ProductName = ?, CategoryID = ?, Price = ?, "
        "CostPrice = ?, Quantity = ?, MinQuantity = ?, Barcode = ?, "
        "UpdatedAt = SYSDATETIME() WHERE ProductID = ?",
        (
            name,
            category_id,
            price_value,
            cost_value,
            quantity_value,
            min_value,
            barcode_value or None,
            product_id,
        ),
    )


def delete_product(db: db_module.Database, product_id: int) -> None:
    count = int(
        db.scalar(
            "SELECT (SELECT COUNT(*) FROM dbo.SaleDetails WHERE ProductID = ?) + "
            "(SELECT COUNT(*) FROM dbo.PurchaseDetails WHERE ProductID = ?) + "
            "(SELECT COUNT(*) FROM dbo.StockMovements WHERE ProductID = ?)",
            (product_id, product_id, product_id),
        )
        or 0
    )
    if count:
        raise ValueError("لا يمكن حذف هذا المنتج لأنه مرتبط بعمليات مسجلة.")
    db.execute("DELETE FROM dbo.Products WHERE ProductID = ?", (product_id,))


def record_movement(
    db: db_module.Database,
    product_id: int,
    movement_type: str,
    quantity: int,
    balance_after: int,
    reference_id: int | None,
    user_id: int | None,
    notes: str = "",
) -> None:
    if movement_type not in MOVEMENT_TYPES:
        raise ValueError("نوع حركة المخزون غير صالح.")
    db.execute(
        "INSERT INTO dbo.StockMovements "
        "(ProductID, MovementType, Quantity, BalanceAfter, ReferenceID, UserID, Notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            product_id,
            movement_type,
            quantity,
            balance_after,
            reference_id,
            user_id,
            str(notes).strip() or None,
        ),
    )


def list_movements(
    db: db_module.Database,
    product_id: int | None = None,
    movement_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT m.MovementID, m.MovementDate, p.ProductName, m.MovementType,
               m.Quantity, m.BalanceAfter, m.ReferenceID,
               ISNULL(u.FullName, N'') AS UserName, ISNULL(m.Notes, N'') AS Notes
        FROM dbo.StockMovements AS m
        JOIN dbo.Products AS p ON p.ProductID = m.ProductID
        LEFT JOIN dbo.Users AS u ON u.UserID = m.UserID
    """
    conditions: list[str] = []
    params: list[Any] = []
    if product_id:
        conditions.append("m.ProductID = ?")
        params.append(product_id)
    if movement_type:
        conditions.append("m.MovementType = ?")
        params.append(movement_type)
    if date_from is not None:
        conditions.append("CAST(m.MovementDate AS DATE) >= ?")
        params.append(date_from.isoformat())
    if date_to is not None:
        conditions.append("CAST(m.MovementDate AS DATE) <= ?")
        params.append(date_to.isoformat())
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY m.MovementID DESC"
    return db.fetchall(sql, tuple(params))


# ---------------------------------------------------------------------------
# العملاء
# ---------------------------------------------------------------------------

def list_customers(db: db_module.Database) -> list[dict[str, Any]]:
    return db.fetchall(
        "SELECT CustomerID, CustomerName, ISNULL(Phone, N'') AS Phone, Balance "
        "FROM dbo.Customers ORDER BY CustomerID"
    )


def get_customer(db: db_module.Database, customer_id: int) -> dict[str, Any] | None:
    return db.fetchone(
        "SELECT CustomerID, CustomerName, ISNULL(Phone, N'') AS Phone, Balance "
        "FROM dbo.Customers WHERE CustomerID = ?",
        (customer_id,),
    )


def add_customer(db: db_module.Database, name: str, phone: str) -> int:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم العميل مطلوب.")
    return int(
        db.scalar(
            "INSERT INTO dbo.Customers (CustomerName, Phone) OUTPUT INSERTED.CustomerID "
            "VALUES (?, ?)",
            (name, str(phone).strip() or None),
        )
    )


def update_customer(db: db_module.Database, customer_id: int, name: str, phone: str) -> None:
    name = str(name).strip()
    if not name:
        raise ValueError("اسم العميل مطلوب.")
    db.execute(
        "UPDATE dbo.Customers SET CustomerName = ?, Phone = ?, "
        "UpdatedAt = SYSDATETIME() WHERE CustomerID = ?",
        (name, str(phone).strip() or None, customer_id),
    )


def pay_balance(db: db_module.Database, customer_id: int, amount: Any) -> None:
    value = _decimal(amount, "المبلغ")
    if value <= 0:
        raise ValueError("المبلغ يجب أن يكون أكبر من صفر.")
    current = _decimal(db.scalar("SELECT Balance FROM dbo.Customers WHERE CustomerID = ?", (customer_id,)) or 0, "الرصيد")
    if value > current:
        raise ValueError("المبلغ أكبر من رصيد العميل.")
    db.execute(
        "UPDATE dbo.Customers SET Balance = Balance - ?, UpdatedAt = SYSDATETIME() "
        "WHERE CustomerID = ?",
        (value, customer_id),
    )


def delete_customer(db: db_module.Database, customer_id: int) -> None:
    count = int(
        db.scalar("SELECT COUNT(*) FROM dbo.Sales WHERE CustomerID = ?", (customer_id,))
        or 0
    )
    if count:
        raise ValueError(f"لا يمكن حذف هذا العميل لأنه مرتبط بـ {count} فاتورة.")
    balance = _decimal(db.scalar("SELECT Balance FROM dbo.Customers WHERE CustomerID = ?", (customer_id,)) or 0, "الرصيد")
    if balance > 0:
        raise ValueError("لا يمكن حذف عميل له رصيد مستحق. سدّد الرصيد أولًا.")
    db.execute("DELETE FROM dbo.Customers WHERE CustomerID = ?", (customer_id,))


# ---------------------------------------------------------------------------
# المبيعات
# ---------------------------------------------------------------------------

SALES_SELECT = """
    SELECT s.SaleID, s.SaleDate, s.PaymentMethod,
           ISNULL(c.CustomerName, N'') AS CustomerName,
           ISNULL(u.FullName, N'') AS UserName,
           ISNULL((SELECT SUM(sd.QuantitySold * sd.UnitPrice)
                   FROM dbo.SaleDetails AS sd WHERE sd.SaleID = s.SaleID), 0) AS Total
    FROM dbo.Sales AS s
    LEFT JOIN dbo.Customers AS c ON c.CustomerID = s.CustomerID
    LEFT JOIN dbo.Users AS u ON u.UserID = s.UserID
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


def get_sale(db: db_module.Database, sale_id: int) -> dict[str, Any] | None:
    return db.fetchone(SALES_SELECT + " WHERE s.SaleID = ?", (sale_id,))


def get_sale_details(db: db_module.Database, sale_id: int) -> list[dict[str, Any]]:
    return db.fetchall(
        """
        SELECT sd.SaleDetailID, sd.ProductID, p.ProductName,
               sd.QuantitySold, sd.UnitPrice,
               CAST(sd.QuantitySold * sd.UnitPrice AS DECIMAL(12,2)) AS LineTotal,
               ISNULL((SELECT SUM(rd.QuantityReturned) FROM dbo.ReturnDetails AS rd
                       WHERE rd.SaleDetailID = sd.SaleDetailID), 0) AS ReturnedQty
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
    payment_method: str,
    user_id: int | None,
    items: Sequence[Mapping[str, Any]],
) -> int:
    if payment_method not in PAYMENT_METHODS:
        raise ValueError("طريقة الدفع غير صالحة.")
    if not items:
        raise ValueError("أضف منتجًا واحدًا على الأقل إلى الفاتورة.")

    aggregated: dict[int, dict[str, Any]] = {}
    normalized: list[tuple[int, int, Decimal]] = []
    for item in items:
        product_id = int(item["product_id"])
        quantity = int(item["quantity"])
        unit_price = _decimal(item["unit_price"], "سعر الوحدة")
        if quantity <= 0:
            raise ValueError("كمية البيع يجب أن تكون أكبر من صفر.")
        entry = aggregated.setdefault(product_id, {"quantity": 0, "name": ""})
        entry["quantity"] += quantity
        normalized.append((product_id, quantity, unit_price))

    with db.transaction():
        total = Decimal("0")
        for product_id, info in aggregated.items():
            row = db.fetchone(
                "SELECT ProductName, Quantity FROM dbo.Products WITH (UPDLOCK) "
                "WHERE ProductID = ?",
                (product_id,),
            )
            if row is None:
                raise ValueError(f"المنتج رقم {product_id} غير موجود.")
            info["name"] = str(row["ProductName"])
            info["balance"] = int(row["Quantity"])
            if info["quantity"] > info["balance"]:
                raise ValueError(
                    f"الكمية المتوفرة من «{info['name']}» هي {info['balance']} فقط."
                )
        for product_id, quantity, unit_price in normalized:
            total += unit_price * quantity

        sale_id = int(
            db.scalar(
                "INSERT INTO dbo.Sales (CustomerID, PaymentMethod, UserID) "
                "OUTPUT INSERTED.SaleID VALUES (?, ?, ?)",
                (customer_id, payment_method, user_id),
            )
        )
        for product_id, quantity, unit_price in normalized:
            db.execute(
                "INSERT INTO dbo.SaleDetails (SaleID, ProductID, QuantitySold, UnitPrice) "
                "VALUES (?, ?, ?, ?)",
                (sale_id, product_id, quantity, unit_price),
            )
        for product_id, info in aggregated.items():
            balance = info["balance"] - info["quantity"]
            db.execute(
                "UPDATE dbo.Products SET Quantity = ?, UpdatedAt = SYSDATETIME() "
                "WHERE ProductID = ?",
                (balance, product_id),
            )
            record_movement(
                db, product_id, "sale", -info["quantity"], balance,
                sale_id, user_id, f"فاتورة رقم {sale_id}",
            )
        if payment_method == "credit" and customer_id:
            db.execute(
                "UPDATE dbo.Customers SET Balance = Balance + ?, "
                "UpdatedAt = SYSDATETIME() WHERE CustomerID = ?",
                (total, customer_id),
            )
    return sale_id


def delete_sale(db: db_module.Database, sale_id: int) -> None:
    sale = get_sale(db, sale_id)
    if sale is None:
        raise ValueError("الفاتورة غير موجودة.")
    returned = int(
        db.scalar("SELECT COUNT(*) FROM dbo.SalesReturns WHERE SaleID = ?", (sale_id,)) or 0
    )
    if returned:
        raise ValueError(
            "لا يمكن حذف فاتورة لها مرتجعات. إلغِ المرتجعات أولًا من تبويب المرتجعات."
        )
    details = get_sale_details(db, sale_id)
    total = _decimal(sale["Total"], "الإجمالي")
    with db.transaction():
        for line in details:
            product_id = int(line["ProductID"])
            quantity = int(line["QuantitySold"])
            balance = int(
                db.scalar("SELECT Quantity FROM dbo.Products WHERE ProductID = ?", (product_id,))
                or 0
            ) + quantity
            db.execute(
                "UPDATE dbo.Products SET Quantity = ?, UpdatedAt = SYSDATETIME() "
                "WHERE ProductID = ?",
                (balance, product_id),
            )
            record_movement(
                db, product_id, "adjustment", quantity, balance,
                sale_id, None, f"إلغاء فاتورة رقم {sale_id}",
            )
        db.execute("DELETE FROM dbo.SaleDetails WHERE SaleID = ?", (sale_id,))
        db.execute("DELETE FROM dbo.Sales WHERE SaleID = ?", (sale_id,))
        if str(sale["PaymentMethod"]) == "credit" and sale["CustomerID"]:
            db.execute(
                "UPDATE dbo.Customers SET Balance = "
                "CASE WHEN Balance - ? >= 0 THEN Balance - ? ELSE 0 END, "
                "UpdatedAt = SYSDATETIME() WHERE CustomerID = ?",
                (total, total, sale["CustomerID"]),
            )


# ---------------------------------------------------------------------------
# المشتريات
# ---------------------------------------------------------------------------

def list_purchases(db: db_module.Database) -> list[dict[str, Any]]:
    return db.fetchall(
        """
        SELECT p.PurchaseID, p.PurchaseDate,
               ISNULL(s.SupplierName, N'') AS SupplierName,
               ISNULL(u.FullName, N'') AS UserName,
               ISNULL(SUM(pd.QuantityPurchased * pd.UnitCost), 0) AS Total
        FROM dbo.Purchases AS p
        LEFT JOIN dbo.Suppliers AS s ON s.SupplierID = p.SupplierID
        LEFT JOIN dbo.Users AS u ON u.UserID = p.UserID
        LEFT JOIN dbo.PurchaseDetails AS pd ON pd.PurchaseID = p.PurchaseID
        GROUP BY p.PurchaseID, p.PurchaseDate, s.SupplierName, u.FullName
        ORDER BY p.PurchaseID DESC
        """
    )


def get_purchase_details(db: db_module.Database, purchase_id: int) -> list[dict[str, Any]]:
    return db.fetchall(
        """
        SELECT pd.PurchaseDetailID, pd.ProductID, p.ProductName,
               pd.QuantityPurchased, pd.UnitCost,
               CAST(pd.QuantityPurchased * pd.UnitCost AS DECIMAL(12,2)) AS LineTotal
        FROM dbo.PurchaseDetails AS pd
        JOIN dbo.Products AS p ON p.ProductID = pd.ProductID
        WHERE pd.PurchaseID = ? ORDER BY pd.PurchaseDetailID
        """,
        (purchase_id,),
    )


def create_purchase(
    db: db_module.Database,
    supplier_id: int | None,
    user_id: int | None,
    notes: str,
    items: Sequence[Mapping[str, Any]],
) -> int:
    if not items:
        raise ValueError("أضف منتجًا واحدًا على الأقل إلى فاتورة الشراء.")
    normalized: list[tuple[int, int, Decimal]] = []
    for item in items:
        quantity = _nonnegative_int(item["quantity"], "الكمية")
        if quantity <= 0:
            raise ValueError("كمية الشراء يجب أن تكون أكبر من صفر.")
        normalized.append(
            (
                int(item["product_id"]),
                quantity,
                _decimal(item["unit_cost"], "سعر التكلفة"),
            )
        )
    with db.transaction():
        purchase_id = int(
            db.scalar(
                "INSERT INTO dbo.Purchases (SupplierID, UserID, Notes) "
                "OUTPUT INSERTED.PurchaseID VALUES (?, ?, ?)",
                (supplier_id, user_id, str(notes).strip() or None),
            )
        )
        for product_id, quantity, unit_cost in normalized:
            db.execute(
                "INSERT INTO dbo.PurchaseDetails "
                "(PurchaseID, ProductID, QuantityPurchased, UnitCost) VALUES (?, ?, ?, ?)",
                (purchase_id, product_id, quantity, unit_cost),
            )
            balance = int(
                db.scalar("SELECT Quantity FROM dbo.Products WHERE ProductID = ?", (product_id,))
                or 0
            ) + quantity
            db.execute(
                "UPDATE dbo.Products SET Quantity = ?, CostPrice = ?, "
                "UpdatedAt = SYSDATETIME() WHERE ProductID = ?",
                (balance, unit_cost, product_id),
            )
            record_movement(
                db, product_id, "purchase", quantity, balance,
                purchase_id, user_id, f"شراء رقم {purchase_id}",
            )
    return purchase_id


def delete_purchase(db: db_module.Database, purchase_id: int) -> None:
    details = get_purchase_details(db, purchase_id)
    for line in details:
        product_id = int(line["ProductID"])
        quantity = int(line["QuantityPurchased"])
        available = int(
            db.scalar("SELECT Quantity FROM dbo.Products WHERE ProductID = ?", (product_id,))
            or 0
        )
        if available < quantity:
            raise ValueError(
                f"لا يمكن إلغاء الشراء لأن الكمية المتوفرة من «{line['ProductName']}» "
                f"أقل من الكمية المشتراة ({quantity})."
            )
    with db.transaction():
        for line in details:
            product_id = int(line["ProductID"])
            quantity = int(line["QuantityPurchased"])
            balance = int(
                db.scalar("SELECT Quantity FROM dbo.Products WHERE ProductID = ?", (product_id,))
                or 0
            ) - quantity
            db.execute(
                "UPDATE dbo.Products SET Quantity = ?, UpdatedAt = SYSDATETIME() "
                "WHERE ProductID = ?",
                (balance, product_id),
            )
            record_movement(
                db, product_id, "adjustment", -quantity, balance,
                purchase_id, None, f"إلغاء شراء رقم {purchase_id}",
            )
        db.execute("DELETE FROM dbo.PurchaseDetails WHERE PurchaseID = ?", (purchase_id,))
        db.execute("DELETE FROM dbo.Purchases WHERE PurchaseID = ?", (purchase_id,))


# ---------------------------------------------------------------------------
# المرتجعات
# ---------------------------------------------------------------------------

def list_returns(db: db_module.Database) -> list[dict[str, Any]]:
    return db.fetchall(
        """
        SELECT r.ReturnID, r.ReturnDate, r.SaleID, r.Reason,
               ISNULL(u.FullName, N'') AS UserName,
               ISNULL(SUM(rd.QuantityReturned * sd.UnitPrice), 0) AS Total
        FROM dbo.SalesReturns AS r
        LEFT JOIN dbo.Users AS u ON u.UserID = r.UserID
        LEFT JOIN dbo.ReturnDetails AS rd ON rd.ReturnID = r.ReturnID
        LEFT JOIN dbo.SaleDetails AS sd ON sd.SaleDetailID = rd.SaleDetailID
        GROUP BY r.ReturnID, r.ReturnDate, r.SaleID, r.Reason, u.FullName
        ORDER BY r.ReturnID DESC
        """
    )


def get_return_details(db: db_module.Database, return_id: int) -> list[dict[str, Any]]:
    return db.fetchall(
        """
        SELECT rd.ReturnDetailID, p.ProductName, rd.QuantityReturned,
               sd.UnitPrice,
               CAST(rd.QuantityReturned * sd.UnitPrice AS DECIMAL(12,2)) AS LineTotal
        FROM dbo.ReturnDetails AS rd
        JOIN dbo.SaleDetails AS sd ON sd.SaleDetailID = rd.SaleDetailID
        JOIN dbo.Products AS p ON p.ProductID = sd.ProductID
        WHERE rd.ReturnID = ? ORDER BY rd.ReturnDetailID
        """,
        (return_id,),
    )


def create_return(
    db: db_module.Database,
    sale_id: int,
    user_id: int | None,
    reason: str,
    lines: Sequence[Mapping[str, Any]],
) -> int:
    if not lines:
        raise ValueError("أضف صنفًا واحدًا على الأقل إلى المرتجع.")
    sale = get_sale(db, sale_id)
    if sale is None:
        raise ValueError("الفاتورة غير موجودة.")
    with db.transaction():
        return_id = int(
            db.scalar(
                "INSERT INTO dbo.SalesReturns (SaleID, UserID, Reason) "
                "OUTPUT INSERTED.ReturnID VALUES (?, ?, ?)",
                (sale_id, user_id, str(reason).strip() or None),
            )
        )
        refund = Decimal("0")
        for line in lines:
            detail_id = int(line["sale_detail_id"])
            quantity = _nonnegative_int(line["quantity"], "الكمية")
            if quantity <= 0:
                raise ValueError("كمية الإرجاع يجب أن تكون أكبر من صفر.")
            row = db.fetchone(
                "SELECT sd.ProductID, sd.QuantitySold, sd.UnitPrice, "
                "ISNULL((SELECT SUM(QuantityReturned) FROM dbo.ReturnDetails "
                "WHERE SaleDetailID = sd.SaleDetailID), 0) AS ReturnedQty "
                "FROM dbo.SaleDetails AS sd WHERE sd.SaleDetailID = ?",
                (detail_id,),
            )
            if row is None:
                raise ValueError("سطر الفاتورة غير موجود.")
            remaining = int(row["QuantitySold"]) - int(row["ReturnedQty"])
            if quantity > remaining:
                raise ValueError(f"الكمية القابلة للإرجاع هي {remaining} فقط.")
            db.execute(
                "INSERT INTO dbo.ReturnDetails (ReturnID, SaleDetailID, QuantityReturned) "
                "VALUES (?, ?, ?)",
                (return_id, detail_id, quantity),
            )
            product_id = int(row["ProductID"])
            balance = int(
                db.scalar("SELECT Quantity FROM dbo.Products WHERE ProductID = ?", (product_id,))
                or 0
            ) + quantity
            db.execute(
                "UPDATE dbo.Products SET Quantity = ?, UpdatedAt = SYSDATETIME() "
                "WHERE ProductID = ?",
                (balance, product_id),
            )
            record_movement(
                db, product_id, "return", quantity, balance,
                return_id, user_id, f"مرتجع رقم {return_id}",
            )
            refund += _decimal(row["UnitPrice"], "السعر") * quantity
        if str(sale["PaymentMethod"]) == "credit" and sale["CustomerID"]:
            db.execute(
                "UPDATE dbo.Customers SET Balance = "
                "CASE WHEN Balance - ? >= 0 THEN Balance - ? ELSE 0 END, "
                "UpdatedAt = SYSDATETIME() WHERE CustomerID = ?",
                (refund, refund, sale["CustomerID"]),
            )
    return return_id


def delete_return(db: db_module.Database, return_id: int) -> None:
    details = db.fetchall(
        "SELECT rd.ReturnDetailID, sd.ProductID, rd.QuantityReturned, "
        "CAST(rd.QuantityReturned * sd.UnitPrice AS DECIMAL(12,2)) AS LineTotal "
        "FROM dbo.ReturnDetails AS rd JOIN dbo.SaleDetails AS sd "
        "ON sd.SaleDetailID = rd.SaleDetailID WHERE rd.ReturnID = ?",
        (return_id,),
    )
    if not details:
        raise ValueError("المرتجع غير موجود.")
    header = db.fetchone(
        "SELECT s.SaleID, s.PaymentMethod, s.CustomerID "
        "FROM dbo.SalesReturns AS r JOIN dbo.Sales AS s ON s.SaleID = r.SaleID "
        "WHERE r.ReturnID = ?",
        (return_id,),
    )
    refund = sum((_decimal(line["LineTotal"], "القيمة") for line in details), Decimal("0"))
    with db.transaction():
        for line in details:
            product_id = int(line["ProductID"])
            quantity = int(line["QuantityReturned"])
            balance = int(
                db.scalar("SELECT Quantity FROM dbo.Products WHERE ProductID = ?", (product_id,))
                or 0
            ) - quantity
            db.execute(
                "UPDATE dbo.Products SET Quantity = ?, UpdatedAt = SYSDATETIME() "
                "WHERE ProductID = ?",
                (balance, product_id),
            )
            record_movement(
                db, product_id, "adjustment", -quantity, balance,
                return_id, None, f"إلغاء مرتجع رقم {return_id}",
            )
        db.execute("DELETE FROM dbo.ReturnDetails WHERE ReturnID = ?", (return_id,))
        db.execute("DELETE FROM dbo.SalesReturns WHERE ReturnID = ?", (return_id,))
        if (
            header is not None
            and str(header["PaymentMethod"]) == "credit"
            and header["CustomerID"]
            and refund > 0
        ):
            db.execute(
                "UPDATE dbo.Customers SET Balance = Balance + ?, "
                "UpdatedAt = SYSDATETIME() WHERE CustomerID = ?",
                (refund, header["CustomerID"]),
            )


# ---------------------------------------------------------------------------
# التقارير واللوحة
# ---------------------------------------------------------------------------

def stock_report(db: db_module.Database, low_stock_only: bool = False) -> list[dict[str, Any]]:
    sql = """
        SELECT p.ProductID, p.ProductName,
               ISNULL(c.CategoryName, N'') AS CategoryName,
               p.Price, p.CostPrice, p.Quantity, p.MinQuantity,
               ISNULL(p.Barcode, N'') AS Barcode
        FROM dbo.Products AS p
        LEFT JOIN dbo.Categories AS c ON c.CategoryID = p.CategoryID
    """
    if low_stock_only:
        sql += " WHERE p.Quantity <= p.MinQuantity"
    sql += " ORDER BY p.Quantity, p.ProductID"
    return db.fetchall(sql)


def dashboard_numbers(db: db_module.Database) -> dict[str, Any]:
    row = db.fetchone(
        """
        SELECT
          (SELECT COUNT(*) FROM dbo.Products) AS Products,
          (SELECT COUNT(*) FROM dbo.Products WHERE Quantity <= MinQuantity) AS LowStock,
          (SELECT COUNT(*) FROM dbo.Customers) AS Customers,
          (SELECT COUNT(*) FROM dbo.Suppliers) AS Suppliers,
          (SELECT ISNULL(SUM(Total), 0) FROM (
              SELECT ISNULL(SUM(sd.QuantitySold * sd.UnitPrice), 0) AS Total
              FROM dbo.Sales AS s
              LEFT JOIN dbo.SaleDetails AS sd ON sd.SaleID = s.SaleID
              GROUP BY s.SaleID
           ) AS SalesTotals) AS Revenue,
          (SELECT ISNULL(SUM(sd.QuantitySold * sd.UnitPrice), 0)
              FROM dbo.Sales AS s
              JOIN dbo.SaleDetails AS sd ON sd.SaleID = s.SaleID
              WHERE CAST(s.SaleDate AS DATE) = CAST(SYSDATETIME() AS DATE)) AS TodayRevenue,
          (SELECT COUNT(*) FROM dbo.Sales
              WHERE CAST(SaleDate AS DATE) = CAST(SYSDATETIME() AS DATE)) AS TodaySales
        """
    )
    return dict(row or {})


def sales_by_day(db: db_module.Database, days: int = 7) -> list[dict[str, Any]]:
    rows = db.fetchall(
        """
        SELECT CAST(s.SaleDate AS DATE) AS SaleDay,
               ISNULL(SUM(sd.QuantitySold * sd.UnitPrice), 0) AS Total
        FROM dbo.Sales AS s
        LEFT JOIN dbo.SaleDetails AS sd ON sd.SaleID = s.SaleID
        GROUP BY CAST(s.SaleDate AS DATE)
        ORDER BY SaleDay DESC
        """
    )
    return list(reversed(rows[:days]))


def top_products(db: db_module.Database, limit: int = 5) -> list[dict[str, Any]]:
    rows = db.fetchall(
        """
        SELECT p.ProductName, SUM(sd.QuantitySold) AS QuantitySold,
               CAST(SUM(sd.QuantitySold * sd.UnitPrice) AS DECIMAL(12,2)) AS Revenue
        FROM dbo.SaleDetails AS sd
        JOIN dbo.Products AS p ON p.ProductID = sd.ProductID
        GROUP BY p.ProductID, p.ProductName
        ORDER BY QuantitySold DESC
        """
    )
    return rows[:limit]
