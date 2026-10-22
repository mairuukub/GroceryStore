"""Initialize/reset the grocery_store database from the SQL script.

WARNING: grocery_store_database.sql starts with DROP DATABASE IF EXISTS.
This will permanently delete an existing grocery_store database. Set RESET_DB=YES
to confirm before running this script.
"""
import os
from pathlib import Path
import pymysql

BASE_DIR = Path(__file__).resolve().parent
if os.getenv("RESET_DB") != "YES":
    raise SystemExit(
        "ยกเลิกเพื่อป้องกันข้อมูลหาย: ไฟล์ SQL จะลบฐานข้อมูล grocery_store เดิม\n"
        "สำรองข้อมูลก่อน แล้วตั้งค่า RESET_DB=YES เพื่อยืนยันการรีเซ็ตฐานข้อมูล"
    )

config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "charset": "utf8mb4",
    "client_flag": pymysql.constants.CLIENT.MULTI_STATEMENTS,
    "autocommit": True,
}
sql_path = BASE_DIR / "grocery_store_database.sql"
print(f"กำลังเชื่อมต่อ MySQL {config['host']}:{config['port']} ...")
conn = pymysql.connect(**config)
try:
    sql_script = sql_path.read_text(encoding="utf-8-sig")
    with conn.cursor() as cursor:
        cursor.execute(sql_script)
        while cursor.nextset():
            pass
    print("นำเข้าฐานข้อมูลและข้อมูลตัวอย่างเรียบร้อย")
finally:
    conn.close()
