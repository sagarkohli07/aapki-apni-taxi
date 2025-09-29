
import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient, errors
from twilio.rest import Client
import logging
import ssl

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get port from environment (Render uses this)
port = int(os.environ.get('PORT', 5000))

# ✅ FIXED MongoDB connection string with SSL parameters
MONGODB_URI = "mongodb+srv://sagarkohli784_db_user:AwJpcHZhEvZT2Edq@sagar.btxiumr.mongodb.net/AapkiApniTaxi?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE"
DATABASE_NAME = "AapkiApniTaxi"
COLLECTION_NAME = "bookings"

# ✅ Verified Twilio credentials
TWILIO_ACCOUNT_SID = "ACdd96ce53f12b05834b6117a650f30cfd"
TWILIO_AUTH_TOKEN = "1f31eb002cf8e77a6c3778afd4ff960e"
TWILIO_PHONE_NUMBER = "+17197671551"

# Global variables
client = None
db = None
bookings_collection = None
twilio_client = None

def clean_phone_number(phone):
    """Convert phone numbers to proper international format"""
    if not phone:
        return phone

    digits = ''.join(filter(str.isdigit, phone))

    if len(digits) == 10 and digits[0] in ['6', '7', '8', '9']:
        return '+91' + digits

    if len(digits) == 12 and digits.startswith('91'):
        return '+' + digits

    if not phone.startswith('+'):
        return '+' + digits

    return phone

def initialize_mongodb():
    """Initialize MongoDB connection with SSL support"""
    global client, db, bookings_collection

    try:
        print("🔍 Connecting to MongoDB Atlas with SSL...")
        print(f"📡 Host: sagar.btxiumr.mongodb.net")

        # ✅ Create client with SSL settings
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=30000,  # Increased timeout
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            ssl=True,
            ssl_cert_reqs=ssl.CERT_NONE,  # ✅ Disable SSL certificate verification
            tlsAllowInvalidCertificates=True  # ✅ Allow invalid certificates
        )

        # Test the connection
        client.admin.command('ping')
        db = client[DATABASE_NAME]
        bookings_collection = db[COLLECTION_NAME]
        bookings_collection.create_index("id", unique=True)

        count = bookings_collection.count_documents({})
        logger.info(f"✅ MongoDB connected successfully! Found {count} existing bookings.")
        return True

    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return False

def initialize_twilio():
    """Initialize Twilio client with error handling"""
    global twilio_client

    try:
        print(f"🔍 Connecting to Twilio...")
        print(f"📱 SID: {TWILIO_ACCOUNT_SID}")

        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # ✅ Test connection by fetching account info
        account = twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()

        logger.info(f"✅ Twilio connected successfully! Account status: {account.status}")
        return True

    except Exception as e:
        logger.error(f"❌ Twilio connection failed: {e}")
        print(f"❌ Twilio Error Details: {e}")
        return False

def send_sms_safe(to_number, message):
    """Send SMS with graceful error handling"""
    if twilio_client is None:
        logger.warning("Twilio client not initialized - SMS functionality disabled")
        return False

    try:
        clean_phone = clean_phone_number(to_number)
        logger.info(f"📱 Sending SMS to: {to_number} → {clean_phone}")

        message_obj = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=clean_phone
        )
        logger.info(f"✅ SMS sent successfully to {clean_phone}")
        logger.info(f"   Message SID: {message_obj.sid}")
        return True

    except Exception as e:
        error_code = str(e)

        if "21608" in error_code or "not yet verified" in error_code.lower():
            logger.warning(f"⚠️  Phone number {clean_phone} not verified in Twilio trial account")
            logger.info(f"📝 SMS message (logged): {message}")
            return True  # Return True for development
        else:
            logger.error(f"❌ Failed to send SMS to {to_number}: {e}")
            return False

def get_next_booking_id():
    """Get the next booking ID"""
    if bookings_collection is None:
        return 1

    try:
        pipeline = [{"$group": {"_id": None, "max_id": {"$max": "$id"}}}]
        result = list(bookings_collection.aggregate(pipeline))

        if result and result[0]["max_id"]:
            return result[0]["max_id"] + 1
        else:
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
        'twilio': 'connected' if twilio_client is not None else 'disconnected',
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
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({'success': False, 'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

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

        try:
            result = bookings_collection.insert_one(booking)
            logger.info(f"💾 Booking saved to MongoDB with ObjectId: {result.inserted_id}")
        except Exception as e:
            logger.error(f"Database error: {e}")
            return jsonify({'success': False, 'error': 'Database error'}), 500

        # Short SMS message for Twilio trial
        customer_message = f"Taxi booked! ID:{booking_id} {booking['pickup']} to {booking['drop']} {datetime.fromisoformat(booking['datetime'].replace('T', ' ')).strftime('%d %b %I:%M%p')} Seats:{booking['seats']} Confirmation soon!"

        sms_sent = send_sms_safe(booking['phone'], customer_message)

        booking_response = booking.copy()
        booking_response.pop('_id', None)

        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'message': 'Booking created successfully',
            'sms_sent': sms_sent,
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
        for booking in bookings:
            booking.pop('_id', None)

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
            booking = bookings_collection.find_one({'id': booking_id})

            sms_sent = False
            if booking:
                if new_status == 'confirmed':
                    message = f"Booking #{booking_id} CONFIRMED! Driver will contact you soon."
                elif new_status == 'rejected':
                    message = f"Booking #{booking_id} could not be confirmed. Please try again."

                sms_sent = send_sms_safe(booking['phone'], message)

            return jsonify({
                'success': True,
                'message': f'Booking {booking_id} updated to {new_status}',
                'sms_sent': sms_sent
            })
        else:
            return jsonify({'success': False, 'error': 'Booking not found'}), 404

    except Exception as e:
        logger.error(f"Error updating booking status: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Initialize connections
print("🚖 Starting Aapki Apni Taxi Server...")
print("="*50)
print("📡 MongoDB Host: sagar.btxiumr.mongodb.net")
print(f"📱 Twilio Phone: {TWILIO_PHONE_NUMBER}")
print("🌐 Server: Production mode")
print("="*50)

mongodb_ok = initialize_mongodb()
twilio_ok = initialize_twilio()

print("\n🎯 FINAL STATUS:")
if mongodb_ok and twilio_ok:
    print("🎉 ALL SYSTEMS OPERATIONAL!")
    print("✅ MongoDB: Connected")
    print("✅ Twilio: Connected")
    print("✅ Ready to handle bookings!")
elif mongodb_ok:
    print("⚠️  PARTIAL FUNCTIONALITY")
    print("✅ MongoDB: Connected")
    print("❌ Twilio: FAILED (SMS disabled)")
    print("✅ Booking system works (no SMS)")
elif twilio_ok:
    print("⚠️  PARTIAL FUNCTIONALITY") 
    print("❌ MongoDB: FAILED (No database)")
    print("✅ Twilio: Connected")
    print("❌ Booking system won't work")
else:
    print("❌ BOTH SERVICES FAILED")
    print("❌ MongoDB: FAILED")
    print("❌ Twilio: FAILED")
    print("⚠️  App will have limited functionality")

print("="*50)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=port)
