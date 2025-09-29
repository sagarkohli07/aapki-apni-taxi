import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get port from environment (Render uses this)
port = int(os.environ.get('PORT', 5000))

# ✅ MongoDB Atlas connection string with TLS enabled
#    Make sure pymongo>=4.3.3 is in requirements.txt
MONGODB_URI = (
    "mongodb+srv://sagarkohli784_db_user:AwJpcHZhEvZT2Edq"
    "@sagar.btxiumr.mongodb.net/AapkiApniTaxi"
    "?retryWrites=true&w=majority&tls=true"
)
DATABASE_NAME = "AapkiApniTaxi"
COLLECTION_NAME = "bookings"

# Global variables
client = None
db = None
bookings_collection = None


def initialize_mongodb():
    """Initialize MongoDB connection with TLS."""
    global client, db, bookings_collection
    try:
        print("🔍 Connecting to MongoDB Atlas...")
        print(f"📡 Host: sagar.btxiumr.mongodb.net")

        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=30000  # 30-second timeout
        )

        # Test the connection
        client.admin.command('ping')
        db = client[DATABASE_NAME]
        bookings_collection = db[COLLECTION_NAME]

        # Create index safely
        try:
            bookings_collection.create_index("id", unique=True)
        except Exception:
            pass

        count = bookings_collection.count_documents({})
        logger.info(f"✅ MongoDB connected successfully! Found {count} existing bookings.")
        print(f"✅ MongoDB connected! Found {count} bookings.")
        return True

    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        print(f"❌ MongoDB Error: {e}")
        return False


def get_next_booking_id():
    if bookings_collection is None:
        return 1
    try:
        pipeline = [{"$group": {"_id": None, "max_id": {"$max": "$id"}}}]
        result = list(bookings_collection.aggregate(pipeline))
        if result and result[0]["max_id"]:
            return result[0]["max_id"] + 1
        return 1
    except Exception as e:
        logger.error(f"Error getting next booking ID: {e}")
        return 1


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'mongodb': 'connected' if bookings_collection is not None else 'disconnected',
        'sms': 'disabled',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'cluster': 'sagar.btxiumr.mongodb.net'
    })


@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        logger.info(f"📝 New booking request: {data.get('name')} - {data.get('phone')}")
        if bookings_collection is None:
            return jsonify({'success': False, 'error': 'Database connection unavailable'}), 500

        required_fields = ['name', 'phone', 'pickup', 'drop', 'datetime', 'seats']
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return jsonify({'success': False, 'error': f'Missing fields: {", ".join(missing_fields)}'}), 400

        try:
            seats = int(data['seats'])
            if seats < 1 or seats > 6:
                return jsonify({'success': False, 'error': 'Seats must be between 1 and 6'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid seats value'}), 400

        booking_id = get_next_booking_id()
        booking = {
            'id': booking_id,
            'name': data['name'].strip(),
            'phone': data['phone'].strip(),
            'pickup': data['pickup'].strip(),
            'drop': data['drop'].strip(),
            'datetime': data['datetime'],
            'seats': seats,
            'status': 'pending',
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'updatedAt': datetime.now(timezone.utc).isoformat()
        }

        result = bookings_collection.insert_one(booking)
        logger.info(f"💾 Booking saved to MongoDB with ObjectId: {result.inserted_id}")

        booking_response = booking.copy()
        booking_response.pop('_id', None)
        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'message': 'Booking created successfully',
            'sms_sent': False,
            'booking': booking_response
        })
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route('/api/bookings', methods=['GET'])
def get_all_bookings():
    try:
        if bookings_collection is None:
            return jsonify({'success': False, 'error': 'Database connection unavailable'}), 500
        bookings = list(bookings_collection.find().sort('createdAt', -1))
        for b in bookings:
            b.pop('_id', None)
        return jsonify({'success': True, 'bookings': bookings})
    except Exception as e:
        logger.error(f"Error getting bookings: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route('/api/bookings/<int:booking_id>/update', methods=['POST'])
def update_booking_status(booking_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        if new_status not in ['pending', 'confirmed', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        if bookings_collection is None:
            return jsonify({'success': False, 'error': 'Database connection unavailable'}), 500

        result = bookings_collection.update_one(
            {'id': booking_id},
            {'$set': {'status': new_status, 'updatedAt': datetime.now(timezone.utc).isoformat()}}
        )
        if result.modified_count > 0:
            return jsonify({'success': True,
                            'message': f'Booking {booking_id} updated to {new_status}',
                            'sms_sent': False})
        else:
            return jsonify({'success': False, 'error': 'Booking not found'}), 404
    except Exception as e:
        logger.error(f"Error updating booking status: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ----- Startup -----
print("🚖 Starting Aapki Apni Taxi Server (MongoDB Only)...")
print("=" * 50)
print("📡 MongoDB Host: sagar.btxiumr.mongodb.net")
print("📱 SMS: Disabled (as requested)")
print("🌐 Server: Production mode")
print("=" * 50)

mongodb_ok = initialize_mongodb()

print("\n🎯 FINAL STATUS:")
if mongodb_ok:
    print("✅ MongoDB: Connected - BOOKING SYSTEM READY!")
else:
    print("❌ MongoDB: FAILED")
    print("⚠️  Booking system won't work")
print("=" * 50)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=port)
