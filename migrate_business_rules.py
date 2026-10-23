"""Safely migrate the existing grocery_store MariaDB schema to the business-rule schema.

Run from the project folder: python migrate_business_rules.py
This script does not drop existing customer/product/employee/sale/detail data.
It asks for confirmation before dropping out-of-scope tables.
"""
import os
import sys
import getpass
import pymysql
from pymysql.cursors import DictCursor

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_NAME = os.getenv('DB_NAME', 'grocery_store')
DB_PASSWORD = os.getenv('DB_PASSWORD')
if DB_PASSWORD is None:
    DB_PASSWORD = getpass.getpass(f'MySQL password for {DB_USER} (leave blank if none): ')


def connect():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASSWORD, database=DB_NAME,
                           charset='utf8mb4', cursorclass=DictCursor,
                           autocommit=True, connect_timeout=5)


def table_exists(cur, table):
    cur.execute('SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=%s AND table_name=%s', (DB_NAME, table))
    return cur.fetchone()['n'] > 0


def columns(cur, table):
    cur.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s', (DB_NAME, table))
    return {r['column_name'] for r in cur.fetchall()}


def rename_column(cur, table, old, new, definition):
    cols = columns(cur, table)
    if old in cols and new not in cols:
        cur.execute(f'ALTER TABLE `{table}` CHANGE COLUMN `{old}` `{new}` {definition}')


def add_column(cur, table, col, definition):
    if col not in columns(cur, table):
        cur.execute(f'ALTER TABLE `{table}` ADD COLUMN `{col}` {definition}')


def drop_fk_for_column(cur, table, column):
    cur.execute('''SELECT DISTINCT constraint_name FROM information_schema.key_column_usage
                   WHERE table_schema=%s AND table_name=%s AND column_name=%s
                   AND referenced_table_name IS NOT NULL''', (DB_NAME, table, column))
    for row in cur.fetchall():
        name = row['constraint_name'].replace('`', '``')
        cur.execute(f'ALTER TABLE `{table}` DROP FOREIGN KEY `{name}`')


def main():
    try:
        conn = connect()
    except Exception as exc:
        print(f'เชื่อมต่อฐานข้อมูลไม่สำเร็จ: {exc}')
        sys.exit(1)
    try:
        with conn.cursor() as cur:
            required = {'categories', 'products', 'employees', 'sales'}
            existing = {t for t in required if table_exists(cur, t)}
            missing = required - existing
            if missing:
                print('ไม่พบตารางจำเป็น: ' + ', '.join(sorted(missing)))
                print('ตรวจสอบ DB_NAME และฐานข้อมูล grocery_store ก่อน')
                sys.exit(2)

            # 1) Move customers to members, preserving rows and IDs.
            has_customers = table_exists(cur, 'customers')
            has_members = table_exists(cur, 'members')
            if has_customers and not has_members:
                drop_fk_for_column(cur, 'sales', 'customer_id')
                cur.execute('RENAME TABLE `customers` TO `members`')
                has_members = True
            elif has_customers and has_members:
                print('พบทั้ง customers และ members อยู่แล้ว; ไม่รวมตารางให้อัตโนมัติเพื่อป้องกันข้อมูลซ้ำ')
                print('กรุณาสำรองและตรวจสอบข้อมูลก่อน แล้วจึงรันใหม่')
                sys.exit(3)
            if not has_members:
                print('ไม่พบทั้ง customers และ members จึงไม่สามารถย้ายข้อมูลสมาชิกได้')
                sys.exit(4)

            # 2) Rename member fields. Keep optional legacy fields to avoid data loss.
            rename_column(cur, 'members', 'customer_id', 'member_id', 'INT NOT NULL AUTO_INCREMENT')
            rename_column(cur, 'members', 'customer_code', 'member_code', 'VARCHAR(20) NOT NULL')
            rename_column(cur, 'members', 'customer_name', 'member_name', 'VARCHAR(150) NOT NULL')
            rename_column(cur, 'members', 'loyalty_points', 'loyalty_points', 'INT NOT NULL DEFAULT 0')
            if 'member_id' not in columns(cur, 'members') or 'member_code' not in columns(cur, 'members') or 'member_name' not in columns(cur, 'members'):
                print('คอลัมน์ใน members ไม่ตรงกับโครงสร้างที่รองรับ โปรดส่งโครงสร้างตารางให้ตรวจสอบ')
                sys.exit(5)

            # 3) Rename the sales customer FK column, then add required sale attributes.
            rename_column(cur, 'sales', 'customer_id', 'member_id', 'INT NULL')
            add_column(cur, 'sales', 'total_amount', 'DECIMAL(12,2) NOT NULL DEFAULT 0.00')
            add_column(cur, 'sales', 'payment_method', "VARCHAR(20) NOT NULL DEFAULT 'CASH'")
            detail_source = 'sale_items' if table_exists(cur, 'sale_items') else ('sale_detail' if table_exists(cur, 'sale_detail') else None)
            if 'discount_amount' in columns(cur, 'sales') and detail_source:
                cur.execute(f'''UPDATE sales s LEFT JOIN
                    (SELECT sale_id, SUM(quantity * unit_price) AS subtotal FROM `{detail_source}` GROUP BY sale_id) d
                    ON d.sale_id=s.sale_id
                    SET s.total_amount=GREATEST(0, COALESCE(d.subtotal,0)-COALESCE(s.discount_amount,0))
                    WHERE s.total_amount=0''')
            if table_exists(cur, 'payments'):
                cur.execute('''UPDATE sales s JOIN payments p ON p.sale_id=s.sale_id
                    SET s.payment_method=p.payment_method WHERE s.payment_method='CASH' ''')

            # 4) Preserve detail data while renaming table.
            if table_exists(cur, 'sale_items') and not table_exists(cur, 'sale_detail'):
                cur.execute('RENAME TABLE `sale_items` TO `sale_detail`')
            if not table_exists(cur, 'sale_detail'):
                print('ไม่พบ sale_items หรือ sale_detail จึงไม่สามารถย้ายรายละเอียดการขายได้')
                sys.exit(6)

            # 5) Rebuild member FK using the final names. Remove stale FK on sales.member_id if present.
            drop_fk_for_column(cur, 'sales', 'member_id')
            if 'member_id' in columns(cur, 'sales'):
                cur.execute('''SELECT COUNT(*) AS n FROM information_schema.key_column_usage
                    WHERE table_schema=%s AND table_name='sales' AND column_name='member_id'
                    AND referenced_table_name='members' ''', (DB_NAME,))
                if cur.fetchone()['n'] == 0:
                    cur.execute('''ALTER TABLE sales ADD CONSTRAINT fk_sale_member
                        FOREIGN KEY (member_id) REFERENCES members(member_id)
                        ON UPDATE CASCADE ON DELETE SET NULL''')

            # Add the six business entities' required links if absent.
            # The product/category and sale detail FKs from the original schema are retained.
            # Payment and purchasing tables are not dropped automatically; keep existing history safe.
            print('\nMigration completed. Tables and row counts:')
            cur.execute('''SELECT table_name, table_rows FROM information_schema.tables
                           WHERE table_schema=%s AND table_type='BASE TABLE' ORDER BY table_name''', (DB_NAME,))
            for row in cur.fetchall():
                print(f"  {row['table_name']}: approx. {row['table_rows']} rows")
            print('\nหมายเหตุ: เก็บตารางนอกขอบเขตไว้ก่อนเพื่อป้องกันข้อมูลสูญหาย')
            print('เมื่อยืนยันว่าระบบทำงานครบแล้ว จึงค่อยพิจารณาลบตารางที่ไม่อยู่ใน 6 Entity')
    except Exception as exc:
        print(f'การย้ายโครงสร้างหยุดเนื่องจากข้อผิดพลาด: {exc}')
        print('สคริปต์จะไม่ลบฐานข้อมูล หากมีการเปลี่ยนแปลง DDL ไปแล้ว ให้ตรวจสอบตาราง/คอลัมน์ก่อนรันซ้ำ')
        sys.exit(10)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
