# Grocery Store Management System (POS & Database)

ระบบบริหารจัดการร้านขายของชำและ POS เชื่อมต่อฐานข้อมูล MySQL พัฒนาขึ้นโดยอ้างอิงโครงสร้างฐานข้อมูลเชิงสัมพันธ์และ Business Rules ของร้านขายของชำ ทำงานแบบแยกส่วนหน้าบ้าน (Frontend), API หลังบ้าน (Backend) และฐานข้อมูล (Database) อย่างชัดเจน

---

## ภาพรวมการทำงาน (Overview)

ระบบถูกออกแบบมาเพื่อจัดการงานขายหน้าร้านและการตัดสต็อกแบบ Real-time โดยคำนึงถึงความถูกต้องของข้อมูลตามกฎของระบบ:

- **หน้าขายหน้าร้าน (POS):** 
  - ค้นหาสินค้าจากชื่อหรือรหัสได้ทันที
  - เลือกลูกค้าได้ทั้งแบบสมาชิกร้าน และลูกค้าทั่วไป (Walk-in)
  - เลือกพนักงานที่รับผิดชอบบิลนั้นๆ
  - คำนวณยอดเงินรวม หักส่วนลด และเลือกช่องทางชำระเงิน (เงินสด, โอนเงิน, QR Code, บัตร)
- **การจัดการสต็อกและกฎทางธุรกิจ (Business Rules & Integrity):**
  - **ตัดสต็อกอัตโนมัติ:** เมื่อกดยืนยันการขาย ระบบจะเข้าไปลดจำนวนสินค้าในตาราง `products` ทันที
  - **ป้องกันการขายเกินสต็อก:** เช็กจำนวนคงเหลือก่อนบันทึกเสมอ หากสินค้าไม่พอหรือหมด ระบบจะไม่อนุญาตให้ทำรายการขาย
  - **เตือนจุดสั่งซื้อ (Reorder Level):** สินค้าที่ยอดเหลือต่ำกว่าหรือเท่ากับจุดสั่งซื้อจะแสดงสถานะเตือน
  - **Database Transaction:** ใช้คำสั่งชุด Transaction พร้อมล็อกแถวข้อมูล (`FOR UPDATE`) ป้องกันปัญหาสต็อกเพี้ยนเมื่อมีคนทำรายการพร้อมกัน หากมีขั้นตอนไหนพลาด ระบบจะ Rollback ทันที

---

## Tech Stack

- **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript (Fetch API)
- **Backend:** Python 3, Flask, Flask-CORS
- **Database Driver:** PyMySQL
- **Database:** MySQL 8.0+ (รันบน Linux/Docker Container หรือ Localhost)

---

## โครงสร้างฐานข้อมูล (Database Schema)

ฐานข้อมูลประกอบด้วย 10 ตารางหลักตาม ER Diagram:

```mermaid
erDiagram
    CUSTOMERS ||--o{ SALES : "has"
    EMPLOYEES ||--o{ SALES : "records"
    EMPLOYEES ||--o{ PURCHASES : "records"
    SUPPLIERS ||--o{ PURCHASES : "supplies"
    CATEGORIES ||--o{ PRODUCTS : "contains"
    SALES ||--|{ SALE_ITEMS : "contains"
    PRODUCTS ||--o{ SALE_ITEMS : "appears_in"
    PURCHASES ||--|{ PURCHASE_ITEMS : "contains"
    PRODUCTS ||--o{ PURCHASE_ITEMS : "appears_in"
    SALES ||--o| PAYMENTS : "paid_by"

    CUSTOMERS {
        int customer_id PK
        varchar customer_code UK
        varchar customer_name
        varchar phone
        varchar email
        varchar address
        boolean active
    }
    EMPLOYEES {
        int employee_id PK
        varchar employee_code UK
        varchar employee_name
        varchar phone
        varchar position
        date hire_date
        boolean active
    }
    SUPPLIERS {
        int supplier_id PK
        varchar supplier_code UK
        varchar supplier_name
        varchar contact_name
        varchar phone
        varchar email
        varchar address
        boolean active
    }
    CATEGORIES {
        int category_id PK
        varchar category_name UK
        varchar description
        boolean active
    }
    PRODUCTS {
        int product_id PK
        varchar product_code UK
        varchar barcode UK
        varchar product_name
        int category_id FK
        varchar unit
        decimal cost_price
        decimal selling_price
        int stock_qty
        int reorder_level
        boolean active
    }
    SALES {
        int sale_id PK
        varchar sale_no UK
        datetime sale_datetime
        int customer_id FK
        int employee_id FK
        decimal discount_amount
        varchar notes
    }
    SALE_ITEMS {
        int sale_id PK,FK
        int product_id PK,FK
        int quantity
        decimal unit_price
    }
    PURCHASES {
        int purchase_id PK
        varchar purchase_no UK
        datetime purchase_datetime
        int supplier_id FK
        int employee_id FK
        varchar notes
    }
    PURCHASE_ITEMS {
        int purchase_id PK,FK
        int product_id PK,FK
        int quantity
        decimal unit_cost
    }
    PAYMENTS {
        int payment_id PK
        int sale_id UK,FK
        datetime payment_datetime
        varchar payment_method
        decimal amount
        varchar reference_no
    }