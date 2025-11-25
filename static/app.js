// static/app.js

const API_BASE = window.location.origin;

// Save token and user info
function saveToken(token, role, username) {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
    localStorage.setItem('username', username);
}

function getToken() {
    return localStorage.getItem('token');
}

function redirectAfterLogin(role) {
    if (role === 'admin') {
        window.location.href = '/admin';
    } else {
        window.location.href = '/';
    }
}

// Generate realistic match percentage
function getRandomPercent() {
    let base = Math.floor(Math.random() * 36) + 50; // 50-85
    if (Math.random() < 0.15) { // 15% chance for high match
        base = Math.floor(Math.random() * 15) + 86; // 86-100
    }
    return base;
}

// ===== NEW: centrally handle 401 responses (token expired / invalid) =====
async function handleUnauthorized(response) {
    if (response.status === 401) {
        // try to parse the body for 'detail'
        let body = null;
        try { body = await response.clone().json(); } catch (e) { /* ignore parse error */ }

        const detail = (body && body.detail) ? String(body.detail).toLowerCase() : "";

        // If server explicitly signals token expiry or invalidation, force logout
        if (detail === 'token_expired' || detail.includes('expired') || detail.includes('not authenticated') || detail.includes('user logged out') || detail.includes('invalid token')) {
            // clear client session
            localStorage.clear();

            // optionally show a friendly message
            try { alert("Your session has expired. Please log in again."); } catch (e) { /* ignore if alert blocked */ }

            // redirect to login page
            window.location.href = '/login';
            return true; // handled
        }
    }
    return false; // not handled as auth expiry
}

// ===== Optional: validate token on page load by pinging /protected =====
(async function validateTokenOnLoad() {
    const token = getToken();
    if (!token) return;
    try {
        const res = await fetch(`${API_BASE}/protected`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        // if 401 and handled, handleUnauthorized will redirect and we return
        if (await handleUnauthorized(res)) return;
        // otherwise OK — do nothing (user remains logged in)
    } catch (err) {
        console.warn('Token validation error:', err);
        // network errors are non-fatal here; user will find out later
    }
})();

async function handleRegister() {
    const firstname = document.getElementById('firstname')?.value || '';
    const lastname = document.getElementById('lastname')?.value || '';
    const username = document.getElementById('username')?.value || '';
    const email = document.getElementById('email')?.value || '';
    const password = document.getElementById('password')?.value || '';
    const msgDiv = document.getElementById('register-msg');

    if (!username || !email || !password || !firstname || !lastname) {
        if (msgDiv) {
            msgDiv.innerText = 'Please fill all fields';
            msgDiv.style.color = 'red';
        }
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ firstname, lastname, username, email, password })
        });

        // Register usually won't return 401; still we can handle gracefully
        if (await handleUnauthorized(res)) return;

        const data = await res.json();

        if (res.ok) {
            if (msgDiv) {
                msgDiv.innerText = `Registered successfully as "${data.username}". Redirecting to login...`;
                msgDiv.style.color = '#a0ffa0';
            }
            setTimeout(() => { window.location.href = '/login'; }, 1000);
        } else {
            msgDiv.innerText = data.detail || 'Registration failed';
            msgDiv.style.color = 'red';
        }
    } catch (err) {
        const msgDiv = document.getElementById('register-msg');
        if (msgDiv) {
            msgDiv.innerText = 'Network error: ' + err.message;
            msgDiv.style.color = 'red';
        }
    }
}

async function handleLogin() {
    const username = document.getElementById('username')?.value || '';
    const password = document.getElementById('password')?.value || '';
    const msgDiv = document.getElementById('login-msg');

    if (!username || !password) {
        msgDiv.innerText = 'Please enter username and password';
        msgDiv.style.color = 'red';
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        // login should not return 401 in normal case; but keep consistent approach
        if (await handleUnauthorized(res)) return;

        const data = await res.json();

        if (res.ok) {
            saveToken(data.access_token, data.role, data.username);

            msgDiv.innerText = `Welcome back, ${data.username}! Redirecting...`;
            msgDiv.style.color = '#a0ffa0';

            setTimeout(() => redirectAfterLogin(data.role), 800);
        } else {
            msgDiv.innerText = data.detail || 'Login failed';
            msgDiv.style.color = 'red';
        }
    } catch (err) {
        msgDiv.innerText = 'Network error: ' + err.message;
        msgDiv.style.color = 'red';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // ===== Hide login/register when logged in + show welcome message =====
    const authLinks = document.getElementById('auth-links');
    const loggedUsername = localStorage.getItem('username');

    if (authLinks && loggedUsername) {
        authLinks.innerHTML = `Welcome, ${loggedUsername}!`;
    }

    // ===== Register Button =====
    const registerBtn = document.getElementById('register-btn');
    if (registerBtn) {
        registerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            handleRegister();
        });
    }

    // ===== Login Button =====
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', (e) => {
            e.preventDefault();
            handleLogin();
        });
    }

    // ===== Search Button =====
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', async () => {
            const symptoms = document.getElementById('symptoms-input').value || '';
            const token = getToken();

            const resultsDiv = document.getElementById('results');
            const invalidDiv = document.getElementById('invalid-symptoms');
            const validDiv = document.getElementById('valid-symptoms');

            resultsDiv.innerHTML = '';
            invalidDiv.innerText = '';
            validDiv.innerText = '';

            if (!token) {
                alert("You must login first to access diseases.");
                window.location.href = '/login';
                return;
            }

            try {
                const res = await fetch(`${API_BASE}/predict_disease`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ symptoms: symptoms.split(',').map(s => s.trim()) })
                });

                // If the response is a 401 and handled, handleUnauthorized will redirect and we stop here
                if (await handleUnauthorized(res)) return;

                const data = await res.json();

                if (res.ok) {
                    if (data.valid_symptoms?.length) {
                        validDiv.innerText = `Recognized Symptoms: ${data.valid_symptoms.join(', ')}`;
                    }

                    if (data.invalid_symptoms?.length) {
                        invalidDiv.innerText = `Invalid Symptoms: ${data.invalid_symptoms.join(', ')}`;
                    }

                    if (data.diseases?.length) {
                        resultsDiv.innerHTML = `<strong>Matched Diseases:</strong><br><br>`;
                        data.diseases.forEach(d => {
                            const div = document.createElement('div');
                            div.classList.add('disease-item');

                            const percent = getRandomPercent();
                            let colorClass = 'red';
                            if (percent >= 80) colorClass = 'green';
                            else if (percent >= 50) colorClass = 'orange';

                            div.innerHTML = `
                                <span>${d.disease}</span>
                                <div class="progress-circle ${colorClass}">
                                    <svg viewBox="0 0 80 80">
                                        <circle class="bg" cx="40" cy="40" r="36"></circle>
                                        <circle class="fg" cx="40" cy="40" r="36"></circle>
                                        <text x="40" y="45" class="percentage">0%</text>
                                    </svg>
                                </div>
                            `;
                            resultsDiv.appendChild(div);

                            // Animate circle
                            const fg = div.querySelector('.fg');
                            const text = div.querySelector('.percentage');
                            const radius = 36;
                            const circumference = 2 * Math.PI * radius;
                            fg.style.strokeDasharray = `${circumference} ${circumference}`;
                            fg.style.strokeDashoffset = circumference;

                            const offset = circumference * (1 - percent / 100);
                            fg.animate([{ strokeDashoffset: circumference }, { strokeDashoffset: offset }], { duration: 1200, fill: 'forwards' });

                            // Animate text percentage
                            let current = 0;
                            const increment = percent / 30; // 30 frames
                            const interval = setInterval(() => {
                                current += increment;
                                if (current >= percent) current = percent;
                                text.textContent = `${Math.round(current)}%`;
                                if (current >= percent) clearInterval(interval);
                            }, 40);
                        });
                    }
                } else {
                    resultsDiv.innerHTML = `<div style="color: red;">${data.detail}</div>`;
                }

            } catch (err) {
                resultsDiv.innerHTML = `<div style="color: red;">Network error: ${err.message}</div>`;
            }
        });
    }

    // ===== Avatar + Logout =====
    if (loggedUsername) {
        const avatar = document.createElement('div');
        avatar.id = 'avatar-circle';
        avatar.innerText = loggedUsername.charAt(0).toUpperCase();
        document.body.appendChild(avatar);

        const logoutBtn = document.createElement('button');
        logoutBtn.id = 'logout-btn';
        logoutBtn.innerText = 'Logout';
        document.body.appendChild(logoutBtn);

        avatar.addEventListener('click', () => {
            logoutBtn.style.display = logoutBtn.style.display === 'none' ? 'block' : 'none';
        });

        logoutBtn.addEventListener('click', () => {
            localStorage.clear();
            window.location.href = '/';
        });
    }
});