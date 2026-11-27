/* Supermarket Management System - schema v2
   SQL Server script: run this file in SSMS, or use the "تهيئة قاعدة البيانات"
   button in the app. WARNING: this drops and recreates all tables.
*/

IF DB_ID(N'SupermarketDB') IS NULL
BEGIN
    CREATE DATABASE SupermarketDB;
END;
GO

USE SupermarketDB;
GO

IF OBJECT_ID(N'dbo.StockMovements', N'U') IS NOT NULL DROP TABLE dbo.StockMovements;
IF OBJECT_ID(N'dbo.ReturnDetails', N'U') IS NOT NULL DROP TABLE dbo.ReturnDetails;
IF OBJECT_ID(N'dbo.SalesReturns', N'U') IS NOT NULL DROP TABLE dbo.SalesReturns;
IF OBJECT_ID(N'dbo.PurchaseDetails', N'U') IS NOT NULL DROP TABLE dbo.PurchaseDetails;
IF OBJECT_ID(N'dbo.Purchases', N'U') IS NOT NULL DROP TABLE dbo.Purchases;
IF OBJECT_ID(N'dbo.SaleDetails', N'U') IS NOT NULL DROP TABLE dbo.SaleDetails;
IF OBJECT_ID(N'dbo.Sales', N'U') IS NOT NULL DROP TABLE dbo.Sales;
IF OBJECT_ID(N'dbo.Customers', N'U') IS NOT NULL DROP TABLE dbo.Customers;
IF OBJECT_ID(N'dbo.Products', N'U') IS NOT NULL DROP TABLE dbo.Products;
IF OBJECT_ID(N'dbo.Categories', N'U') IS NOT NULL DROP TABLE dbo.Categories;
IF OBJECT_ID(N'dbo.Suppliers', N'U') IS NOT NULL DROP TABLE dbo.Suppliers;
IF OBJECT_ID(N'dbo.Users', N'U') IS NOT NULL DROP TABLE dbo.Users;
GO

CREATE TABLE dbo.Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    UserName NVARCHAR(100) NOT NULL UNIQUE,
    FullName NVARCHAR(150) NOT NULL,
    PasswordHash NVARCHAR(200) NOT NULL,
    Role NVARCHAR(20) NOT NULL DEFAULT N'cashier' CHECK (Role IN (N'admin', N'cashier')),
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
GO

CREATE TABLE dbo.Categories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(100) NOT NULL UNIQUE,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    UpdatedAt DATETIME2 NULL
);
GO

CREATE TABLE dbo.Suppliers (
    SupplierID INT IDENTITY(1,1) PRIMARY KEY,
    SupplierName NVARCHAR(150) NOT NULL UNIQUE,
    Phone NVARCHAR(30) NULL,
    Address NVARCHAR(300) NULL,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    UpdatedAt DATETIME2 NULL
);
GO

CREATE TABLE dbo.Products (
    ProductID INT IDENTITY(1,1) PRIMARY KEY,
    ProductName NVARCHAR(150) NOT NULL,
    CategoryID INT NULL,
    Price DECIMAL(10,2) NOT NULL CHECK (Price >= 0),
    CostPrice DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (CostPrice >= 0),
    Quantity INT NOT NULL DEFAULT 0 CHECK (Quantity >= 0),
    MinQuantity INT NOT NULL DEFAULT 10 CHECK (MinQuantity >= 0),
    Barcode NVARCHAR(50) NULL UNIQUE,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    UpdatedAt DATETIME2 NULL,
    CONSTRAINT FK_Products_Categories FOREIGN KEY (CategoryID)
        REFERENCES dbo.Categories(CategoryID)
);
GO

CREATE TABLE dbo.Customers (
    CustomerID INT IDENTITY(1,1) PRIMARY KEY,
    CustomerName NVARCHAR(150) NOT NULL,
    Phone NVARCHAR(30) NULL,
    Balance DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (Balance >= 0),
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    UpdatedAt DATETIME2 NULL
);
GO

CREATE TABLE dbo.Sales (
    SaleID INT IDENTITY(1,1) PRIMARY KEY,
    SaleDate DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CustomerID INT NULL,
    PaymentMethod NVARCHAR(20) NOT NULL DEFAULT N'cash'
        CHECK (PaymentMethod IN (N'cash', N'card', N'credit')),
    UserID INT NULL,
    UpdatedAt DATETIME2 NULL,
    CONSTRAINT FK_Sales_Customers FOREIGN KEY (CustomerID)
        REFERENCES dbo.Customers(CustomerID),
    CONSTRAINT FK_Sales_Users FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID)
);
GO

CREATE TABLE dbo.SaleDetails (
    SaleDetailID INT IDENTITY(1,1) PRIMARY KEY,
    SaleID INT NOT NULL,
    ProductID INT NOT NULL,
    QuantitySold INT NOT NULL CHECK (QuantitySold > 0),
    UnitPrice DECIMAL(10,2) NOT NULL CHECK (UnitPrice >= 0),
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_SaleDetails_Sales FOREIGN KEY (SaleID) REFERENCES dbo.Sales(SaleID),
    CONSTRAINT FK_SaleDetails_Products FOREIGN KEY (ProductID) REFERENCES dbo.Products(ProductID)
);
GO

CREATE TABLE dbo.Purchases (
    PurchaseID INT IDENTITY(1,1) PRIMARY KEY,
    PurchaseDate DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    SupplierID INT NULL,
    UserID INT NULL,
    Notes NVARCHAR(300) NULL,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_Purchases_Suppliers FOREIGN KEY (SupplierID)
        REFERENCES dbo.Suppliers(SupplierID),
    CONSTRAINT FK_Purchases_Users FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID)
);
GO

CREATE TABLE dbo.PurchaseDetails (
    PurchaseDetailID INT IDENTITY(1,1) PRIMARY KEY,
    PurchaseID INT NOT NULL,
    ProductID INT NOT NULL,
    QuantityPurchased INT NOT NULL CHECK (QuantityPurchased > 0),
    UnitCost DECIMAL(10,2) NOT NULL CHECK (UnitCost >= 0),
    CONSTRAINT FK_PurchaseDetails_Purchases FOREIGN KEY (PurchaseID)
        REFERENCES dbo.Purchases(PurchaseID),
    CONSTRAINT FK_PurchaseDetails_Products FOREIGN KEY (ProductID)
        REFERENCES dbo.Products(ProductID)
);
GO

CREATE TABLE dbo.SalesReturns (
    ReturnID INT IDENTITY(1,1) PRIMARY KEY,
    ReturnDate DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    SaleID INT NOT NULL,
    UserID INT NULL,
    Reason NVARCHAR(300) NULL,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_Returns_Sales FOREIGN KEY (SaleID) REFERENCES dbo.Sales(SaleID),
    CONSTRAINT FK_Returns_Users FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID)
);
GO

CREATE TABLE dbo.ReturnDetails (
    ReturnDetailID INT IDENTITY(1,1) PRIMARY KEY,
    ReturnID INT NOT NULL,
    SaleDetailID INT NOT NULL,
    QuantityReturned INT NOT NULL CHECK (QuantityReturned > 0),
    CONSTRAINT FK_ReturnDetails_Returns FOREIGN KEY (ReturnID)
        REFERENCES dbo.SalesReturns(ReturnID),
    CONSTRAINT FK_ReturnDetails_SaleDetails FOREIGN KEY (SaleDetailID)
        REFERENCES dbo.SaleDetails(SaleDetailID),
    CONSTRAINT UQ_ReturnDetails UNIQUE (ReturnID, SaleDetailID)
);
GO

CREATE TABLE dbo.StockMovements (
    MovementID INT IDENTITY(1,1) PRIMARY KEY,
    ProductID INT NOT NULL,
    MovementType NVARCHAR(20) NOT NULL
        CHECK (MovementType IN (N'purchase', N'sale', N'return', N'adjustment')),
    Quantity INT NOT NULL,
    BalanceAfter INT NOT NULL,
    ReferenceID INT NULL,
    UserID INT NULL,
    Notes NVARCHAR(300) NULL,
    MovementDate DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_Movements_Products FOREIGN KEY (ProductID)
        REFERENCES dbo.Products(ProductID),
    CONSTRAINT FK_Movements_Users FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID)
);
GO

CREATE INDEX IX_Products_ProductName ON dbo.Products(ProductName);
CREATE INDEX IX_Sales_SaleDate ON dbo.Sales(SaleDate);
CREATE INDEX IX_SaleDetails_SaleID ON dbo.SaleDetails(SaleID);
CREATE INDEX IX_Purchases_SupplierID ON dbo.Purchases(SupplierID);
CREATE INDEX IX_StockMovements_ProductID ON dbo.StockMovements(ProductID);
GO

-- كلمات المرور الافتراضية: admin / admin123 و cashier / cashier123 (يفضل تغييرها)
INSERT INTO dbo.Users (UserName, FullName, PasswordHash, Role, IsActive)
VALUES
(N'admin', N'مدير النظام', N'020fae3966b7dd415a9b0329efe4481c$0019da5ae3265c192b2c35f81d414202b6142d68306c29f3b2a666704bbce7e0', N'admin', 1),
(N'cashier', N'كاشير', N'2ab0eb60132cd370d5de0b329a5759cc$84a9852eae0e214f519586783ad7eb123027877552662acf0ee27aaa41a430bb', N'cashier', 1);
GO

INSERT INTO dbo.Categories (CategoryName)
VALUES (N'ألبان'), (N'مشروبات'), (N'معلبات'), (N'منظفات'), (N'مواد غذائية');
GO

INSERT INTO dbo.Products (ProductName, CategoryID, Price, CostPrice, Quantity, MinQuantity, Barcode)
VALUES
(N'لبن', 1, 30.00, 22.00, 50, 10, N'100001'),
(N'عصير', 2, 15.00, 11.00, 40, 10, N'100002'),
(N'تونة', 3, 45.00, 35.00, 25, 8, N'100003'),
(N'مسحوق غسيل', 4, 80.00, 60.00, 15, 5, N'100004'),
(N'أرز 1 كيلو', 5, 35.00, 26.00, 60, 15, N'100005');
GO

INSERT INTO dbo.Customers (CustomerName, Phone)
VALUES (N'عميل نقدي', NULL), (N'أحمد محمد', N'01000000000');
GO

INSERT INTO dbo.Suppliers (SupplierName, Phone, Address)
VALUES (N'مورد عام', N'01055555555', N'القاهرة');
GO

INSERT INTO dbo.Purchases (SupplierID, UserID, Notes)
VALUES (1, 1, N'رصيد افتتاحي');
GO

INSERT INTO dbo.PurchaseDetails (PurchaseID, ProductID, QuantityPurchased, UnitCost)
VALUES
(1, 1, 50, 22.00), (1, 2, 40, 11.00), (1, 3, 25, 35.00),
(1, 4, 15, 60.00), (1, 5, 60, 26.00);
GO

INSERT INTO dbo.StockMovements (ProductID, MovementType, Quantity, BalanceAfter, ReferenceID, UserID, Notes)
VALUES
(1, N'purchase', 50, 50, 1, 1, N'رصيد افتتاحي'),
(2, N'purchase', 40, 40, 1, 1, N'رصيد افتتاحي'),
(3, N'purchase', 25, 25, 1, 1, N'رصيد افتتاحي'),
(4, N'purchase', 15, 15, 1, 1, N'رصيد افتتاحي'),
(5, N'purchase', 60, 60, 1, 1, N'رصيد افتتاحي');
GO

-- Example query: products, categories, and stock levels
SELECT p.ProductID, p.ProductName, c.CategoryName, p.Price, p.Quantity, p.MinQuantity
FROM dbo.Products AS p
LEFT JOIN dbo.Categories AS c ON p.CategoryID = c.CategoryID
ORDER BY p.ProductID;
GO
