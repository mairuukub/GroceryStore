-- Grocery Store Database Project
-- Target DBMS: MySQL 8.0+
-- File purpose: create database, create tables, insert sample data,
-- and provide example CRUD/query statements.
-- This file can also be used as a logical SQL backup/script.

DROP DATABASE IF EXISTS grocery_store;
CREATE DATABASE grocery_store
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE grocery_store;

-- 1) MASTER TABLES
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_code VARCHAR(20) NOT NULL UNIQUE,
    customer_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(150),
    address VARCHAR(255),
    active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_code VARCHAR(20) NOT NULL UNIQUE,
    employee_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20),
    position VARCHAR(80) NOT NULL,
    hire_date DATE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE suppliers (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_code VARCHAR(20) NOT NULL UNIQUE,
    supplier_name VARCHAR(150) NOT NULL,
    contact_name VARCHAR(150),
    phone VARCHAR(20),
    email VARCHAR(150),
    address VARCHAR(255),
    active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(30) NOT NULL UNIQUE,
    barcode VARCHAR(30) UNIQUE,
    product_name VARCHAR(150) NOT NULL,
    category_id INT NOT NULL,
    unit VARCHAR(30) NOT NULL,
    cost_price DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    selling_price DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    stock_qty INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_product_cost CHECK (cost_price >= 0),
    CONSTRAINT chk_product_selling CHECK (selling_price >= 0),
    CONSTRAINT chk_product_stock CHECK (stock_qty >= 0),
    CONSTRAINT chk_product_reorder CHECK (reorder_level >= 0),
    CONSTRAINT fk_product_category
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 2) TRANSACTION HEADER TABLES
CREATE TABLE sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_no VARCHAR(30) NOT NULL UNIQUE,
    sale_datetime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    customer_id INT NULL,
    employee_id INT NOT NULL,
    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    notes VARCHAR(255),
    CONSTRAINT chk_sale_discount CHECK (discount_amount >= 0),
    CONSTRAINT fk_sale_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_sale_employee
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE purchases (
    purchase_id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_no VARCHAR(30) NOT NULL UNIQUE,
    purchase_datetime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    supplier_id INT NOT NULL,
    employee_id INT NOT NULL,
    notes VARCHAR(255),
    CONSTRAINT fk_purchase_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_purchase_employee
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 3) TRANSACTION DETAIL TABLES
CREATE TABLE sale_items (
    sale_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (sale_id, product_id),
    CONSTRAINT chk_sale_item_qty CHECK (quantity > 0),
    CONSTRAINT chk_sale_item_price CHECK (unit_price >= 0),
    CONSTRAINT fk_sale_item_sale
        FOREIGN KEY (sale_id) REFERENCES sales(sale_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_sale_item_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE purchase_items (
    purchase_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_cost DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (purchase_id, product_id),
    CONSTRAINT chk_purchase_item_qty CHECK (quantity > 0),
    CONSTRAINT chk_purchase_item_cost CHECK (unit_cost >= 0),
    CONSTRAINT fk_purchase_item_purchase
        FOREIGN KEY (purchase_id) REFERENCES purchases(purchase_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_purchase_item_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL UNIQUE,
    payment_datetime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_method VARCHAR(20) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    reference_no VARCHAR(80),
    CONSTRAINT chk_payment_method CHECK (payment_method IN ('CASH','TRANSFER','CARD','QR')),
    CONSTRAINT chk_payment_amount CHECK (amount >= 0),
    CONSTRAINT fk_payment_sale
        FOREIGN KEY (sale_id) REFERENCES sales(sale_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4) INDEXES
CREATE INDEX idx_product_category ON products(category_id);
CREATE INDEX idx_sale_customer ON sales(customer_id);
CREATE INDEX idx_sale_employee ON sales(employee_id);
CREATE INDEX idx_sale_datetime ON sales(sale_datetime);
CREATE INDEX idx_purchase_supplier ON purchases(supplier_id);
CREATE INDEX idx_purchase_employee ON purchases(employee_id);
CREATE INDEX idx_purchase_datetime ON purchases(purchase_datetime);
CREATE INDEX idx_sale_item_product ON sale_items(product_id);
CREATE INDEX idx_purchase_item_product ON purchase_items(product_id);

-- 5) SAMPLE DATA
INSERT INTO categories (category_name, description) VALUES
('อาหารแห้ง', 'ข้าว บะหมี่กึ่งสำเร็จรูป และอาหารแห้ง'),
('เครื่องดื่ม', 'น้ำดื่ม น้ำอัดลม และเครื่องดื่มต่าง ๆ'),
('ขนมขบเคี้ยว', 'ขนมและของว่าง'),
('ของใช้ในบ้าน', 'ผลิตภัณฑ์สำหรับใช้ในบ้าน');

INSERT INTO customers (customer_code, customer_name, phone, email, address) VALUES
('CUS001', 'สมชาย ใจดี', '0812345678', 'somchai@example.com', 'กรุงเทพมหานคร'),
('CUS002', 'สุดา พอใจ', '0898765432', 'suda@example.com', 'นนทบุรี');

INSERT INTO employees (employee_code, employee_name, phone, position, hire_date) VALUES
('EMP001', 'กิตติ พนักงานดี', '0801111111', 'Cashier', '2026-01-10'),
('EMP002', 'มานะ ขยันงาน', '0802222222', 'Storekeeper', '2026-02-01');

INSERT INTO suppliers (supplier_code, supplier_name, contact_name, phone, email, address) VALUES
('SUP001', 'บริษัท อาหารไทย จำกัด', 'คุณวิชัย', '022222222', 'sales@thaifood.example', 'กรุงเทพมหานคร'),
('SUP002', 'บริษัท เครื่องดื่มดี จำกัด', 'คุณนิดา', '023333333', 'sales@drinkgood.example', 'ปทุมธานี');

INSERT INTO products
(product_code, barcode, product_name, category_id, unit, cost_price, selling_price, stock_qty, reorder_level)
VALUES
('P001', '8850000000011', 'ข้าวหอมมะลิ 5 กก.', 1, 'ถุง', 150.00, 180.00, 30, 10),
('P002', '8850000000028', 'บะหมี่กึ่งสำเร็จรูป', 1, 'ซอง', 5.00, 7.00, 100, 20),
('P003', '8850000000035', 'น้ำดื่ม 600 มล.', 2, 'ขวด', 4.00, 6.00, 120, 30),
('P004', '8850000000042', 'น้ำอัดลม 1.25 ลิตร', 2, 'ขวด', 18.00, 25.00, 50, 10),
('P005', '8850000000059', 'มันฝรั่งทอด', 3, 'ถุง', 20.00, 30.00, 40, 10),
('P006', '8850000000066', 'น้ำยาล้างจาน', 4, 'ขวด', 25.00, 35.00, 25, 5);

INSERT INTO sales (sale_no, sale_datetime, customer_id, employee_id, discount_amount, notes) VALUES
('S20260927001', '2026-09-27 09:30:00', 1, 1, 5.00, 'สมาชิก'),
('S20260927002', '2026-09-27 10:15:00', NULL, 1, 0.00, 'Walk-in');

INSERT INTO sale_items (sale_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 180.00),
(1, 2, 3, 7.00),
(2, 3, 4, 6.00),
(2, 5, 1, 30.00);

INSERT INTO payments (sale_id, payment_datetime, payment_method, amount, reference_no) VALUES
(1, '2026-09-27 09:31:00', 'CASH', 196.00, NULL),
(2, '2026-09-27 10:16:00', 'QR', 54.00, 'QR20260927002');

INSERT INTO purchases (purchase_no, purchase_datetime, supplier_id, employee_id, notes) VALUES
('PO20260927001', '2026-09-27 08:00:00', 1, 2, 'รับสินค้าอาหารแห้ง'),
('PO20260927002', '2026-09-27 08:30:00', 2, 2, 'รับสินค้าเครื่องดื่ม');

INSERT INTO purchase_items (purchase_id, product_id, quantity, unit_cost) VALUES
(1, 1, 20, 150.00),
(1, 2, 50, 5.00),
(2, 3, 60, 4.00),
(2, 4, 30, 18.00);

-- NOTE:
-- The sample stock_qty above is the starting stock for demonstration.
-- In a real transaction, purchase receiving should increase stock
-- and a completed sale should decrease stock in the same transaction.

-- 6) EXAMPLE READ QUERIES
-- All products with category
SELECT p.product_code, p.product_name, c.category_name,
       p.unit, p.selling_price, p.stock_qty
FROM products p
JOIN categories c ON c.category_id = p.category_id
ORDER BY p.product_code;

-- Sales report with calculated subtotal and grand total
SELECT s.sale_no, s.sale_datetime,
       COALESCE(c.customer_name, 'Walk-in') AS customer_name,
       e.employee_name,
       SUM(si.quantity * si.unit_price) AS subtotal,
       s.discount_amount,
       SUM(si.quantity * si.unit_price) - s.discount_amount AS grand_total
FROM sales s
LEFT JOIN customers c ON c.customer_id = s.customer_id
JOIN employees e ON e.employee_id = s.employee_id
JOIN sale_items si ON si.sale_id = s.sale_id
GROUP BY s.sale_id, s.sale_no, s.sale_datetime, c.customer_name,
         e.employee_name, s.discount_amount
ORDER BY s.sale_datetime DESC;

-- Products that should be reordered
SELECT product_code, product_name, stock_qty, reorder_level
FROM products
WHERE active = TRUE AND stock_qty <= reorder_level
ORDER BY stock_qty ASC;

-- 7) EXAMPLE INSERT
-- INSERT INTO customers
-- (customer_code, customer_name, phone, email, address)
-- VALUES ('CUS003', 'ลูกค้าทดสอบ', '0803333333', 'test@example.com', 'กรุงเทพมหานคร');

-- 8) EXAMPLE UPDATE
-- Prefer changing active status instead of deleting referenced master data.
-- UPDATE products SET selling_price = 32.00 WHERE product_id = 5;
-- UPDATE customers SET phone = '0809999999' WHERE customer_id = 1;
-- UPDATE products SET active = FALSE WHERE product_id = 6;

-- 9) EXAMPLE TRANSACTION FOR RECEIVING PURCHASE
-- START TRANSACTION;
-- INSERT INTO purchases (...) VALUES (...);
-- INSERT INTO purchase_items (...) VALUES (...);
-- UPDATE products
-- SET stock_qty = stock_qty + 10
-- WHERE product_id = 1;
-- COMMIT;

-- 10) EXAMPLE TRANSACTION FOR SALE
-- Before executing, verify stock_qty >= quantity for every sale item.
-- START TRANSACTION;
-- INSERT INTO sales (...) VALUES (...);
-- INSERT INTO sale_items (...) VALUES (...);
-- UPDATE products
-- SET stock_qty = stock_qty - 1
-- WHERE product_id = 1 AND stock_qty >= 1;
-- COMMIT;

-- 11) OPTIONAL VIEW FOR EASY REPORTING
CREATE OR REPLACE VIEW v_product_stock AS
SELECT p.product_id, p.product_code, p.product_name,
       c.category_name, p.unit, p.selling_price,
       p.stock_qty, p.reorder_level,
       CASE
         WHEN p.stock_qty <= p.reorder_level THEN 'REORDER'
         ELSE 'OK'
       END AS stock_status
FROM products p
JOIN categories c ON c.category_id = p.category_id
WHERE p.active = TRUE;

-- END OF SCRIPT
