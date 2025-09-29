import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from contextlib import contextmanager
import logging

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

port = int(os.environ.get('PORT', 5000))
DATABASE_FILE = 'bookings.db'

def init_db():
    """Initialize the database with proper error handling"""
    try:
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
        logger.info("✅ SQLite database initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

@contextmanager
def get_db():
    """Database connection context manager with proper error handling"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
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
            cursor = conn.execute('SELECT COUNT(*) FROM bookings')
            count = cursor.fetchone()[0]

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'type': 'SQLite',
            'bookings': count,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'database': 'disconnected',
            'error': str(e)
        }), 500

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        logger.info(f"📝 Creating booking for: {data.get('name')}")

        # Validate required fields
        required = ['name', 'phone', 'pickup', 'drop', 'datetime', 'seats']
        missing = [field for field in required if not data.get(field)]
        if missing:
            return jsonify({
                'success': False, 
                'error': f'Missing fields: {", ".join(missing)}'
            }), 400

        # Validate seats
        try:
            seats = int(data['seats'])
            if not (1 <= seats <= 6):
                return jsonify({
                    'success': False, 
                    'error': 'Seats must be between 1 and 6'
                }), 400
        except ValueError:
            return jsonify({
                'success': False, 
                'error': 'Invalid seats value'
            }), 400

        # Create booking
        now = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO bookings (name, phone, pickup, drop_location, datetime, seats, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (
                data['name'].strip(),
                data['phone'].strip(),
                data['pickup'].strip(),
                data['drop'].strip(),
                data['datetime'],
                seats,
                now,
                now
            ))

            booking_id = cursor.lastrowid
            conn.commit()

        logger.info(f"✅ Booking {booking_id} created successfully")

        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'message': 'Booking created successfully'
        })

    except Exception as e:
        logger.error(f"❌ Create booking error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error while creating booking'
        }), 500

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    try:
        logger.info("📋 Fetching all bookings...")

        with get_db() as conn:
            cursor = conn.execute("""
                SELECT 
                    id, 
                    name, 
                    phone, 
                    pickup, 
                    drop_location as drop, 
                    datetime, 
                    seats, 
                    status, 
                    created_at as createdAt, 
                    updated_at as updatedAt
                FROM bookings 
                ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()
            bookings = []

            for row in rows:
                booking = {
                    'id': row['id'],
                    'name': row['name'],
                    'phone': row['phone'],
                    'pickup': row['pickup'],
                    'drop': row['drop'],
                    'datetime': row['datetime'],
                    'seats': row['seats'],
                    'status': row['status'],
                    'createdAt': row['createdAt'],
                    'updatedAt': row['updatedAt']
                }
                bookings.append(booking)

        logger.info(f"✅ Retrieved {len(bookings)} bookings")

        return jsonify({
            'success': True,
            'bookings': bookings
        })

    except Exception as e:
        logger.error(f"❌ Get bookings error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error while fetching bookings'
        }), 500

@app.route('/api/bookings/<int:booking_id>/update', methods=['POST'])
def update_booking(booking_id):
    try:
        data = request.get_json()
        status = data.get('status')

        if status not in ['pending', 'confirmed', 'rejected']:
            return jsonify({
                'success': False,
                'error': 'Invalid status. Must be pending, confirmed, or rejected'
            }), 400

        now = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            cursor = conn.execute(
                'UPDATE bookings SET status = ?, updated_at = ? WHERE id = ?',
                (status, now, booking_id)
            )

            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"✅ Booking {booking_id} updated to {status}")

                return jsonify({
                    'success': True,
                    'message': f'Booking {booking_id} updated to {status}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Booking not found'
                }), 404

    except Exception as e:
        logger.error(f"❌ Update booking error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error while updating booking'
        }), 500

# Initialize database and start server
print("🚖 Starting Taxi Booking System...")
print("💾 Database: SQLite")
print("📱 SMS: Disabled")

if init_db():
    print("✅ SQLite Ready!")
else:
    print("❌ Database initialization failed!")

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=port)
