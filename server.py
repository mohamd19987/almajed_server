import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# تحديد ملف قاعدة البيانات داخل Railway
DB_PATH = "almajed.db"

app = Flask(__name__)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT,
            booking_date TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            men_days TEXT,
            men_dates TEXT,
            men_time TEXT,
            women_days TEXT,
            women_dates TEXT,
            women_time TEXT,
            total_amount REAL,
            paid_amount REAL,
            remaining_amount REAL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES ('admin', '1234', 'admin')
        """)

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return jsonify({"status": "ok", "msg": "Almajed Hall API is running"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({"status": "ok", "role": row["role"]})
    return jsonify({"status": "error", "msg": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401

@app.route("/bookings", methods=["POST"])
def save_booking():
    data = request.get_json()

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO bookings (
            event_name, booking_date, customer_name, customer_phone,
            men_days, men_dates, men_time,
            women_days, women_dates, women_time,
            total_amount, paid_amount, remaining_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("event_name"),
        data.get("booking_date"),
        data.get("customer_name"),
        data.get("customer_phone"),
        data.get("men_days"),
        data.get("men_dates"),
        data.get("men_time"),
        data.get("women_days"),
        data.get("women_dates"),
        data.get("women_time"),
        float(data.get("total_amount", 0)),
        float(data.get("paid_amount", 0)),
        float(data.get("remaining_amount", 0)),
    ))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "invoice_id": new_id})

@app.route("/bookings/<int:booking_id>", methods=["GET"])
def get_booking(booking_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE id=?", (booking_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"status": "error", "msg": "الحجز غير موجود"}), 404

    return jsonify({"status": "ok", "booking": dict(row)})

@app.route("/search", methods=["GET"])
def search_booking():
    q = request.args.get("q", "")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, customer_name, customer_phone, booking_date, event_name
        FROM bookings
        WHERE customer_name LIKE ? OR customer_phone LIKE ? OR booking_date LIKE ?
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    rows = cursor.fetchall()
    conn.close()

    return jsonify({"status": "ok", "results": [dict(r) for r in rows]})

@app.route("/report/daily", methods=["GET"])
def daily_report():
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, customer_name, event_name, booking_date,
               men_days, men_time, women_days, women_time
        FROM bookings
        WHERE booking_date = ?
    """, (date_str,))
    rows = cursor.fetchall()
    conn.close()

    return jsonify({"status": "ok", "results": [dict(r) for r in rows]})

@app.route("/report/weekly", methods=["GET"])
def weekly_report():
    start = request.args.get("start", datetime.now().strftime("%Y-%m-%d"))
    base_date = datetime.strptime(start, "%Y-%m-%d")

    week_dates = [(base_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT id, customer_name, event_name, booking_date,
               men_days, men_time, women_days, women_time
        FROM bookings
        WHERE booking_date IN ({','.join(['?']*7)})
    """, week_dates)
    rows = cursor.fetchall()
    conn.close()

    return jsonify({"status": "ok", "results": [dict(r) for r in rows]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
