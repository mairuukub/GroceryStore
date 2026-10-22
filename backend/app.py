import os
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pymysql
from pymysql.cursors import DictCursor

BASE_DIR = Path(__file__).resolve().parent
# Support the common project layout where backend/ and frontend/ are siblings.
FRONTEND_DIR = BASE_DIR.parent / "frontend"
HTML_FILE = FRONTEND_DIR / "grocery_pos.html"
if not HTML_FILE.is_file():
    HTML_FILE = BASE_DIR / "grocery_pos.html"
app = Flask(__name__, static_folder=None)
CORS(app)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "grocery_store"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": False,
    "connect_timeout": 5,
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def as_float(value, default=0):
    try:
        return float(value if value is not None else default)
    except (ValueError, TypeError):
        return float(default)

def json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    return value

def rows_json(rows):
    return [{k: json_value(v) for k, v in row.items()} for row in rows]

def error(message, status=400):
    return jsonify({"error": str(message)}), status

@app.errorhandler(pymysql.MySQLError)
def mysql_error(exc):
    app.logger.exception("MySQL error")
    return jsonify({"error": "เชื่อมต่อหรือดำเนินการกับ MySQL ไม่สำเร็จ: " + str(exc)}), 500

@app.get("/")
def index():
    return send_from_directory(HTML_FILE.parent, HTML_FILE.name)

@app.get("/api/health")
def health():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE() AS db_name, VERSION() AS mysql_version")
            return jsonify({"ok": True, **cur.fetchone()})
    finally:
        conn.close()

@app.get("/api/products")
def get_products():
    all_rows = request.args.get("all") == "1"
    conn = get_db()
    try:
        with conn.cursor() as cur:
            sql = """SELECT p.product_id AS id, p.product_code AS code, p.barcode,
                     p.product_name AS name, p.category_id, c.category_name,
                     p.unit, p.cost_price, p.selling_price, p.stock_qty,
                     p.reorder_level, p.expiry_date, p.active
                     FROM products p JOIN categories c ON c.category_id=p.category_id"""
            if not all_rows:
                sql += " WHERE p.active=TRUE"
            sql += " ORDER BY p.product_id"
            cur.execute(sql)
            return jsonify(rows_json(cur.fetchall()))
    finally:
        conn.close()

@app.post("/api/products")
def create_product():
    d = request.get_json(silent=True) or {}
    required = ["code", "name", "category_id", "unit", "cost_price", "selling_price", "stock_qty", "reorder_level"]
    if any(d.get(k) is None or str(d.get(k)).strip() == "" for k in required):
        return error("กรุณากรอกข้อมูลสินค้าให้ครบ")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO products
                (product_code,barcode,product_name,category_id,unit,cost_price,selling_price,stock_qty,reorder_level,expiry_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d["code"].strip(), d.get("barcode") or None, d["name"].strip(), int(d["category_id"]),
                 d["unit"].strip(), as_float(d["cost_price"]), as_float(d["selling_price"]),
                 as_float(d["stock_qty"]), as_float(d["reorder_level"]), d.get("expiry_date") or None))
            conn.commit()
            return jsonify({"success": True, "id": cur.lastrowid}), 201
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@app.route("/api/products/<int:product_id>", methods=["PUT", "PATCH"])
def update_product(product_id):
    d = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT product_id FROM products WHERE product_id=%s", (product_id,))
            if not cur.fetchone():
                return error("ไม่พบสินค้า", 404)
            if request.method == "PATCH" and "active" in d:
                cur.execute("UPDATE products SET active=%s WHERE product_id=%s", (bool(d["active"]), product_id))
            else:
                required = ["code", "name", "category_id", "unit", "cost_price", "selling_price", "stock_qty", "reorder_level"]
                if any(d.get(k) is None or str(d.get(k)).strip() == "" for k in required):
                    return error("กรุณากรอกข้อมูลสินค้าให้ครบ")
                cur.execute("""UPDATE products SET product_code=%s,barcode=%s,product_name=%s,category_id=%s,
                    unit=%s,cost_price=%s,selling_price=%s,stock_qty=%s,reorder_level=%s,expiry_date=%s
                    WHERE product_id=%s""",
                    (d["code"].strip(), d.get("barcode") or None, d["name"].strip(), int(d["category_id"]),
                     d["unit"].strip(), as_float(d["cost_price"]), as_float(d["selling_price"]),
                     as_float(d["stock_qty"]), as_float(d["reorder_level"]), d.get("expiry_date") or None, product_id))
            conn.commit()
            return jsonify({"success": True})
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@app.get("/api/customers")
def get_customers():
    all_rows = request.args.get("all") == "1"
    conn = get_db()
    try:
        with conn.cursor() as cur:
            sql = """SELECT customer_id AS id, customer_code AS code, customer_name AS name, phone,
                     credit_balance, loyalty_points AS points, active FROM customers"""
            if not all_rows:
                sql += " WHERE active=TRUE"
            sql += " ORDER BY customer_id"
            cur.execute(sql)
            return jsonify(rows_json(cur.fetchall()))
    finally:
        conn.close()

@app.post("/api/customers")
def create_customer():
    d = request.get_json(silent=True) or {}
    if not str(d.get("code", "")).strip() or not str(d.get("name", "")).strip():
        return error("กรุณากรอกรหัสและชื่อลูกค้า")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO customers (customer_code,customer_name,phone,credit_balance,loyalty_points)
                VALUES (%s,%s,%s,%s,%s)""",
                (d["code"].strip(), d["name"].strip(), d.get("phone") or None,
                 as_float(d.get("credit_balance")), int(as_float(d.get("points")))))
            conn.commit()
            return jsonify({"success": True, "id": cur.lastrowid}), 201
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@app.route("/api/customers/<int:customer_id>", methods=["PUT", "PATCH"])
def update_customer(customer_id):
    d = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT customer_id FROM customers WHERE customer_id=%s", (customer_id,))
            if not cur.fetchone():
                return error("ไม่พบลูกค้า", 404)
            if request.method == "PATCH" and "active" in d:
                cur.execute("UPDATE customers SET active=%s WHERE customer_id=%s", (bool(d["active"]), customer_id))
            else:
                if not str(d.get("code", "")).strip() or not str(d.get("name", "")).strip():
                    return error("กรุณากรอกรหัสและชื่อลูกค้า")
                cur.execute("""UPDATE customers SET customer_code=%s,customer_name=%s,phone=%s,
                    credit_balance=%s,loyalty_points=%s WHERE customer_id=%s""",
                    (d["code"].strip(), d["name"].strip(), d.get("phone") or None,
                     as_float(d.get("credit_balance")), int(as_float(d.get("points"))), customer_id))
            conn.commit()
            return jsonify({"success": True})
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@app.get("/api/categories")
def get_categories():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT category_id AS id, category_name AS name FROM categories WHERE active=TRUE ORDER BY category_id")
            return jsonify(cur.fetchall())
    finally:
        conn.close()

@app.get("/api/employees")
def get_employees():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT employee_id, employee_code, employee_name, position FROM employees WHERE active=TRUE ORDER BY employee_id")
            return jsonify(cur.fetchall())
    finally:
        conn.close()

@app.get("/api/dashboard")
def dashboard():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT COALESCE(SUM(p.amount),0) AS sales_today, COUNT(DISTINCT s.sale_id) AS bills_today
                FROM sales s JOIN payments p ON p.sale_id=s.sale_id WHERE DATE(s.sale_datetime)=CURDATE()""")
            totals = cur.fetchone()
            cur.execute("""SELECT product_code AS code, product_name AS name, stock_qty, reorder_level
                FROM products WHERE active=TRUE AND stock_qty<=reorder_level ORDER BY stock_qty""")
            low_stock = cur.fetchall()
            cur.execute("""SELECT product_name AS name, expiry_date FROM products
                WHERE active=TRUE AND expiry_date IS NOT NULL AND expiry_date BETWEEN CURDATE()
                AND DATE_ADD(CURDATE(), INTERVAL 30 DAY) ORDER BY expiry_date""")
            expiring = cur.fetchall()
            cur.execute("""SELECT p.payment_method, SUM(p.amount) AS amount FROM payments p
                JOIN sales s ON s.sale_id=p.sale_id WHERE DATE(s.sale_datetime)=CURDATE()
                GROUP BY p.payment_method ORDER BY p.payment_method""")
            payments = cur.fetchall()
            cur.execute("""SELECT pr.product_name AS name, SUM(si.quantity) AS qty
                FROM sale_items si JOIN sales s ON s.sale_id=si.sale_id
                JOIN products pr ON pr.product_id=si.product_id
                WHERE DATE(s.sale_datetime)=CURDATE()
                GROUP BY pr.product_id,pr.product_name ORDER BY qty DESC LIMIT 5""")
            top = cur.fetchall()
            return jsonify({"sales_today": json_value(totals["sales_today"]), "bills_today": totals["bills_today"],
                "low_stock": rows_json(low_stock), "expiring": rows_json(expiring),
                "payments": rows_json(payments), "top_sellers": rows_json(top)})
    finally:
        conn.close()

@app.post("/api/checkout")
def checkout():
    d = request.get_json(silent=True) or {}
    items = d.get("items") or []
    method = str(d.get("payment_method", "CASH")).upper()
    if method not in {"CASH", "TRANSFER", "CARD", "QR", "CREDIT"}:
        return error("วิธีชำระเงินไม่ถูกต้อง")
    if not items:
        return error("ไม่มีสินค้าในตะกร้า")
    discount = as_float(d.get("discount_amount"))
    if discount < 0:
        return error("ส่วนลดต้องไม่ติดลบ")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            total = Decimal("0.00")
            clean_items = []
            # Lock products and validate before writing any rows.
            for item in items:
                try:
                    pid = int(item["product_id"])
                    qty = Decimal(str(item["quantity"]))
                except (KeyError, ValueError, TypeError, InvalidOperation):
                    conn.rollback()
                    return error("ข้อมูลสินค้าในตะกร้าไม่ถูกต้อง")
                if qty <= 0:
                    conn.rollback()
                    return error("จำนวนสินค้าต้องมากกว่า 0")
                cur.execute("""SELECT product_id,product_name,selling_price,stock_qty,active
                    FROM products WHERE product_id=%s FOR UPDATE""", (pid,))
                p = cur.fetchone()
                if not p or not p["active"]:
                    conn.rollback()
                    return error("สินค้านี้ไม่พร้อมขาย")
                if Decimal(str(p["stock_qty"])) < qty:
                    conn.rollback()
                    return error(f"สินค้า {p['product_name']} สต็อกไม่พอ (เหลือ {p['stock_qty']})")
                price = Decimal(str(p["selling_price"]))
                total += qty * price
                clean_items.append((pid, qty, price, p["product_name"]))
            discount_dec = Decimal(str(discount))
            if discount_dec > total:
                conn.rollback()
                return error("ส่วนลดต้องไม่เกินยอดรวม")
            customer_id = d.get("customer_id") or None
            employee_id = int(d.get("employee_id") or 1)
            cur.execute("SELECT employee_id FROM employees WHERE employee_id=%s AND active=TRUE", (employee_id,))
            if not cur.fetchone():
                cur.execute("SELECT employee_id FROM employees WHERE active=TRUE ORDER BY employee_id LIMIT 1")
                emp = cur.fetchone()
                if not emp:
                    conn.rollback()
                    return error("ยังไม่มีพนักงานที่ใช้งานได้ กรุณาเพิ่มพนักงานในฐานข้อมูล", 400)
                employee_id = emp["employee_id"]
            if customer_id:
                cur.execute("SELECT customer_id FROM customers WHERE customer_id=%s AND active=TRUE", (int(customer_id),))
                if not cur.fetchone():
                    conn.rollback()
                    return error("ไม่พบลูกค้าที่เลือก")
                customer_id = int(customer_id)
            net = (total - discount_dec).quantize(Decimal("0.01"))
            sale_no = "S" + datetime.now().strftime("%Y%m%d%H%M%S%f")
            cur.execute("""INSERT INTO sales (sale_no,sale_datetime,customer_id,employee_id,discount_amount,notes)
                VALUES (%s,NOW(),%s,%s,%s,%s)""",
                (sale_no, customer_id, employee_id, discount_dec, d.get("notes", "ขายหน้าร้าน")))
            sale_id = cur.lastrowid
            for pid, qty, price, name in clean_items:
                cur.execute("INSERT INTO sale_items (sale_id,product_id,quantity,unit_price) VALUES (%s,%s,%s,%s)",
                            (sale_id, pid, qty, price))
                cur.execute("UPDATE products SET stock_qty=stock_qty-%s WHERE product_id=%s AND stock_qty >= %s",
                            (qty, pid, qty))
                if cur.rowcount != 1:
                    raise ValueError(f"ตัดสต็อกสินค้า {name} ไม่สำเร็จ")
            cur.execute("""INSERT INTO payments (sale_id,payment_datetime,payment_method,amount,reference_no)
                VALUES (%s,NOW(),%s,%s,%s)""", (sale_id, method, net, d.get("reference_no")))
            change = max(Decimal("0.00"), Decimal(str(as_float(d.get("cash_received")))) - net) if method == "CASH" else Decimal("0.00")
            points_earned = int(net // Decimal("10")) if customer_id else 0
            if customer_id and points_earned:
                cur.execute("UPDATE customers SET loyalty_points=loyalty_points+%s WHERE customer_id=%s", (points_earned, customer_id))
            conn.commit()
            return jsonify({"success": True, "sale_no": sale_no, "net_amount": float(net),
                            "change": float(change), "points_earned": points_earned})
    except ValueError as exc:
        conn.rollback()
        return error(str(exc), 400)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@app.post("/api/shifts/close")
def close_shift():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT p.payment_method, COALESCE(SUM(p.amount),0) AS amount
                FROM payments p JOIN sales s ON s.sale_id=p.sale_id
                WHERE DATE(s.sale_datetime)=CURDATE()
                GROUP BY p.payment_method ORDER BY p.payment_method""")
            payments = rows_json(cur.fetchall())
            total = sum(x["amount"] for x in payments)
            # This endpoint summarizes the current day; it does not prevent later sales.
            return jsonify({"total": total, "payments": payments, "date": date.today().isoformat()})
    finally:
        conn.close()

if __name__ == "__main__":
    print("Grocery Store API: http://127.0.0.1:5000")
    print("Database:", DB_CONFIG["host"], DB_CONFIG["database"], "user:", DB_CONFIG["user"])
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
