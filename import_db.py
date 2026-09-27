import pymysql

DB_HOST = "10.10.10.38"
DB_USER = "root"
DB_PASS = "0837741136"

print("กำลังเชื่อมต่อ Database...")
conn = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASS,
    client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS,
    autocommit=True
)

print("กำลังอ่านไฟล์ grocery_store_database.sql...")
with open("grocery_store_database.sql", "r", encoding="utf-8") as f:
    sql_script = f.read()

print("กำลังนำเข้าข้อมูลลง MySQL...")
with conn.cursor() as cursor:
    cursor.execute(sql_script)

conn.close()
print("สร้าง Database และนำเข้าข้อมูลเรียบร้อย 100%!")