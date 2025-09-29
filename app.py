import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE_FILE = 'taxi_bookings.db'

# Initialize database
def init_database():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            pickup TEXT,
            drop_location TEXT,
            datetime TEXT,
            seats INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database ready!")

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/<filename>')
def files(filename):
    return send_from_directory('.', filename)

@app.route('/api/health')
def health():
    return {"status": "healthy", "database": "connected"}

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.json

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bookings (name, phone, pickup, drop_location, datetime, seats, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'],
            data['phone'], 
            data['pickup'],
            data['drop'],
            data['datetime'],
            int(data['seats']),
            datetime.now().isoformat()
        ))

        booking_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {"success": True, "booking_id": booking_id}
    except:
        return {"success": False, "error": "Failed"}

@app.route('/api/bookings')
def get_bookings():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, phone, pickup, drop_location as drop, 
                   datetime, seats, status, created_at as createdAt
            FROM bookings ORDER BY id DESC
        """)

        rows = cursor.fetchall()
        bookings = []
        for row in rows:
            bookings.append({
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"],
                "pickup": row["pickup"],
                "drop": row["drop"],
                "datetime": row["datetime"],
                "seats": row["seats"],
                "status": row["status"],
                "createdAt": row["createdAt"]
            })

        conn.close()
        return {"success": True, "bookings": bookings}
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "bookings": []}

@app.route('/api/bookings/<int:booking_id>/update', methods=['POST'])
def update_booking(booking_id):
    try:
        data = request.json
        status = data['status']

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
        conn.commit()
        conn.close()

        return {"success": True, "message": f"Booking updated to {status}"}
    except:
        return {"success": False, "error": "Update failed"}

print("🚖 Starting Simple Taxi System...")
init_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
