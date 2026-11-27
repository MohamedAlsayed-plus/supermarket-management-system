/* Supermarket Management System
   SQL Server script: run this file in SQL Server Management Studio (SSMS).
*/

IF DB_ID(N'SupermarketDB') IS NULL
BEGIN
    CREATE DATABASE SupermarketDB;
END;
GO

USE SupermarketDB;
GO

IF OBJECT_ID(N'dbo.SaleDetails', N'U') IS NOT NULL DROP TABLE dbo.SaleDetails;
IF OBJECT_ID(N'dbo.Sales', N'U') IS NOT NULL DROP TABLE dbo.Sales;
IF OBJECT_ID(N'dbo.Customers', N'U') IS NOT NULL DROP TABLE dbo.Customers;
IF OBJECT_ID(N'dbo.Products', N'U') IS NOT NULL DROP TABLE dbo.Products;
IF OBJECT_ID(N'dbo.Categories', N'U') IS NOT NULL DROP TABLE dbo.Categories;
GO

CREATE TABLE dbo.Categories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(100) NOT NULL UNIQUE
);
GO

CREATE TABLE dbo.Products (
    ProductID INT IDENTITY(1,1) PRIMARY KEY,
    ProductName NVARCHAR(150) NOT NULL,
    CategoryID INT NULL,
    Price DECIMAL(10,2) NOT NULL CHECK (Price >= 0),
    Quantity INT NOT NULL DEFAULT 0 CHECK (Quantity >= 0),
    Barcode NVARCHAR(50) NULL UNIQUE,
    CONSTRAINT FK_Products_Categories FOREIGN KEY (CategoryID)
        REFERENCES dbo.Categories(CategoryID)
);
GO

CREATE TABLE dbo.Customers (
    CustomerID INT IDENTITY(1,1) PRIMARY KEY,
    CustomerName NVARCHAR(150) NOT NULL,
    Phone NVARCHAR(30) NULL
);
GO

CREATE TABLE dbo.Sales (
    SaleID INT IDENTITY(1,1) PRIMARY KEY,
    SaleDate DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CustomerID INT NULL,
    CONSTRAINT FK_Sales_Customers FOREIGN KEY (CustomerID)
        REFERENCES dbo.Customers(CustomerID)
);
GO

CREATE TABLE dbo.SaleDetails (
    SaleDetailID INT IDENTITY(1,1) PRIMARY KEY,
    SaleID INT NOT NULL,
    ProductID INT NOT NULL,
    QuantitySold INT NOT NULL CHECK (QuantitySold > 0),
    UnitPrice DECIMAL(10,2) NOT NULL CHECK (UnitPrice >= 0),
    CONSTRAINT FK_SaleDetails_Sales FOREIGN KEY (SaleID)
        REFERENCES dbo.Sales(SaleID),
    CONSTRAINT FK_SaleDetails_Products FOREIGN KEY (ProductID)
        REFERENCES dbo.Products(ProductID)
);
GO

INSERT INTO dbo.Categories (CategoryName)
VALUES (N'ألبان'), (N'مشروبات'), (N'معلبات'), (N'منظفات'), (N'مواد غذائية');
GO

INSERT INTO dbo.Products (ProductName, CategoryID, Price, Quantity, Barcode)
VALUES
(N'لبن', 1, 30.00, 50, N'100001'),
(N'عصير', 2, 15.00, 40, N'100002'),
(N'تونة', 3, 45.00, 25, N'100003'),
(N'مسحوق غسيل', 4, 80.00, 15, N'100004'),
(N'أرز 1 كيلو', 5, 35.00, 60, N'100005');
GO

INSERT INTO dbo.Customers (CustomerName, Phone)
VALUES (N'عميل نقدي', NULL), (N'أحمد محمد', N'01000000000');
GO

-- Example query: show products and their categories
SELECT p.ProductID, p.ProductName, c.CategoryName, p.Price, p.Quantity
FROM dbo.Products AS p
LEFT JOIN dbo.Categories AS c ON p.CategoryID = c.CategoryID
ORDER BY p.ProductID;
GO
