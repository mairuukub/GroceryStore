from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': '10.10.10.38',
    'user': 'root',
    'password': '0837741136',
    'database': 'grocery_store',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': False
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

# 1. API ดึงรายการสินค้าทั้งหมด (เฉพาะ active=TRUE)
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT p.product_id, p.product_code, p.barcode, p.product_name, 
                       c.category_name, p.unit, p.selling_price, p.stock_qty, p.reorder_level
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                WHERE p.active = TRUE
                ORDER BY p.product_id ASC
            """
            cursor.execute(sql)
            products = cursor.fetchall()
            return jsonify(products)
    finally:
        conn.close()

# 2. API ดึงข้อมูลลูกค้า
@app.route('/api/customers', methods=['GET'])
def get_customers():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT customer_id, customer_code, customer_name, phone FROM customers WHERE active = TRUE")
            return jsonify(cursor.fetchall())
    finally:
        conn.close()

# 3. API ดึงข้อมูลพนักงาน
@app.route('/api/employees', methods=['GET'])
def get_employees():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT employee_id, employee_code, employee_name, position FROM employees WHERE active = TRUE")
            return jsonify(cursor.fetchall())
    finally:
        conn.close()

# 4. API บันทึกการขาย (POS Checkout) รองรับ Transaction + ตัดสต็อกตาม Business Rules
@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json
    customer_id = data.get('customer_id') or None
    employee_id = data.get('employee_id', 1)
    discount_amount = float(data.get('discount_amount', 0))
    payment_method = data.get('payment_method', 'CASH')
    items = data.get('items', [])

    if not items:
        return jsonify({'error': 'ไม่มีสินค้าในตะกร้า'}), 400

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # ตรวจสอบสต็อกตาม BR-12 และ BR-13 (ห้ามขายเกินสต็อก)
            for item in items:
                cursor.execute("SELECT stock_qty, product_name, active FROM products WHERE product_id = %s FOR UPDATE", (item['product_id'],))
                prod = cursor.fetchone()
                if not prod or not prod['active']:
                    conn.rollback()
                    return jsonify({'error': f"สินค้า {item.get('product_name')} ไม่พร้อมขาย (Inactive)"}), 400
                if prod['stock_qty'] < item['quantity']:
                    conn.rollback()
                    return jsonify({'error': f"สินค้า {prod['product_name']} สต็อกไม่พอ (เหลือ {prod['stock_qty']})"}), 400

            # สร้าง Sale No แบบรันตามเวลา
            sale_no = f"S{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor.execute(
                """INSERT INTO sales (sale_no, sale_datetime, customer_id, employee_id, discount_amount, notes)
                   VALUES (%s, NOW(), %s, %s, %s, %s)""",
                (sale_no, customer_id, employee_id, discount_amount, data.get('notes', 'ขายหน้าร้าน'))
            )
            sale_id = cursor.lastrowid

            total_amount = 0
            # บันทึก sale_items และตัดสต็อก products (BR-12)
            for item in items:
                qty = int(item['quantity'])
                price = float(item['unit_price'])
                total_amount += (qty * price)

                cursor.execute(
                    """INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
                       VALUES (%s, %s, %s, %s)""",
                    (sale_id, item['product_id'], qty, price)
                )

                cursor.execute(
                    """UPDATE products SET stock_qty = stock_qty - %s WHERE product_id = %s""",
                    (qty, item['product_id'])
                )

            # คำนวณยอดชำระสุทธิ
            net_amount = max(0.0, total_amount - discount_amount)

            # บันทึก payments (BR-11)
            cursor.execute(
                """INSERT INTO payments (sale_id, payment_datetime, payment_method, amount, reference_no)
                   VALUES (%s, NOW(), %s, %s, %s)""",
                (sale_id, payment_method, net_amount, data.get('reference_no', None))
            )

            conn.commit()
            return jsonify({'success': True, 'sale_no': sale_no, 'net_amount': net_amount})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    print("🚀 Backend API รันอยู่ที่ http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)