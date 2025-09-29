import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from contextlib import contextmanager

app = Flask(__name__)
CORS(app)

port = int(os.environ.get('PORT', 5000))
DATABASE_FILE = 'bookings.db'

def init_db():
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                pickup TEXT NOT NULL,
                drop_location TEXT NOT NULL,
                datetime TEXT NOT NULL,
                seats INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
    print("✅ SQLite Ready!")

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory('.', filename)

@app.route('/api/health')
def health():
    try:
        with get_db() as conn:
            count = conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'type': 'SQLite',
            'bookings': count
        })
    except:
        return jsonify({'status': 'error'}), 500

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()

        required = ['name', 'phone', 'pickup', 'drop', 'datetime', 'seats']
        if not all(field in data for field in required):
            return jsonify({'success': False, 'error': 'Missing fields'}), 400

        seats = int(data['seats'])
        if not (1 <= seats <= 6):
            return jsonify({'success': False, 'error': 'Invalid seats'}), 400

        now = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO bookings (name, phone, pickup, drop_location, datetime, seats, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (data['name'], data['phone'], data['pickup'], data['drop'], data['datetime'], seats, now, now))

            booking_id = cursor.lastrowid
            conn.commit()

        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'message': 'Booking created successfully'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bookings')
def get_bookings():
    try:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT id, name, phone, pickup, drop_location as drop, datetime, 
                       seats, status, created_at as createdAt, updated_at as updatedAt
                FROM bookings ORDER BY created_at DESC
            """).fetchall()
            bookings = [dict(row) for row in rows]

        return jsonify({'success': True, 'bookings': bookings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bookings/<int:booking_id>/update', methods=['POST'])
def update_booking(booking_id):
    try:
        data = request.get_json()
        status = data.get('status')

        if status not in ['pending', 'confirmed', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        now = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            cursor = conn.execute(
                'UPDATE bookings SET status = ?, updated_at = ? WHERE id = ?',
                (status, now, booking_id)
            )

            if cursor.rowcount > 0:
                conn.commit()
                return jsonify({
                    'success': True,
                    'message': f'Booking {booking_id} updated to {status}'
                })
            else:
                return jsonify({'success': False, 'error': 'Booking not found'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

print("🚖 Starting Taxi Booking System...")
print("💾 Database: SQLite")
print("📱 SMS: Disabled")

init_db()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=port)
