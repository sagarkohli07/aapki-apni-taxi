// Simple app.js for SQLite backend
const API_BASE = '';

// Current page state
let currentPage = 'home';
let isAdminLoggedIn = false;

// Page navigation
function showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // Show selected page
    const page = document.getElementById(pageId + '-page');
    if (page) {
        page.classList.add('active');
        currentPage = pageId;
    }

    // Load data for specific pages
    if (pageId === 'admin' && isAdminLoggedIn) {
        loadAdminBookings();
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span>${message}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

// Show loading overlay
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// Test API connection
async function testAPI() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        console.log('API Health:', data);
        return data.status === 'healthy';
    } catch (error) {
        console.error('API test failed:', error);
        return false;
    }
}

// Handle booking form submission
async function handleBookingSubmit(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const bookingData = {
        name: formData.get('name'),
        phone: formData.get('phone'),
        pickup: formData.get('pickup'),
        drop: formData.get('drop'),
        datetime: formData.get('datetime'),
        seats: formData.get('seats')
    };

    // Validate required fields
    if (!bookingData.name || !bookingData.phone || !bookingData.pickup || 
        !bookingData.drop || !bookingData.datetime || !bookingData.seats) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch('/api/bookings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(bookingData)
        });

        const result = await response.json();

        if (result.success) {
            // Show success modal
            document.getElementById('success-booking-id').textContent = result.booking_id;
            document.getElementById('booking-success-overlay').style.display = 'flex';

            // Reset form
            event.target.reset();

            showToast('Booking created successfully!', 'success');
        } else {
            showToast(result.error || 'Booking failed', 'error');
        }
    } catch (error) {
        console.error('Booking error:', error);
        showToast('Network error. Please try again.', 'error');
    }

    hideLoading();
}

// Close success modal
function closeSuccessModal() {
    document.getElementById('booking-success-overlay').style.display = 'none';
}

// Handle admin login
async function handleAdminLogin(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const username = formData.get('username');
    const password = formData.get('password');

    // Simple admin check
    if (username === 'admin' && password === 'admin123') {
        isAdminLoggedIn = true;
        document.getElementById('admin-login').style.display = 'none';
        document.getElementById('admin-dashboard').style.display = 'block';
        loadAdminBookings();
        showToast('Admin login successful', 'success');
    } else {
        showToast('Invalid credentials', 'error');
    }
}

// Admin logout
function adminLogout() {
    isAdminLoggedIn = false;
    document.getElementById('admin-login').style.display = 'block';
    document.getElementById('admin-dashboard').style.display = 'none';
    document.getElementById('admin-login-form').reset();
}

// Load admin bookings
async function loadAdminBookings() {
    try {
        const response = await fetch('/api/bookings');
        const result = await response.json();

        if (result.success) {
            displayAdminBookings(result.bookings);
        } else {
            showToast('Failed to load bookings', 'error');
        }
    } catch (error) {
        console.error('Load bookings error:', error);
        showToast('Failed to load bookings', 'error');
    }
}

// Display bookings in admin table
function displayAdminBookings(bookings) {
    const tbody = document.getElementById('admin-bookings-list');

    if (bookings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No bookings found</td></tr>';
        return;
    }

    tbody.innerHTML = bookings.map(booking => `
        <tr>
            <td>${booking.id}</td>
            <td>${booking.name}</td>
            <td>${booking.phone}</td>
            <td>${booking.pickup}</td>
            <td>${booking.drop}</td>
            <td>${new Date(booking.datetime).toLocaleString()}</td>
            <td>${booking.seats}</td>
            <td><span class="status-badge status-${booking.status}">${booking.status.toUpperCase()}</span></td>
            <td class="actions">
                ${booking.status === 'pending' ? `
                    <button class="btn btn--sm btn--success" onclick="updateBookingStatus(${booking.id}, 'confirmed')">Confirm</button>
                    <button class="btn btn--sm btn--danger" onclick="updateBookingStatus(${booking.id}, 'rejected')">Reject</button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

// Update booking status
async function updateBookingStatus(bookingId, status) {
    try {
        const response = await fetch(`/api/bookings/${bookingId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status })
        });

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            loadAdminBookings(); // Refresh the table
        } else {
            showToast(result.error || 'Update failed', 'error');
        }
    } catch (error) {
        console.error('Update status error:', error);
        showToast('Network error', 'error');
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set minimum datetime to current time
    const now = new Date();
    now.setMinutes(now.getMinutes() + 30); // 30 minutes from now
    document.getElementById('datetime').min = now.toISOString().slice(0, 16);

    // Bind form events
    const bookingForm = document.getElementById('booking-form');
    if (bookingForm) {
        bookingForm.addEventListener('submit', handleBookingSubmit);
    }

    const adminLoginForm = document.getElementById('admin-login-form');
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', handleAdminLogin);
    }

    // Test API connection
    testAPI().then(connected => {
        if (connected) {
            console.log('Backend connected successfully');
        } else {
            showToast('Backend connection issue', 'error');
        }
    });

    // Show home page by default
    showPage('home');
});
