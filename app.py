import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE_FILE = 'bookings.db'

def init_database():
    conn = sqlite3.connect(DATABASE_FILE)
    # Use quoted column names to avoid SQL reserved word issues
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            pickup TEXT,
            destination TEXT,
            datetime TEXT,
            seats INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized!")

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/<filename>')
def files(filename):
    return send_from_directory('.', filename)

@app.route('/api/health')
def health():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM bookings')
        count = cursor.fetchone()[0]
        conn.close()
        return {"status": "healthy", "database": "connected", "bookings": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.json
        print(f"📝 Creating booking for: {data.get('name')}")

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bookings (name, phone, pickup, destination, datetime, seats, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'],
            data['phone'], 
            data['pickup'],
            data['drop'],  # Will be stored as 'destination'
            data['datetime'],
            int(data['seats']),
            datetime.now().isoformat()
        ))

        booking_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"✅ Booking {booking_id} created successfully")
        return {"success": True, "booking_id": booking_id}

    except Exception as e:
        print(f"❌ Error creating booking: {e}")
        return {"success": False, "error": str(e)}

@app.route('/api/bookings')
def get_bookings():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Use 'destination' instead of 'drop' to avoid SQL reserved word issue
        cursor.execute("""
            SELECT id, name, phone, pickup, destination as drop, 
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
        print(f"✅ Retrieved {len(bookings)} bookings")
        return {"success": True, "bookings": bookings}

    except Exception as e:
        print(f"❌ Error getting bookings: {e}")
        return {"success": False, "bookings": [], "error": str(e)}

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

        print(f"✅ Booking {booking_id} updated to {status}")
        return {"success": True, "message": f"Booking updated to {status}"}

    except Exception as e:
        print(f"❌ Error updating booking: {e}")
        return {"success": False, "error": str(e)}

# Special endpoint for status checking
@app.route('/api/bookings/status', methods=['POST'])
def check_booking_status():
    try:
        data = request.json
        booking_id = data.get('booking_id')
        phone = data.get('phone')

        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, phone, pickup, destination as drop, 
                   datetime, seats, status, created_at as createdAt
            FROM bookings WHERE id = ? AND phone = ?
        """, (booking_id, phone))

        row = cursor.fetchone()
        conn.close()

        if row:
            booking = {
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"],
                "pickup": row["pickup"],
                "drop": row["drop"],
                "datetime": row["datetime"],
                "seats": row["seats"],
                "status": row["status"],
                "createdAt": row["createdAt"]
            }
            return {"success": True, "booking": booking}
        else:
            return {"success": False, "error": "Booking not found"}

    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return {"success": False, "error": str(e)}

print("🚖 Starting Complete Taxi System...")
init_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
