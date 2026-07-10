from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)

DB_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DB_URL)

@app.route("/")
def home():
    return "Almajed Server is Running"

@app.route("/add_booking", methods=["POST"])
def add_booking():
    data = request.get_json()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bookings (name, phone, event, date)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (data["name"], data["phone"], data["event"], data["date"]))
    booking_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "ok", "id": booking_id})

@app.route("/get_bookings", methods=["GET"])
def get_bookings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, phone, event, date FROM bookings")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    bookings = [
        {"id": r[0], "name": r[1], "phone": r[2], "event": r[3], "date": r[4]}
        for r in rows
    ]
    return jsonify(bookings)
