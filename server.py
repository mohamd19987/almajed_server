import os
from datetime import datetime, timedelta

from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras

# اتصال بقاعدة البيانات PostgreSQL عبر DATABASE_URL من Railway
DB_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

app = Flask(__name__)


def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            password VARCHAR(100),
            role VARCHAR(50)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            event_name VARCHAR(200),
            booking_date VARCHAR(50),
            customer_name VARCHAR(200),
            customer_phone VARCHAR(50),
            men_days TEXT,
            men_dates TEXT,
            men_time VARCHAR(50),
            women_days TEXT,
            women_dates TEXT,
            women_time VARCHAR(50),
            total_amount FLOAT,
            paid_amount FLOAT,
            remaining_amount FLOAT
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES ('admin', '1234', 'admin')
        """)

    conn.commit()


init_db()


@app.route("/")
def index():
    return jsonify({"status": "ok", "msg": "Almajed Hall API is running"})


# تسجيل الدخول
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    cursor.execute(
        "SELECT role FROM users WHERE username=%s AND password=%s",
        (username, password)
    )
    row = cursor.fetchone()

    if row:
        return jsonify({"status": "ok", "role": row["role"]})
    return jsonify({"status": "error", "msg": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401


# إضافة مستخدم (اختياري للإدارة)
@app.route("/users", methods=["POST"])
def add_user():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "user").strip()

    try:
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, %s)
        """, (username, password, role))
        conn.commit()
        return jsonify({"status": "ok"})
    except psycopg2.Error as e:
        return jsonify({"status": "error", "msg": str(e)}), 400


# حفظ حجز جديد
@app.route("/bookings", methods=["POST"])
def save_booking():
    data = request.get_json(force=True)

    event_name = data.get("event_name", "")
    booking_date = data.get("booking_date", "")
    customer_name = data.get("customer_name", "")
    customer_phone = data.get("customer_phone", "")
    men_days = data.get("men_days", "")
    men_dates = data.get("men_dates", "")
    men_time = data.get("men_time", "")
    women_days = data.get("women_days", "")
    women_dates = data.get("women_dates", "")
    women_time = data.get("women_time", "")
    total_amount = float(data.get("total_amount", 0) or 0)
    paid_amount = float(data.get("paid_amount", 0) or 0)
    remaining_amount = total_amount - paid_amount

    cursor.execute("""
        INSERT INTO bookings (
            event_name, booking_date, customer_name, customer_phone,
            men_days, men_dates, men_time,
            women_days, women_dates, women_time,
            total_amount, paid_amount, remaining_amount
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        event_name, booking_date, customer_name, customer_phone,
        men_days, men_dates, men_time,
        women_days, women_dates, women_time,
        total_amount, paid_amount, remaining_amount
    ))
    new_id = cursor.fetchone()["id"]
    conn.commit()

    return jsonify({"status": "ok", "invoice_id": new_id})


# جلب حجز واحد بالتفصيل
@app.route("/bookings/<int:booking_id>", methods=["GET"])
def get_booking(booking_id):
    cursor.execute("""
        SELECT *
        FROM bookings
        WHERE id = %s
    """, (booking_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"status": "error", "msg": "الحجز غير موجود"}), 404

    return jsonify({"status": "ok", "booking": dict(row)})


# البحث عن حجز بالاسم / الهاتف / التاريخ
@app.route("/search", methods=["GET"])
def search_booking():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"status": "ok", "results": []})

    cursor.execute("""
        SELECT id, customer_name, customer_phone, booking_date, event_name
        FROM bookings
        WHERE customer_name ILIKE %s
           OR customer_phone ILIKE %s
           OR booking_date ILIKE %s
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    rows = cursor.fetchall()

    results = [dict(r) for r in rows]
    return jsonify({"status": "ok", "results": results})


# تقرير يومي
@app.route("/daily_report", methods=["GET"])
def daily_report():
    date_str = request.args.get("date")
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT id, customer_name, event_name, booking_date,
               men_days, men_time, women_days, women_time
        FROM bookings
        WHERE booking_date = %s
    """, (date_str,))
    rows = cursor.fetchall()

    return jsonify({
        "status": "ok",
        "date": date_str,
        "results": [dict(r) for r in rows]
    })


# تقرير أسبوعي من تاريخ معيّن (أو من اليوم)
@app.route("/week_report", methods=["GET"])
def week_report():
    base_str = request.args.get("start")
    if base_str:
        base_date = datetime.strptime(base_str, "%Y-%m-%d")
    else:
        base_date = datetime.now()

    week_dates = [(base_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    cursor.execute("""
        SELECT id, customer_name, event_name, booking_date,
               men_days, men_time, women_days, women_time
        FROM bookings
        WHERE booking_date IN ({})
    """.format(",".join(["%s"] * len(week_dates))), week_dates)
    rows = cursor.fetchall()

    return jsonify({
        "status": "ok",
        "start": base_date.strftime("%Y-%m-%d"),
        "dates": week_dates,
        "results": [dict(r) for r in rows]
    })


if __name__ == "__main__":
    # للتشغيل المحلي فقط
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
