
// Enhanced JavaScript with better error handling for booking status updates
// Application State
let currentPage = 'home';
let isAdminLoggedIn = false;
let bookings = [];
let seatAvailability = "Available";
let nextBookingId = 1;

// Admin credentials
const adminCredentials = {
    username: "admin",
    password: "admin123"
};

// Backend API configuration
const API_BASE_URL = 'http://localhost:5000/api';

// Initialize Application
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚖 Initializing Aapki Apni Taxi with MongoDB and Twilio...');

    // Test backend connection on startup
    testBackendConnection();

    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.classList.add('hidden');
    }

    initializeApp();
    setupEventListeners();
    setMinDateTime();
    loadBookingsFromDatabase();

    console.log('✅ Application initialized successfully');
});

async function testBackendConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Backend connection successful:', data);
        } else {
            console.error('❌ Backend health check failed:', response.status);
        }
    } catch (error) {
        console.error('❌ Cannot connect to backend server:', error.message);
        console.error('💡 Make sure server is running: python server_with_password.py');
    }
}

async function loadBookingsFromDatabase() {
    try {
        console.log('📊 Loading bookings from database...');
        const response = await fetch(`${API_BASE_URL}/bookings`);
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                bookings = data.bookings;
                console.log(`✅ Loaded ${bookings.length} bookings from database`);

                if (bookings.length > 0) {
                    const maxId = Math.max(...bookings.map(b => b.id));
                    nextBookingId = maxId + 1;
                }

                if (isAdminLoggedIn) {
                    updateBookingsTable();
                }
            }
        } else {
            console.error('❌ Failed to load bookings:', response.status);
        }
    } catch (error) {
        console.error('❌ Error loading bookings from database:', error);
        showToast('Unable to load existing bookings. Check server connection.', 'warning');
    }
}

function initializeApp() {
    showPage('home');
    if (isAdminLoggedIn) {
        updateBookingsTable();
    }
}

function setupEventListeners() {
    const bookingForm = document.getElementById('booking-form');
    if (bookingForm) {
        bookingForm.addEventListener('submit', handleBookingSubmission);
    }

    const adminLoginForm = document.getElementById('admin-login-form');
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', handleAdminLogin);
    }

    const statusCheckForm = document.getElementById('status-check-form');
    if (statusCheckForm) {
        statusCheckForm.addEventListener('submit', handleStatusCheck);
    }
}

// Navigation Functions - Updated for your HTML structure
function showPage(pageId) {
    console.log('🧭 Navigating to page:', pageId);

    const pages = document.querySelectorAll('.page');
    pages.forEach(page => {
        page.classList.remove('active');
    });

    const pageMapping = {
        'home': 'home-page',
        'booking': 'booking-page',
        'book': 'booking-page',
        'status': 'status-page',
        'availability': 'availability-page', 
        'admin': 'admin-page'
    };

    const actualPageId = pageMapping[pageId] || pageId;
    const targetPage = document.getElementById(actualPageId);

    if (targetPage) {
        targetPage.classList.add('active');
        currentPage = pageId;

        if (pageId === 'admin') {
            if (isAdminLoggedIn) {
                showAdminDashboard();
            } else {
                showAdminLogin();
            }
        }

        if (pageId === 'status') {
            clearStatusResults();
        }

        console.log('✅ Successfully navigated to:', pageId);
    } else {
        console.error('❌ Page not found:', actualPageId);
    }
}

function toggleMobileNav() {
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
    }
}

function setMinDateTime() {
    const datetimeInput = document.getElementById('datetime');
    if (datetimeInput) {
        const now = new Date();
        const minDateTime = new Date(now.getTime() + 30 * 60000);
        datetimeInput.min = minDateTime.toISOString().slice(0, 16);
    }
}

async function handleBookingSubmission(event) {
    event.preventDefault();
    console.log('📝 Processing booking submission...');

    const formData = new FormData(event.target);
    const bookingData = {
        name: formData.get('name'),
        phone: formData.get('phone'),
        pickup: formData.get('pickup'),
        drop: formData.get('drop'),
        datetime: formData.get('datetime'),
        seats: parseInt(formData.get('seats'))
    };

    if (!validateBookingData(bookingData)) {
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/bookings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(bookingData)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            const newBooking = {
                id: result.booking_id,
                ...bookingData,
                status: 'pending',
                createdAt: new Date().toISOString()
            };

            bookings.push(newBooking);

            if (isAdminLoggedIn) {
                updateBookingsTable();
            }

            hideLoading();
            showBookingSuccessMessage(newBooking);
            event.target.reset();
            setMinDateTime();

            console.log('✅ Booking saved successfully with ID:', result.booking_id);

        } else {
            throw new Error(result.error || 'Failed to create booking');
        }

    } catch (error) {
        hideLoading();
        console.error('❌ Booking error:', error);
        showToast('Error saving booking to database. Please try again.', 'error');
    }
}

function showBookingSuccessMessage(booking) {
    const message = `✅ Booking ID: ${booking.id} created successfully! SMS sent to your phone.`;
    showToast(message, 'success', 8000);

    setTimeout(() => {
        showPage('status');
        const statusIdInput = document.getElementById('status-booking-id');
        if (statusIdInput) {
            statusIdInput.value = booking.id;
        }
    }, 3000);
}

async function handleStatusCheck(event) {
    event.preventDefault();
    console.log('🔍 Checking booking status...');

    const formData = new FormData(event.target);
    const bookingId = parseInt(formData.get('booking-id'));
    const phone = formData.get('phone').trim();

    if (!bookingId || !phone) {
        showToast('Please enter both Booking ID and Phone Number', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/bookings/${bookingId}/status?booking_id=${bookingId}&phone=${encodeURIComponent(phone)}`);
        const result = await response.json();

        hideLoading();

        if (response.ok && result.success) {
            displayBookingStatus(result.booking);
        } else {
            displayBookingNotFound();
        }

    } catch (error) {
        hideLoading();
        console.error('❌ Error checking booking status:', error);
        showToast('Error checking booking status. Please try again.', 'error');
    }
}

function displayBookingStatus(booking) {
    const statusResult = document.getElementById('status-result');
    if (!statusResult) return;

    const statusColor = {
        'pending': '#ffc107',
        'confirmed': '#28a745', 
        'rejected': '#dc3545'
    };

    const statusIcon = {
        'pending': '⏳',
        'confirmed': '✅',
        'rejected': '❌'
    };

    statusResult.classList.remove('hidden');
    statusResult.innerHTML = `
        <div class="card">
            <div class="card__body">
                <div class="status-display">
                    <div class="status-header">
                        <span class="status-icon" style="color: ${statusColor[booking.status]}">${statusIcon[booking.status]}</span>
                        <h3>Booking #${booking.id}</h3>
                        <span class="status status--${booking.status}">${booking.status.toUpperCase()}</span>
                    </div>

                    <div class="booking-details">
                        <div class="detail-row">
                            <span class="detail-label">Name:</span>
                            <span class="detail-value">${booking.name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Phone:</span>
                            <span class="detail-value">${booking.phone}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">From:</span>
                            <span class="detail-value">${booking.pickup}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">To:</span>
                            <span class="detail-value">${booking.drop}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Date & Time:</span>
                            <span class="detail-value">${new Date(booking.datetime).toLocaleString()}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Seats:</span>
                            <span class="detail-value">${booking.seats}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    statusResult.scrollIntoView({ behavior: 'smooth' });
}

function displayBookingNotFound() {
    const statusResult = document.getElementById('status-result');
    if (!statusResult) return;

    statusResult.classList.remove('hidden');
    statusResult.innerHTML = `
        <div class="card">
            <div class="card__body">
                <div class="status-display">
                    <div class="status-header">
                        <span class="status-icon error-icon">❌</span>
                        <h3>Booking Not Found</h3>
                    </div>
                    <p>No booking found with the provided details. Please check your Booking ID and phone number.</p>
                    <button onclick="showPage('booking')" class="btn btn--primary">Make New Booking</button>
                </div>
            </div>
        </div>
    `;

    statusResult.scrollIntoView({ behavior: 'smooth' });
}

function clearStatusResults() {
    const statusResult = document.getElementById('status-result');
    if (statusResult) {
        statusResult.classList.add('hidden');
        statusResult.innerHTML = '';
    }
}

function handleAdminLogin(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const username = formData.get('username');
    const password = formData.get('password');

    if (username === adminCredentials.username && password === adminCredentials.password) {
        isAdminLoggedIn = true;
        showAdminDashboard();
        showToast('Admin login successful', 'success');
        loadBookingsFromDatabase();
    } else {
        showToast('Invalid credentials', 'error');
    }
}

function showAdminLogin() {
    document.getElementById('admin-login').classList.remove('hidden');
    document.getElementById('admin-dashboard').classList.add('hidden');
}

function showAdminDashboard() {
    document.getElementById('admin-login').classList.add('hidden');
    document.getElementById('admin-dashboard').classList.remove('hidden');
    updateBookingsTable();
}

function adminLogout() {
    isAdminLoggedIn = false;
    showAdminLogin();
    showToast('Logged out successfully', 'success');
}

function updateBookingsTable() {
    const tbody = document.getElementById('bookings-table-body');
    if (!tbody) return;

    if (bookings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #666;">No bookings found</td></tr>';
        return;
    }

    const sortedBookings = [...bookings].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    tbody.innerHTML = sortedBookings.map(booking => `
        <tr class="booking-row ${booking.status}">
            <td>${booking.id}</td>
            <td>${booking.name}</td>
            <td>${booking.phone}</td>
            <td>${booking.pickup}</td>
            <td>${booking.drop}</td>
            <td>${new Date(booking.datetime).toLocaleString()}</td>
            <td>${booking.seats}</td>
            <td>
                <span class="status status--${booking.status}">${booking.status.toUpperCase()}</span>
            </td>
            <td class="actions">
                ${booking.status === 'pending' ? `
                    <button onclick="updateBookingStatus(${booking.id}, 'confirmed')" class="btn btn--sm btn--success">✅ Confirm</button>
                    <button onclick="updateBookingStatus(${booking.id}, 'rejected')" class="btn btn--sm btn--danger">❌ Reject</button>
                ` : `
                    <span class="status-final">${booking.status === 'confirmed' ? '✅ Confirmed' : '❌ Rejected'}</span>
                `}
            </td>
        </tr>
    `).join('');
}

// FIXED updateBookingStatus function with comprehensive error handling
async function updateBookingStatus(bookingId, newStatus) {
    console.log(`🔄 Attempting to update booking ${bookingId} to ${newStatus}`);

    try {
        showLoading();

        // First check if backend server is reachable
        console.log('🔍 Testing backend connection...');
        try {
            const healthResponse = await fetch(`${API_BASE_URL}/health`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!healthResponse.ok) {
                throw new Error(`Backend server returned ${healthResponse.status}`);
            }

            console.log('✅ Backend server is reachable');
        } catch (error) {
            console.error('❌ Backend server connectivity test failed:', error);
            throw new Error('Cannot connect to backend server. Please ensure server is running on localhost:5000');
        }

        // Now attempt the booking status update
        console.log(`📡 Making API call to update booking ${bookingId}...`);

        const updateUrl = `${API_BASE_URL}/bookings/${bookingId}/update`;
        console.log('🔗 Update URL:', updateUrl);

        const requestBody = { status: newStatus };
        console.log('📦 Request body:', requestBody);

        const response = await fetch(updateUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        console.log('📊 Response status:', response.status);
        console.log('📊 Response ok:', response.ok);
        console.log('📊 Response headers:', Object.fromEntries(response.headers));

        if (!response.ok) {
            let errorMessage;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || `HTTP ${response.status}`;
                console.error('❌ Server error response:', errorData);
            } catch (parseError) {
                const errorText = await response.text();
                errorMessage = errorText || `HTTP ${response.status}`;
                console.error('❌ Server error response (text):', errorText);
            }

            throw new Error(`Server error: ${errorMessage}`);
        }

        const result = await response.json();
        console.log('✅ Update result:', result);

        if (result.success) {
            // Update local booking status
            const booking = bookings.find(b => b.id === bookingId);
            if (booking) {
                booking.status = newStatus;
                booking.updatedAt = new Date().toISOString();
                console.log('✅ Updated local booking:', booking);
            } else {
                console.warn('⚠️ Booking not found in local array:', bookingId);
            }

            // Refresh the table display
            updateBookingsTable();

            const actionText = newStatus === 'confirmed' ? 'confirmed' : 'rejected';
            const successMessage = `✅ Booking ${bookingId} ${actionText} successfully! Customer SMS sent.`;
            showToast(successMessage, 'success');

            console.log(`✅ ${successMessage}`);
        } else {
            throw new Error(result.error || 'Unknown server error');
        }

    } catch (error) {
        console.error('❌ Complete error details:', error);
        console.error('❌ Error stack:', error.stack);

        // Provide specific error messages based on error type
        let userErrorMessage;

        if (error.message.includes('Cannot connect to backend server')) {
            userErrorMessage = '🔌 Server Connection Error: Please ensure the backend server is running.\n\nTo start server: python server_with_password.py';
        } else if (error.message.includes('Server error: HTTP 404')) {
            userErrorMessage = '🔍 API Endpoint Not Found: The booking update endpoint is not available. Check server configuration.';
        } else if (error.message.includes('Server error: HTTP 500')) {
            userErrorMessage = '💾 Database Error: There was a database connection issue. Check MongoDB connection.';
        } else if (error.message.includes('Failed to fetch')) {
            userErrorMessage = '🌐 Network Error: Cannot connect to localhost:5000. Make sure the server is running.';
        } else {
            userErrorMessage = `❌ Update Error: ${error.message}\n\nCheck browser console (F12) for more details.`;
        }

        showToast(userErrorMessage, 'error');
    } finally {
        hideLoading();
    }
}

function validateBookingData(data) {
    if (!data.name || data.name.trim().length < 2) {
        showToast('Please enter a valid name (at least 2 characters)', 'error');
        return false;
    }

    if (!data.phone || data.phone.trim().length < 10) {
        showToast('Please enter a valid phone number', 'error');
        return false;
    }

    if (!data.pickup || data.pickup.trim().length < 3) {
        showToast('Please enter a valid pickup location', 'error');
        return false;
    }

    if (!data.drop || data.drop.trim().length < 3) {
        showToast('Please enter a valid drop location', 'error');
        return false;
    }

    if (!data.datetime) {
        showToast('Please select date and time', 'error');
        return false;
    }

    const selectedTime = new Date(data.datetime);
    const minTime = new Date(Date.now() + 30 * 60000);

    if (selectedTime < minTime) {
        showToast('Please select a time at least 30 minutes from now', 'error');
        return false;
    }

    if (!data.seats || data.seats < 1 || data.seats > 6) {
        showToast('Please select between 1 and 6 seats', 'error');
        return false;
    }

    return true;
}

function showLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.classList.remove('hidden');
    }
}

function hideLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.classList.add('hidden');
    }
}

function showToast(message, type = 'info', duration = 8000) {
    // Enhanced toast function
    console.log(`📢 Toast (${type}):`, message);

    if (type === 'error') {
        alert('❌ ERROR:\n\n' + message);
    } else if (type === 'success') {
        alert('✅ SUCCESS:\n\n' + message);
    } else if (type === 'warning') {
        alert('⚠️ WARNING:\n\n' + message);
    } else {
        alert('ℹ️ INFO:\n\n' + message);
    }
}

function hideToast() {
    // Implementation for hiding toast
}

function toggleAvailability() {
    const currentStatus = document.getElementById('admin-availability-status');
    const toggleButton = document.getElementById('toggle-availability');

    if (seatAvailability === "Available") {
        seatAvailability = "Fully Booked";
        currentStatus.textContent = "Fully Booked";
        currentStatus.className = "status status--rejected";
        toggleButton.textContent = "Set Available";
    } else {
        seatAvailability = "Available";
        currentStatus.textContent = "Available";  
        currentStatus.className = "status status--confirmed";
        toggleButton.textContent = "Set Fully Booked";
    }

    const publicStatus = document.getElementById('availability-status');
    const statusEmoji = document.getElementById('status-emoji');

    if (publicStatus) {
        publicStatus.textContent = seatAvailability;
    }

    if (statusEmoji) {
        statusEmoji.textContent = seatAvailability === "Available" ? "✅" : "❌";
    }
}
