from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# الاتصال بقاعدة البيانات على Railway
DATABASE_URL = os.getenv("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# -----------------------------
# تسجيل الدخول
# -----------------------------
@app.post("/login")
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE username=%s AND password=%s", (username, password))
    row = cur.fetchone()
    conn.close()

    if row:
        return jsonify({"status": "ok", "role": row[0]})
    return jsonify({"status": "error"})


# -----------------------------
# إضافة مستخدم
# -----------------------------
@app.post("/add_user")
def add_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    role = data.get("role")

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, password, role))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


# -----------------------------
# حفظ الحجز
# -----------------------------
@app.post("/bookings")
def save_booking():
    data = request.json

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO bookings (
            event_name, booking_date, customer_name, customer_phone,
            men_days, men_dates, men_time,
            women_days, women_dates, women_time,
            total_amount, paid_amount, remaining_amount,
            notes, created_by
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        data["event_name"], data["booking_date"], data["customer_name"], data["customer_phone"],
        data["men_days"], data["men_dates"], data["men_time"],
        data["women_days"], data["women_dates"], data["women_time"],
        data["total_amount"], data["paid_amount"], data["remaining_amount"],
        data["notes"], data["created_by"]
    ))

    booking_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "id": booking_id})


# -----------------------------
# البحث
# -----------------------------
@app.get("/search")
def search():
    q = request.args.get("q", "")

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, customer_name, customer_phone, booking_date, event_name
        FROM bookings
        WHERE customer_name ILIKE %s OR customer_phone ILIKE %s OR booking_date ILIKE %s
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))

    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "customer_name": r[1],
            "customer_phone": r[2],
            "booking_date": r[3],
            "event_name": r[4]
        })

    return jsonify({"results": results})


# -----------------------------
# جلب حجز واحد
# -----------------------------
@app.get("/bookings/<int:booking_id>")
def get_booking(booking_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM bookings WHERE id=%s
    """, (booking_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"status": "not_found"})

    keys = [
        "id", "event_name", "booking_date", "customer_name", "customer_phone",
        "men_days", "men_dates", "men_time",
        "women_days", "women_dates", "women_time",
        "total_amount", "paid_amount", "remaining_amount",
        "notes", "created_by"
    ]

    booking = dict(zip(keys, row))

    return jsonify({"booking": booking})


# -----------------------------
# تقرير يومي
# -----------------------------
@app.get("/report/daily")
def report_daily():
    date = request.args.get("date")

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, customer_name, event_name, booking_date,
               men_days, men_time, women_days, women_time
        FROM bookings
        WHERE booking_date=%s
    """, (date,))

    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "customer_name": r[1],
            "event_name": r[2],
            "booking_date": r[3],
            "men_days": r[4],
            "men_time": r[5],
            "women_days": r[6],
            "women_time": r[7],
        })

    return jsonify({"results": results})


# -----------------------------
# تقرير أسبوعي
# -----------------------------
@app.get("/report/weekly")
def report_weekly():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, customer_name, event_name, booking_date,
               men_days, men_time, women_days, women_time
        FROM bookings
        ORDER BY booking_date DESC
        LIMIT 50
    """)

    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "customer_name": r[1],
            "event_name": r[2],
            "booking_date": r[3],
            "men_days": r[4],
            "men_time": r[5],
            "women_days": r[6],
            "women_time": r[7],
        })

    return jsonify({"results": results})


# -----------------------------
# تشغيل السيرفر
# -----------------------------
@app.get("/")
def home():
    return "Server is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
