import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
from contextlib import contextmanager

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

port = int(os.environ.get('PORT', 5000))

DATABASE_FILE = 'taxi_bookings.db'

def init_database():
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
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
            ''')
            conn.commit()
            print("✅ SQLite database initialized successfully!")
            return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

@contextmanager
def get_db_connection():
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
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM bookings')
            count = cursor.fetchone()[0]
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'database_type': 'SQLite',
            'total_bookings': count,
            'sms': 'disabled',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'database': 'disconnected',
            'error': str(e)
        }), 500

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        logger.info(f"📝 New booking: {data.get('name')} - {data.get('phone')}")

        required_fields = ['name', 'phone', 'pickup', 'drop', 'datetime', 'seats']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({'success': False, 'error': f'Missing fields: {", ".join(missing_fields)}'}), 400

        try:
            seats = int(data['seats'])
            if seats < 1 or seats > 6:
                return jsonify({'success': False, 'error': 'Seats must be 1-6'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid seats'}), 400

        current_time = datetime.now(timezone.utc).isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bookings (name, phone, pickup, drop_location, datetime, seats, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['name'].strip(),
                data['phone'].strip(), 
                data['pickup'].strip(),
                data['drop'].strip(),
                data['datetime'],
                seats,
                'pending',
                current_time,
                current_time
            ))
            booking_id = cursor.lastrowid
            conn.commit()

        logger.info(f"💾 Booking {booking_id} saved successfully")

        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'message': 'Booking created successfully',
            'sms_sent': False,
            'booking': {
                'id': booking_id,
                'name': data['name'].strip(),
                'phone': data['phone'].strip(),
                'pickup': data['pickup'].strip(),
                'drop': data['drop'].strip(),
                'datetime': data['datetime'],
                'seats': seats,
                'status': 'pending',
                'createdAt': current_time,
                'updatedAt': current_time
            }
        })

    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@app.route('/api/bookings', methods=['GET'])
def get_all_bookings():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, phone, pickup, drop_location as drop, datetime, seats, status, 
                       created_at as createdAt, updated_at as updatedAt
                FROM bookings ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            bookings = [dict(row) for row in rows]

        return jsonify({'success': True, 'bookings': bookings})
    except Exception as e:
        logger.error(f"Error getting bookings: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@app.route('/api/bookings/<int:booking_id>/update', methods=['POST'])
def update_booking_status(booking_id):
    try:
        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ['pending', 'confirmed', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        current_time = datetime.now(timezone.utc).isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE bookings SET status = ?, updated_at = ? WHERE id = ?', 
                         (new_status, current_time, booking_id))

            if cursor.rowcount > 0:
                conn.commit()
                return jsonify({
                    'success': True,
                    'message': f'Booking {booking_id} updated to {new_status}',
                    'sms_sent': False
                })
            else:
                return jsonify({'success': False, 'error': 'Booking not found'}), 404

    except Exception as e:
        logger.error(f"Error updating booking: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

print("🚖 Starting Aapki Apni Taxi Server (SQLite)...")
print("="*50)
print("💾 Database: Local SQLite")
print("📱 SMS: Disabled")
print("🌐 Server: Production")
print("="*50)

db_ok = init_database()

if db_ok:
    print("✅ SQLite Database: Ready!")
    print("✅ Booking system: Fully functional")
    print("✅ NO SSL issues!")
else:
    print("❌ Database failed to initialize")

print("="*50)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=port)
