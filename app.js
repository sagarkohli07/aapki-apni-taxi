// Complete JavaScript with ALL fixes
const API_BASE = '';

let currentPage = 'home';
let isAdminLoggedIn = false;

// Page navigation
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    const page = document.getElementById(pageId + '-page');
    if (page) {
        page.classList.add('active');
        currentPage = pageId;
    }

    // Close mobile menu when page is selected
    closeMobileMenu();

    // Load admin bookings if needed
    if (pageId === 'admin' && isAdminLoggedIn) {
        loadAdminBookings();
    }
}

// Mobile menu handling
function toggleMobileMenu() {
    const navLinks = document.querySelector('.nav-links');
    const navMobile = document.querySelector('.nav-mobile');

    if (navLinks && navMobile) {
        navLinks.classList.toggle('nav-links--active');
        navMobile.classList.toggle('nav-mobile--active');
    }
}

function closeMobileMenu() {
    const navLinks = document.querySelector('.nav-links');
    const navMobile = document.querySelector('.nav-mobile');

    if (navLinks && navMobile) {
        navLinks.classList.remove('nav-links--active');
        navMobile.classList.remove('nav-mobile--active');
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

function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'none';
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

    if (!bookingData.name || !bookingData.phone || !bookingData.pickup || 
        !bookingData.drop || !bookingData.datetime || !bookingData.seats) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch('/api/bookings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bookingData)
        });

        const result = await response.json();

        if (result.success) {
            const successIdEl = document.getElementById('success-booking-id');
            if (successIdEl) successIdEl.textContent = result.booking_id;

            const successOverlay = document.getElementById('booking-success-overlay');
            if (successOverlay) successOverlay.style.display = 'flex';

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

function closeSuccessModal() {
    const overlay = document.getElementById('booking-success-overlay');
    if (overlay) overlay.style.display = 'none';
}

// Handle status form submission
async function handleStatusSubmit(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const bookingId = formData.get('booking-id');
    const phone = formData.get('phone');

    if (!bookingId || !phone) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch('/api/bookings/status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ booking_id: bookingId, phone: phone })
        });

        const result = await response.json();

        if (result.success) {
            displayBookingStatus(result.booking);
        } else {
            showToast(result.error || 'Booking not found', 'error');
        }
    } catch (error) {
        console.error('Status check error:', error);
        showToast('Network error. Please try again.', 'error');
    }

    hideLoading();
}

function displayBookingStatus(booking) {
    const resultDiv = document.getElementById('status-result');
    if (!resultDiv) return;

    const statusColors = {
        'pending': '#ffc107',
        'confirmed': '#28a745',
        'rejected': '#dc3545'
    };

    resultDiv.innerHTML = `
        <div class="status-card">
            <h3>Booking Details</h3>
            <div class="booking-info">
                <div class="info-row">
                    <span class="info-label">Booking ID:</span>
                    <span class="info-value">${booking.id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Name:</span>
                    <span class="info-value">${booking.name}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Phone:</span>
                    <span class="info-value">${booking.phone}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Pickup:</span>
                    <span class="info-value">${booking.pickup}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Drop:</span>
                    <span class="info-value">${booking.drop}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Date & Time:</span>
                    <span class="info-value">${new Date(booking.datetime).toLocaleString()}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Seats:</span>
                    <span class="info-value">${booking.seats}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Status:</span>
                    <span class="status-badge" style="background: ${statusColors[booking.status] || '#6c757d'}; color: white; padding: 4px 8px; border-radius: 4px;">
                        ${booking.status.toUpperCase()}
                    </span>
                </div>
            </div>
        </div>
    `;

    resultDiv.style.display = 'block';
}

// Admin functions
async function handleAdminLogin(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const username = formData.get('username');
    const password = formData.get('password');

    if (username === 'admin' && password === 'admin123') {
        isAdminLoggedIn = true;
        const loginDiv = document.getElementById('admin-login');
        const dashboardDiv = document.getElementById('admin-dashboard');

        if (loginDiv) loginDiv.style.display = 'none';
        if (dashboardDiv) dashboardDiv.style.display = 'block';

        loadAdminBookings();
        showToast('Admin login successful', 'success');
    } else {
        showToast('Invalid credentials', 'error');
    }
}

function adminLogout() {
    isAdminLoggedIn = false;
    const loginDiv = document.getElementById('admin-login');
    const dashboardDiv = document.getElementById('admin-dashboard');
    const form = document.getElementById('admin-login-form');

    if (loginDiv) loginDiv.style.display = 'block';
    if (dashboardDiv) dashboardDiv.style.display = 'none';
    if (form) form.reset();
}

async function loadAdminBookings() {
    try {
        const response = await fetch('/api/bookings');
        const result = await response.json();

        if (result.success) {
            displayAdminBookings(result.bookings);
        } else {
            showToast('Failed to load bookings: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Load bookings error:', error);
        showToast('Failed to load bookings', 'error');
    }
}

function displayAdminBookings(bookings) {
    const tbody = document.getElementById('admin-bookings-list');
    if (!tbody) return;

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

async function updateBookingStatus(bookingId, status) {
    try {
        const response = await fetch(`/api/bookings/${bookingId}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            loadAdminBookings();
        } else {
            showToast(result.error || 'Update failed', 'error');
        }
    } catch (error) {
        console.error('Update status error:', error);
        showToast('Network error', 'error');
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Set minimum datetime
    const datetimeInput = document.getElementById('datetime');
    if (datetimeInput) {
        const now = new Date();
        now.setMinutes(now.getMinutes() + 30);
        datetimeInput.min = now.toISOString().slice(0, 16);
    }

    // Bind form events
    const bookingForm = document.getElementById('booking-form');
    if (bookingForm) {
        bookingForm.addEventListener('submit', handleBookingSubmit);
    }

    const statusForm = document.getElementById('status-form');
    if (statusForm) {
        statusForm.addEventListener('submit', handleStatusSubmit);
    }

    const adminLoginForm = document.getElementById('admin-login-form');
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', handleAdminLogin);
    }

    // Mobile menu event
    const navMobile = document.querySelector('.nav-mobile');
    if (navMobile) {
        navMobile.addEventListener('click', toggleMobileMenu);
    }

    // Show home page by default
    showPage('home');
});
