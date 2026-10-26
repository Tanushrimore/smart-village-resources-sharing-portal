import streamlit as st
import sqlite3
import hashlib
import datetime

# --------------------------------------------------
# PAGE SETTINGS & DATABASE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Smart Village",
    page_icon="🌾",
    layout="wide"
)

DB_FILE = "smart_village.db"

def init_db():
    """Create database tables if they do not exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            village TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Resources Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            owner_name TEXT NOT NULL,
            owner_phone TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            village TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            price TEXT DEFAULT 'Free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    ''')

    # Resource Requests Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            requester_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'Pending',
            start_date TEXT,
            end_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resource_id) REFERENCES resources(id),
            FOREIGN KEY (requester_id) REFERENCES users(id),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    ''')

    # Reviews Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            reviewer_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resource_id) REFERENCES resources(id),
            FOREIGN KEY (reviewer_id) REFERENCES users(id)
        )
    ''')

    # Village Notice Board / Announcements Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            author_village TEXT NOT NULL,
            author_role TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users(id)
        )
    ''')

    # Safe schema migration for existing databases
    c.execute("PRAGMA table_info(resources)")
    res_cols = [col[1] for col in c.fetchall()]
    if "price" not in res_cols:
        c.execute("ALTER TABLE resources ADD COLUMN price TEXT DEFAULT 'Free'")

    c.execute("PRAGMA table_info(requests)")
    req_cols = [col[1] for col in c.fetchall()]
    if "start_date" not in req_cols:
        c.execute("ALTER TABLE requests ADD COLUMN start_date TEXT")
    if "end_date" not in req_cols:
        c.execute("ALTER TABLE requests ADD COLUMN end_date TEXT")

    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256 for security."""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(name, email, phone, village, password, role):
    """Insert a new user into the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO users (name, email, phone, village, password, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email.lower().strip(), phone, village, hash_password(password), role))
        conn.commit()
        conn.close()
        return True, "Account created successfully! 🎉"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "An account with this email already exists."

def authenticate_user(email, password):
    """Check credentials against the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT id, name, email, phone, role, village FROM users 
        WHERE email = ? AND password = ?
    ''', (email.lower().strip(), hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user

def add_resource(owner_id, owner_name, owner_phone, title, category, village, description, price="Free"):
    """Add a new resource listing to the database with optional price."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO resources (owner_id, owner_name, owner_phone, title, category, village, description, price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (owner_id, owner_name, owner_phone, title, category, village, description, price))
    conn.commit()
    conn.close()

def update_resource(resource_id, owner_id, title, category, village, description, price, status):
    """Update an existing resource listing."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE resources
        SET title = ?, category = ?, village = ?, description = ?, price = ?, status = ?
        WHERE id = ? AND owner_id = ?
    ''', (title, category, village, description, price, status, resource_id, owner_id))
    conn.commit()
    success = c.rowcount > 0
    conn.close()
    return success

def toggle_resource_availability(resource_id, owner_id):
    """Toggle resource availability between 'Available' and 'In Use'."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT status FROM resources WHERE id = ? AND owner_id = ?", (resource_id, owner_id))
    row = c.fetchone()
    if row:
        new_status = "In Use" if row[0] == "Available" else "Available"
        c.execute("UPDATE resources SET status = ? WHERE id = ? AND owner_id = ?", (new_status, resource_id, owner_id))
        conn.commit()
        conn.close()
        return new_status
    conn.close()
    return None

def delete_owner_resource(resource_id, owner_id):
    """Delete a resource listing by its owner."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM resources WHERE id = ? AND owner_id = ?", (resource_id, owner_id))
    conn.commit()
    success = c.rowcount > 0
    conn.close()
    return success

def get_resources(category_filter="All", village_filter="All", search_keyword="", availability_filter="All", price_filter="All"):
    """Fetch resource listings with optional filtering and keyword search."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    query = """
        SELECT id, title, category, village, description,
               owner_name, owner_phone, status, owner_id, COALESCE(price, 'Free')
        FROM resources
        WHERE 1=1
    """
    params = []

    if category_filter != "All":
        query += " AND category = ?"
        params.append(category_filter)

    if village_filter != "All":
        query += " AND village = ?"
        params.append(village_filter)

    if availability_filter != "All":
        query += " AND status = ?"
        params.append(availability_filter)

    if price_filter == "Free Only":
        query += " AND (price = 'Free' OR price = '' OR price IS NULL)"
    elif price_filter == "Paid Only":
        query += " AND price != 'Free' AND price != '' AND price IS NOT NULL"

    if search_keyword.strip():
        kw = f"%{search_keyword.strip().lower()}%"
        query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)"
        params.extend([kw, kw, kw])

    query += " ORDER BY id DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def get_owner_resources(owner_id):
    """Fetch all listings posted by a specific owner."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT id, title, category, village, description, status, COALESCE(price, 'Free'), created_at
        FROM resources
        WHERE owner_id = ?
        ORDER BY id DESC
    """, (owner_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_resource_owner_id(resource_id):
    """Fetch the owner ID for a given resource."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT owner_id FROM resources WHERE id = ?", (resource_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def submit_resource_request(resource_id, owner_id, requester_id, message, start_date=None, end_date=None):
    """Submit a request for a resource with optional duration dates."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO requests
            (resource_id, requester_id, owner_id, message, status, start_date, end_date)
            VALUES (?, ?, ?, ?, 'Pending', ?, ?)
        """, (resource_id, requester_id, owner_id, message, start_date, end_date))

        conn.commit()
        return True

    except sqlite3.Error as e:
        st.error(f"Could not submit request: {e}")
        return False

    finally:
        conn.close()

def get_owner_requests(owner_id):
    """Fetch all incoming requests made for resources owned by owner_id."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT 
            r.id, 
            r.resource_id, 
            COALESCE(res.title, 'Resource #' || r.resource_id) AS title, 
            COALESCE(res.category, 'General') AS category, 
            r.requester_id, 
            COALESCE(u.name, 'Unknown User') AS requester_name, 
            COALESCE(u.phone, 'N/A') AS requester_phone, 
            COALESCE(u.village, 'N/A') AS requester_village, 
            r.message, 
            r.status, 
            r.created_at,
            COALESCE(res.price, 'Free') AS price,
            r.start_date,
            r.end_date
        FROM requests r
        LEFT JOIN resources res ON r.resource_id = res.id
        LEFT JOIN users u ON r.requester_id = u.id
        WHERE r.owner_id = ?
        ORDER BY r.id DESC
    """, (owner_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def update_request_status(request_id, new_status, owner_id=None):
    """Update status of a request ('Accepted', 'Rejected')."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        if owner_id is not None:
            c.execute("""
                UPDATE requests 
                SET status = ? 
                WHERE id = ? AND owner_id = ?
            """, (new_status, request_id, owner_id))
        else:
            c.execute("""
                UPDATE requests 
                SET status = ? 
                WHERE id = ?
            """, (new_status, request_id))
        conn.commit()
        return c.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Error updating request: {e}")
        return False
    finally:
        conn.close()

def get_user_requests(requester_id, status_filter="All"):
    """Fetch all requests submitted by requester_id with optional status filtering."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = """
        SELECT 
            r.id, 
            r.resource_id, 
            COALESCE(res.title, 'Resource #' || r.resource_id) AS title, 
            COALESCE(res.category, 'General') AS category, 
            r.owner_id, 
            COALESCE(u.name, 'Unknown Owner') AS owner_name, 
            COALESCE(u.phone, 'N/A') AS owner_phone, 
            COALESCE(u.village, 'N/A') AS owner_village, 
            r.message, 
            r.status, 
            r.created_at,
            COALESCE(res.price, 'Free') AS price,
            r.start_date,
            r.end_date
        FROM requests r
        LEFT JOIN resources res ON r.resource_id = res.id
        LEFT JOIN users u ON r.owner_id = u.id
        WHERE r.requester_id = ?
    """
    params = [requester_id]
    if status_filter != "All":
        query += " AND r.status = ?"
        params.append(status_filter)
    query += " ORDER BY r.id DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def cancel_request(request_id, requester_id):
    """Cancel / remove a pending request submitted by the user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM requests WHERE id = ? AND requester_id = ? AND status = 'Pending'", (request_id, requester_id))
    conn.commit()
    conn.close()

# --- REVIEWS & RATINGS FUNCTIONS ---

def add_review(resource_id, reviewer_id, reviewer_name, rating, comment):
    """Add a review and rating for a resource."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO reviews (resource_id, reviewer_id, reviewer_name, rating, comment)
        VALUES (?, ?, ?, ?, ?)
    """, (resource_id, reviewer_id, reviewer_name, rating, comment))
    conn.commit()
    conn.close()

def get_resource_reviews(resource_id):
    """Fetch all reviews for a resource."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT reviewer_name, rating, comment, created_at
        FROM reviews
        WHERE resource_id = ?
        ORDER BY id DESC
    """, (resource_id,))
    reviews = c.fetchall()
    conn.close()
    return reviews

def get_resource_rating_summary(resource_id):
    """Return average rating and review count for a resource."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT AVG(rating), COUNT(rating)
        FROM reviews
        WHERE resource_id = ?
    """, (resource_id,))
    row = c.fetchone()
    conn.close()
    avg_rating = round(row[0], 1) if row and row[0] is not None else None
    count = row[1] if row else 0
    return avg_rating, count

# --- ANNOUNCEMENTS / NOTICE BOARD FUNCTIONS ---

def add_announcement(author_id, author_name, author_village, author_role, title, category, content):
    """Post a new village announcement."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO announcements (author_id, author_name, author_village, author_role, title, category, content)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (author_id, author_name, author_village, author_role, title, category, content))
    conn.commit()
    conn.close()

def get_announcements(category_filter="All"):
    """Fetch all village announcements."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = """
        SELECT id, author_id, author_name, author_village, author_role, title, category, content, created_at
        FROM announcements
    """
    params = []
    if category_filter != "All":
        query += " WHERE category = ?"
        params.append(category_filter)
    query += " ORDER BY id DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def delete_announcement(announcement_id, user_id, is_admin=False):
    """Delete an announcement (by author or admin)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if is_admin:
        c.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
    else:
        c.execute("DELETE FROM announcements WHERE id = ? AND author_id = ?", (announcement_id, user_id))
    conn.commit()
    success = c.rowcount > 0
    conn.close()
    return success

def delete_resource(resource_id):
    """Delete a resource listing from the database (Admin action)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
    conn.commit()
    conn.close()

def get_all_users():
    """Fetch all registered users for Admin panel."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, email, phone, village, role FROM users ORDER BY id DESC")
    users = c.fetchall()
    conn.close()
    return users

# Initialize database on app startup
init_db()

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "page" not in st.session_state:
    st.session_state.page = "Home"

if "user" not in st.session_state:
    st.session_state.user = None  # Holds logged-in user info

# --------------------------------------------------
# FUNCTIONS
# --------------------------------------------------

def go_to(page):
    st.session_state.page = page
    st.rerun()

def logout():
    st.session_state.user = None
    st.session_state.page = "Home"
    st.rerun()
# --------------------------------------------------
# CSS
# --------------------------------------------------

st.markdown("""
<style>

/* Main application background */
.stApp {
    background-color: #f5faf7;
}

/* Main content spacing */
.block-container {
    padding-top: 2rem !important;
    padding-left: 4% !important;
    padding-right: 4% !important;
    max-width: 100% !important;
}

/* Navbar */
.navbar {
    background-color: #0b5d3b;
    padding: 18px 24px;
    border-radius: 15px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    min-height: 65px;
    height: auto;
    box-sizing: border-box;
    overflow: visible;
}

/* Logo */
.logo {
    color: white;
    font-size: 26px;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 10px;
    white-space: nowrap;
}

/* Fix Streamlit navigation buttons */
.stButton {
    width: 100%;
    min-width: 0;
}

.stButton > button {
    width: 100% !important;
    min-height: 45px !important;
    height: auto !important;
    padding: 10px 8px !important;
    box-sizing: border-box !important;
    white-space: normal !important;
    overflow: visible !important;
    line-height: 1.4 !important;
    border-radius: 8px !important;
}

/* Keep button labels visible */
.stButton > button p {
    margin: 0 !important;
    line-height: 1.4 !important;
    white-space: normal !important;
    overflow-wrap: anywhere;
}

/* Button hover effect */
.stButton > button:hover {
    border-color: #0b5d3b !important;
    color: #0b5d3b !important;
}

/* Hero section */
.hero {
    background: linear-gradient(135deg, #075e3b, #198754);
    padding: 60px 30px;
    border-radius: 25px;
    text-align: center;
    color: white;
    margin-bottom: 25px;
}

.hero-title {
    font-size: 40px;
    font-weight: bold;
}

.hero-text {
    font-size: 18px;
    margin-top: 15px;
}

/* Cards */
.card {
    background-color: white;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #dce8df;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    margin-bottom: 15px;
    box-sizing: border-box;
}

/* Form box */
.form-box {
    background-color: white;
    padding: 25px;
    border-radius: 20px 20px 0 0;
    border: 1px solid #dce8df;
    border-bottom: none;
    box-shadow: 0 -5px 15px rgba(0,0,0,0.02);
    box-sizing: border-box;
}

.form-title {
    text-align: center;
    color: #0b5d3b;
    font-size: 30px;
    font-weight: bold;
}

.form-subtitle {
    text-align: center;
    color: #666;
    margin-bottom: 10px;
}

/* Section title */
.section-title {
    color: #145a32;
    font-size: 28px;
    font-weight: bold;
    margin-top: 25px;
    margin-bottom: 20px;
}

/* Footer */
.footer {
    background-color: #0b5d3b;
    color: white;
    padding: 25px;
    text-align: center;
    border-radius: 15px;
    margin-top: 50px;
}

/* Pending badge */
.status-badge-pending {
    background-color: #fff3cd;
    color: #856404;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
    display: inline-block;
    border: 1px solid #ffeeba;
}

/* Accepted badge */
.status-badge-accepted {
    background-color: #d4edda;
    color: #155724;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
    display: inline-block;
    border: 1px solid #c3e6cb;
}

/* Rejected badge */
.status-badge-rejected {
    background-color: #f8d7da;
    color: #721c24;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
    display: inline-block;
    border: 1px solid #f5c6cb;
}

/* Free price badge */
.price-badge-free {
    background-color: #e8f5e9;
    color: #2e7d32;
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: bold;
    border: 1px solid #c8e6c9;
    display: inline-block;
}

/* Paid price badge */
.price-badge-paid {
    background-color: #fff8e1;
    color: #b78103;
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: bold;
    border: 1px solid #ffe082;
    display: inline-block;
}

/* Rating badge */
.rating-badge {
    background-color: #fffde7;
    color: #f57f17;
    padding: 3px 8px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: bold;
    border: 1px solid #fff59d;
    display: inline-block;
}

/* Notice card */
.notice-card {
    background-color: white;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #dce8df;
    border-left: 5px solid #0b5d3b;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    margin-bottom: 15px;
    box-sizing: border-box;
}

</style>
""", unsafe_allow_html=True)
# ==================================================
# NAVBAR
# ==================================================

is_admin = st.session_state.user and st.session_state.user["role"] == "Admin"
if is_admin:
    nav1, nav2, nav3, nav4, nav5, nav6, nav7, nav8, nav9 = st.columns(
        [1.8, 0.7, 1.1, 1.2, 1.1, 1.2, 1.1, 1.0, 0.8]
    )
elif st.session_state.user:
    nav1, nav2, nav3, nav4, nav5, nav6, nav7, nav8 = st.columns(
        [2.0, 0.8, 1.2, 1.3, 1.2, 1.3, 1.2, 0.9]
    )
else:
    nav1, nav2, nav3, nav4, nav5, nav6 = st.columns(
        [2.3, 0.9, 1.3, 1.4, 1.1, 1.1]
    )

with nav1:
  st.markdown(
    '<div class="navbar">'
    '<div class="logo">🌾 Smart Village</div>'
    '</div>',
    unsafe_allow_html=True
)

with nav2:
    if st.button("🏠 Home", use_container_width=True, key="nav_home"):
        go_to("Home")

with nav3:
    if st.button("🛒 Marketplace", use_container_width=True, key="nav_market"):
        go_to("Marketplace")

with nav4:
    if st.button("📢 Notice Board", use_container_width=True, key="nav_notice"):
        go_to("Notice Board")

if is_admin:
    with nav5:
        if st.button("📋 My Requests", use_container_width=True, key="nav_my_req"):
            go_to("My Requests")
    with nav6:
        if st.button("📥 Manage Requests", use_container_width=True, key="nav_manage_req"):
            go_to("Manage Requests")
    with nav7:
        if st.button("🛡️ Admin Panel", use_container_width=True, key="nav_admin"):
            go_to("Admin")
    with nav8:
        st.write(f"👑 **{st.session_state.user['name']}**")
    with nav9:
        if st.button("🚪 Logout", use_container_width=True, key="nav_logout"):
            logout()
elif st.session_state.user:
    with nav5:
        if st.button("📋 My Requests", use_container_width=True, key="nav_my_req"):
            go_to("My Requests")
    with nav6:
        if st.button("📥 Manage Requests", use_container_width=True, key="nav_manage_req"):
            go_to("Manage Requests")
    with nav7:
        st.write(f"👋 **{st.session_state.user['name']}**")
    with nav8:
        if st.button("🚪 Logout", use_container_width=True, key="nav_logout"):
            logout()
else:
    with nav5:
        if st.button("🔐 Login", use_container_width=True, key="nav_login"):
            go_to("Login")
    with nav6:
        if st.button("📝 Register", use_container_width=True, key="nav_register"):
            go_to("Register")


# ==================================================
# HOME PAGE
# ==================================================

if st.session_state.page == "Home":

    if st.session_state.user:
        st.success(f"Welcome back, **{st.session_state.user['name']}**! (Village: {st.session_state.user['village']} | Role: {st.session_state.user['role']})")

    st.markdown("""
    <div class="hero">
        <div class="hero-title">
            Smart Village Resource Sharing Portal
        </div>
        <div class="hero-text">
            Connect with your community, share useful resources, and easily find what you need.
        </div>
    </div>
    """, unsafe_allow_html=True)

    

    # About
    st.markdown('<div class="section-title">🌱 About Our Portal</div>', unsafe_allow_html=True)
    st.write(
        "Smart Village Resource Sharing Portal is a community-based platform that allows villagers "
        "to share and access useful resources such as farming equipment, vehicles, books, and tools."
    )

    # Resources
    st.markdown('<div class="section-title">📦 Resources You Can Share</div>', unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <h2>🚜</h2>
            <h3>Farming</h3>
            <p>Tractors, pumps, and farming equipment.</p>
        </div>
        """, unsafe_allow_html=True)

    with r2:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <h2>🚗</h2>
            <h3>Vehicles</h3>
            <p>Vehicles and transportation resources.</p>
        </div>
        """, unsafe_allow_html=True)

    with r3:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <h2>📚</h2>
            <h3>Books</h3>
            <p>Educational books and study materials.</p>
        </div>
        """, unsafe_allow_html=True)

    with r4:
        st.markdown("""
        <div class="card" style="text-align: center;">
            <h2>🔧</h2>
            <h3>Tools</h3>
            <p>Tools and equipment for community sharing.</p>
        </div>
        """, unsafe_allow_html=True)

    # How it works
    st.markdown('<div class="section-title">⚙️ How It Works</div>', unsafe_allow_html=True)
    h1, h2, h3, h4 = st.columns(4)

    with h1:
        st.info("👤 **1. Register**\n\nCreate your account.")
    with h2:
        st.info("🔎 **2. Search**\n\nFind a resource.")
    with h3:
        st.info("📩 **3. Request**\n\nSend a request.")
    with h4:
        st.info("🤝 **4. Share**\n\nGet the resource.")


# ==================================================
# MARKETPLACE PAGE
# ==================================================

elif st.session_state.page == "Marketplace":

    st.markdown('<div class="section-title">🛒 Resource Marketplace</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔎 Browse Resources", "➕ Add New Listing", "📦 My Listings"])

    # --- TAB 1: BROWSE RESOURCES ---
    with tab1:
        st.subheader("Available Community Resources")

        # Search Bar
        search_kw = st.text_input("🔍 Search by title, keyword or description", placeholder="e.g. Tractor, Water Pump, Fertilizer, Books...", key="search_bar")

        # Filters
        f1, f2, f3, f4 = st.columns([1.5, 1.5, 1.2, 1.2])
        with f1:
            category_filter = st.selectbox("Category", ["All", "Farming", "Vehicles", "Books", "Tools", "Other"], key="filter_cat")
        with f2:
            village_filter = st.text_input("Village Location", placeholder="Leave blank for all", key="filter_vil")
        with f3:
            avail_filter = st.selectbox("Availability", ["All", "Available", "In Use"], key="filter_avail")
        with f4:
            price_filter = st.selectbox("Pricing", ["All", "Free Only", "Paid Only"], key="filter_price")

        selected_village = village_filter.strip() if village_filter.strip() else "All"
        resources = get_resources(
            category_filter=category_filter,
            village_filter=selected_village,
            search_keyword=search_kw,
            availability_filter=avail_filter,
            price_filter=price_filter
        )

        st.write("")

        if not resources:
            st.info("No resources match your search and filter criteria.")
        else:
            st.caption(f"Showing **{len(resources)}** resource(s)")
            for item in resources:
                item_id, title, category, village, desc, owner_name, owner_phone, status, owner_id, price = item
                avg_rating, count_reviews = get_resource_rating_summary(item_id)

                price_badge = '<span class="price-badge-free">💰 Free</span>' if price.lower() == "free" else f'<span class="price-badge-paid">💰 {price}</span>'
                rating_badge = f'<span class="rating-badge">⭐ {avg_rating} ({count_reviews} reviews)</span>' if avg_rating else '<span class="rating-badge">⭐ New (No reviews)</span>'
                status_color = "#198754" if status == "Available" else "#e67e22"

                with st.container():
                    st.markdown(f"""
                    <div class="card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <h3 style="margin: 0; color: #0b5d3b;">📦 {title} <span style="font-size:14px; color:{status_color}; font-weight:600;">({status})</span></h3>
                                <p style="margin: 5px 0 0 0; color: #555;"><strong>Category:</strong> {category} | <strong>Village:</strong> {village}</p>
                            </div>
                            <div style="display: flex; gap: 8px; align-items: center;">
                                {price_badge}
                                {rating_badge}
                            </div>
                        </div>
                        <p style="margin-top: 12px; margin-bottom: 8px;">{desc}</p>
                        <p style="margin: 0; font-size: 14px; color: #444;"><strong>Owner:</strong> {owner_name}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Reviews expander
                    reviews = get_resource_reviews(item_id)
                    if reviews:
                        with st.expander(f"💬 Community Reviews ({len(reviews)})"):
                            for r_name, r_rating, r_comment, r_date in reviews:
                                st.markdown(f"**{'⭐' * r_rating}** by *{r_name}* <span style='font-size:12px; color:#888;'>({r_date})</span>", unsafe_allow_html=True)
                                if r_comment:
                                    st.write(f'"{r_comment}"')
                                st.write("---")

                    c_btn1, c_btn2 = st.columns([2, 2])

                    with c_btn1:
                        if st.session_state.user:
                            if st.button(
                                f"📞 Contact Owner ({owner_name})",
                                key=f"contact_{item_id}"
                            ):
                                st.success(f"Contact Phone: **{owner_phone}**")

                    with c_btn2:
                        if st.session_state.user:
                            current_user = st.session_state.user

                            if current_user["id"] != owner_id:
                                with st.form(key=f"request_form_{item_id}"):
                                    st.write("📅 **Select Borrowing Duration:**")
                                    col_d1, col_d2 = st.columns(2)
                                    with col_d1:
                                        start_d = st.date_input("From Date", value=datetime.date.today(), key=f"req_s_{item_id}")
                                    with col_d2:
                                        end_d = st.date_input("To Date", value=datetime.date.today() + datetime.timedelta(days=1), key=f"req_e_{item_id}")

                                    message = st.text_input(
                                        "Message to owner (optional)",
                                        key=f"message_{item_id}"
                                    )

                                    submitted = st.form_submit_button(
                                        "📩 Request Resource"
                                    )

                                    if submitted:
                                        if start_d > end_d:
                                            st.error("Return date must be on or after start date.")
                                        else:
                                            if submit_resource_request(
                                                resource_id=item_id,
                                                owner_id=owner_id,
                                                requester_id=current_user["id"],
                                                message=message,
                                                start_date=str(start_d),
                                                end_date=str(end_d)
                                            ):
                                                st.success("Request submitted successfully! Status: Pending")
                            else:
                                st.caption("ℹ️ You own this listing")
                        else:
                            st.info("Please log in to request a resource.")
                    st.write("---")

    # --- TAB 2: ADD NEW LISTING ---
    with tab2:
        if not st.session_state.user:
            st.warning("🔒 You must be logged in to list a resource.")
            if st.button("🔐 Go to Login", key="mkt_login_redirect"):
                go_to("Login")
        else:
            st.subheader("Post a Resource for Community Sharing")

            with st.form("add_resource_form"):
                title = st.text_input("Resource Name / Title", placeholder="e.g. Water Pump 5HP / John Deere Tractor")
                category = st.selectbox("Category", ["Farming", "Vehicles", "Books", "Tools", "Other"])
                village = st.text_input("Village Location", value=st.session_state.user["village"])

                p_col1, p_col2 = st.columns([1, 1])
                with p_col1:
                    price_type = st.selectbox("Pricing Option", ["Free (Community Sharing)", "Paid / Rental Fee"])
                with p_col2:
                    rental_fee = st.text_input("Rental Rate (if paid)", placeholder="e.g. ₹500 / day or ₹100 / hr")

                description = st.text_area("Description / Conditions", placeholder="Describe the item condition, availability terms, etc.")

                submit_item = st.form_submit_button("🚀 Post Listing", use_container_width=True)

                if submit_item:
                    if not title or not description or not village:
                        st.error("Please fill in all required fields.")
                    else:
                        price_val = "Free" if "Free" in price_type else (rental_fee.strip() if rental_fee.strip() else "Paid")
                        add_resource(
                            owner_id=st.session_state.user["id"],
                            owner_name=st.session_state.user["name"],
                            owner_phone=st.session_state.user["phone"],
                            title=title,
                            category=category,
                            village=village,
                            description=description,
                            price=price_val
                        )
                        st.success(f"🎉 '{title}' has been listed successfully!")

    # --- TAB 3: MY LISTINGS (OWNER MANAGER) ---
    with tab3:
        if not st.session_state.user:
            st.warning("🔒 You must be logged in to manage your listings.")
            if st.button("🔐 Go to Login", key="mkt_my_list_login"):
                go_to("Login")
        else:
            st.subheader("Manage Your Listed Resources")
            owner_items = get_owner_resources(st.session_state.user["id"])

            if not owner_items:
                st.info("You haven't posted any resources yet. Use the '➕ Add New Listing' tab to list your equipment!")
            else:
                st.write(f"You have **{len(owner_items)}** listing(s):")
                for o_item in owner_items:
                    res_id, r_title, r_cat, r_vil, r_desc, r_stat, r_price, r_date = o_item
                    status_col = "#198754" if r_stat == "Available" else "#e67e22"

                    with st.container():
                        st.markdown(f"""
                        <div class="card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin: 0; color: #0b5d3b;">📦 {r_title} <span style="font-size:14px; color:{status_col}; font-weight:600;">({r_stat})</span></h3>
                                <span class="price-badge-free" style="background:#eef6f0;">💰 {r_price}</span>
                            </div>
                            <p style="margin: 5px 0 0 0; color: #666;"><strong>Category:</strong> {r_cat} | <strong>Village:</strong> {r_vil}</p>
                            <p style="margin-top: 8px;">{r_desc}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        btn_c1, btn_c2, btn_c3 = st.columns([2, 1, 1])

                        with btn_c1:
                            toggle_label = "Mark as In Use" if r_stat == "Available" else "Mark as Available"
                            if st.button(f"🔄 {toggle_label}", key=f"toggle_stat_{res_id}", use_container_width=True):
                                toggle_resource_availability(res_id, st.session_state.user["id"])
                                st.rerun()

                        with btn_c2:
                            with st.popover("✏️ Edit", use_container_width=True):
                                with st.form(key=f"edit_form_{res_id}"):
                                    new_t = st.text_input("Title", value=r_title)
                                    new_cat = st.selectbox("Category", ["Farming", "Vehicles", "Books", "Tools", "Other"], index=["Farming", "Vehicles", "Books", "Tools", "Other"].index(r_cat) if r_cat in ["Farming", "Vehicles", "Books", "Tools", "Other"] else 0)
                                    new_vil = st.text_input("Village", value=r_vil)
                                    new_pr = st.text_input("Price / Rate", value=r_price)
                                    new_st = st.selectbox("Status", ["Available", "In Use"], index=0 if r_stat == "Available" else 1)
                                    new_desc = st.text_area("Description", value=r_desc)
                                    save_btn = st.form_submit_button("💾 Save Changes")

                                    if save_btn:
                                        update_resource(res_id, st.session_state.user["id"], new_t, new_cat, new_vil, new_desc, new_pr, new_st)
                                        st.success("Listing updated successfully!")
                                        st.rerun()

                        with btn_c3:
                            if st.button("🗑️ Delete", key=f"del_owner_res_{res_id}", use_container_width=True):
                                delete_owner_resource(res_id, st.session_state.user["id"])
                                st.warning("Listing deleted.")
                                st.rerun()

                        st.write("---")


# ==================================================
# MY REQUESTS PAGE
# ==================================================

elif st.session_state.page == "My Requests":

    if not st.session_state.user:
        st.warning("🔒 You must be logged in to view your submitted requests.")

        if st.button("🔐 Go to Login", key="my_req_login_redirect"):
            go_to("Login")

    else:
        st.title("📋 My Requests")
        st.write(
            "Track the status of resources you have requested "
            "from fellow villagers."
        )

        _, top_col2 = st.columns([3, 1])

        with top_col2:
            if st.button(
                "📥 Switch to Incoming Requests",
                key="btn_to_manage_req",
                use_container_width=True
            ):
                go_to("Manage Requests")

        user_id = st.session_state.user["id"]
        my_requests = get_user_requests(user_id)

        total_my = len(my_requests)
        pending_my = sum(1 for r in my_requests if r[9] == "Pending")
        accepted_my = sum(1 for r in my_requests if r[9] == "Accepted")
        rejected_my = sum(1 for r in my_requests if r[9] == "Rejected")

        # Request summary
        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Total Submitted", total_my)
        m2.metric("⏳ Pending", pending_my)
        m3.metric("✅ Accepted", accepted_my)
        m4.metric("❌ Rejected", rejected_my)

        st.write("")

        # Request status tabs
        tab_my_all, tab_my_pend, tab_my_acc, tab_my_rej = st.tabs([
    f"All ({total_my})",
    f"⏳ Pending ({pending_my})",
    f"✅ Accepted ({accepted_my})",
    f"❌ Rejected ({rejected_my})"
])
        def display_my_requests(
    req_list,
    show_empty_msg="No requests found in this category.",
    tab_key="all"
):

            if not req_list:
                st.info(show_empty_msg)
                return

            for req in req_list:

                (
                    req_id, res_id, title, category, owner_id,
                    owner_name, owner_phone, owner_village, msg,
                    status, created_at, price, start_date, end_date
                ) = req

                # Request card using only Streamlit components
                with st.container(border=True):

                    st.subheader(f"📦 {title}")
                    st.caption(f"Category: {category}")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Owner:** {owner_name}")
                        st.write(f"**Village:** {owner_village}")

                    with col2:
                        price = str(price or "Free")

                        if price.lower() == "free":
                            st.success("💰 Free")
                        else:
                            st.info(f"💰 {price}")

                        if status == "Pending":
                            st.warning("⏳ Pending")
                        elif status == "Accepted":
                            st.success("✅ Accepted")
                        elif status == "Rejected":
                            st.error("❌ Rejected")

                    if start_date and end_date:
                        st.write("**📅 Borrowing Period**")
                        st.write(f"{start_date} to {end_date}")

                    # Display the request message
                    st.write("**Your Message:**")

                    if msg:
                        # Remove old HTML tags saved in the database
                        import re
                        import html

                        clean_msg = re.sub(
                            r"<br\s*/?>",
                            "\n",
                            str(msg),
                            flags=re.IGNORECASE
                        )
                        clean_msg = re.sub(
                            r"</p\s*>",
                            "\n",
                            clean_msg,
                            flags=re.IGNORECASE
                        )
                        clean_msg = re.sub(
                            r"<[^>]+>",
                            "",
                            clean_msg
                        )
                        clean_msg = html.unescape(clean_msg).strip()

                        st.write(clean_msg)
                    else:
                        st.write("None")

                    st.caption(f"Request date: {created_at}")

                    st.divider()

                    # Accepted request actions
                    if status == "Accepted":

                        st.success(
                            f"🎉 Request accepted! Contact "
                            f"{owner_name} at {owner_phone} "
                            f"to coordinate."
                        )

                        with st.expander("⭐ Leave a Rating & Review"):

                            with st.form(key=f"rev_form_{req_id}_{tab_key}"):

                                rating_val = st.slider(
                                    "Rating (1 to 5 stars)",
                                    min_value=1,
                                    max_value=5,
                                    value=5,
                                   key=f"slider_{req_id}_{tab_key}"
                                )

                                comment_val = st.text_area(
                                    "Your Review / Experience",
                                    placeholder=(
                                        "Describe how useful the "
                                        "resource was..."
                                    ),
                                    key=f"rev_txt_{req_id}_{tab_key}"
                                )

                                submitted = st.form_submit_button(
                                    "⭐ Submit Review"
                                )

                                if submitted:
                                    add_review(
                                        res_id,
                                        user_id,
                                        st.session_state.user["name"],
                                        rating_val,
                                        comment_val
                                    )

                                    st.success(
                                        "Thank you! Your review has been recorded."
                                    )
                                    st.rerun()

                    # Pending request actions
                    elif status == "Pending":

                        st.info(
                            "⏳ Your request is awaiting "
                            "the owner's review."
                        )

                        if st.button(
    "Cancel Request",
    key=f"btn_cancel_req_{req_id}_{tab_key}"
):
                            cancel_request(req_id, user_id)
                            st.success("Request cancelled.")
                            st.rerun()

                    # Rejected request information
                    elif status == "Rejected":
                        st.error(
                            "The owner is currently unable "
                            "to share this resource."
                        )

        # All requests
        with tab_my_all:
            display_my_requests(
                my_requests,
                "You haven't made any resource requests yet.",
                tab_key="all"
            )

        with tab_my_pend:
            display_my_requests(
                [r for r in my_requests if r[9] == "Pending"],
                "No pending requests.",
                tab_key="pending"
            )

        with tab_my_acc:
            display_my_requests(
                [r for r in my_requests if r[9] == "Accepted"],
                "No accepted requests yet.",
                tab_key="accepted"
            )

        with tab_my_rej:
            display_my_requests(
                [r for r in my_requests if r[9] == "Rejected"],
                "No rejected requests.",
                tab_key="rejected"
            )

# ==================================================
# OWNER-SIDE REQUEST MANAGEMENT PAGE
# ==================================================

elif st.session_state.page == "Manage Requests":

    if not st.session_state.user:
        st.warning("🔒 You must be logged in to manage incoming requests.")
        if st.button("🔐 Go to Login", key="manage_req_login_redirect"):
            go_to("Login")
    else:
        st.markdown('<div class="section-title">📥 Manage Resource Requests</div>', unsafe_allow_html=True)
        st.write("Review and respond to incoming requests from villagers for your resources.")

        top_col1, top_col2 = st.columns([3, 1])
        with top_col2:
            if st.button("📋 Switch to My Requests", key="btn_to_my_req", use_container_width=True):
                go_to("My Requests")

        owner_id = st.session_state.user["id"]
        incoming = get_owner_requests(owner_id)

        total_inc = len(incoming)
        pending_inc = sum(1 for r in incoming if r[9] == "Pending")
        accepted_inc = sum(1 for r in incoming if r[9] == "Accepted")
        rejected_inc = sum(1 for r in incoming if r[9] == "Rejected")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Received", total_inc)
        m2.metric("⏳ Pending Action", pending_inc)
        m3.metric("✅ Accepted", accepted_inc)
        m4.metric("❌ Rejected", rejected_inc)

        st.write("")

        tab_inc_all, tab_inc_pend, tab_inc_acc, tab_inc_rej = st.tabs([
            f"All ({total_inc})",
            f"⏳ Pending Action ({pending_inc})",
            f"✅ Accepted ({accepted_inc})",
            f"❌ Rejected ({rejected_inc})"
        ])

        def display_owner_requests(req_list, show_empty_msg="No incoming requests in this category.", tab_key="all"):
            if not req_list:
                st.info(show_empty_msg)
                return

            for req in req_list:
                req_id, res_id, title, category, requester_id, requester_name, requester_phone, requester_village, msg, status, created_at, price, start_date, end_date = req

                if status == "Accepted":
                    badge_html = '<span class="status-badge-accepted">✅ Accepted</span>'
                elif status == "Rejected":
                    badge_html = '<span class="status-badge-rejected">❌ Rejected</span>'
                else:
                    badge_html = '<span class="status-badge-pending">⏳ Pending Review</span>'

                price_html = '<span class="price-badge-free">💰 Free</span>' if price.lower() == "free" else f'<span class="price-badge-paid">💰 {price}</span>'

                with st.container():
                    st.markdown(f"""
                    <div class="card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin: 0; color: #0b5d3b;">📦 {title} <span style="font-size:14px; color:#555; font-weight:normal;">({category})</span></h3>
                            <div style="display: flex; gap: 8px; align-items: center;">
                                {price_html}
                                {badge_html}
                            </div>
                        </div>
                        <p style="margin-top: 10px; margin-bottom: 5px;"><strong>Requester:</strong> {requester_name} (Village: {requester_village})</p>
                        <p style="margin-bottom: 5px;"><strong>Requester Phone:</strong> 📞 {requester_phone}</p>
                        {f'<p style="margin-bottom: 5px;"><strong>📅 Requested Duration:</strong> {start_date} to {end_date}</p>' if start_date and end_date else ''}
                        <p style="margin-bottom: 5px;"><strong>Message:</strong> {msg if msg else '<em>None</em>'}</p>
                        <p style="font-size: 13px; color: #777; margin-bottom: 0;"><strong>Date:</strong> {created_at}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    if status == "Pending":
                        b1, b2, b_space = st.columns([1, 1, 3])
                        with b1:
                            if st.button("✅ Accept", key=f"btn_accept_{req_id}_{tab_key}", type="primary", use_container_width=True):
                                if update_request_status(req_id, "Accepted", owner_id):
                                    st.success(f"Accepted request from {requester_name} for '{title}'!")
                                    st.rerun()
                                else:
                                    st.error("Failed to update status.")
                        with b2:
                            if st.button("❌ Reject", key=f"btn_reject_{req_id}_{tab_key}", use_container_width=True):
                                if update_request_status(req_id, "Rejected", owner_id):
                                    st.warning(f"Rejected request from {requester_name} for '{title}'.")
                                    st.rerun()
                                else:
                                    st.error("Failed to update status.")
                    elif status == "Accepted":
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.success(f"✅ You accepted this request. Contact {requester_name} at 📞 **{requester_phone}**.")
                        with c2:
                            if st.button("Change to Reject", key=f"btn_re_rej_{req_id}_{tab_key}", use_container_width=True):
                                update_request_status(req_id, "Rejected", owner_id)
                                st.rerun()
                    elif status == "Rejected":
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.error("❌ You rejected this request.")
                        with c2:
                            if st.button("Change to Accept", key=f"btn_re_acc_{req_id}_{tab_key}", use_container_width=True):
                                update_request_status(req_id, "Accepted", owner_id)
                                st.rerun()

                    st.write("---")

        with tab_inc_all:
            display_owner_requests(incoming, "No incoming requests for your resources.", tab_key="all")

        with tab_inc_pend:
            display_owner_requests([r for r in incoming if r[9] == "Pending"], "No requests pending your review.", tab_key="pending")

        with tab_inc_acc:
            display_owner_requests([r for r in incoming if r[9] == "Accepted"], "No accepted requests.", tab_key="accepted")

        with tab_inc_rej:
            display_owner_requests([r for r in incoming if r[9] == "Rejected"], "No rejected requests.", tab_key="rejected")


# ==================================================
# NOTICE BOARD / VILLAGE ANNOUNCEMENTS
# ==================================================

elif st.session_state.page == "Notice Board":

    st.markdown('<div class="section-title">📢 Village Notice Board</div>', unsafe_allow_html=True)
    st.write("Stay connected with community notices, urgent requests, and farming advisories.")

    notice_tab1, notice_tab2 = st.tabs(["📋 View Announcements", "✍️ Post New Announcement"])

    with notice_tab1:
        n_filter = st.selectbox(
            "Filter by Category",
            ["All", "General", "Urgent Request", "Farming Alert", "Community Event"],
            key="notice_cat_filter"
        )

        all_notices = get_announcements(n_filter)

        if not all_notices:
            st.info("No notices currently posted in this category.")
        else:
            st.caption(f"Showing **{len(all_notices)}** notice(s)")
            for notice in all_notices:
                n_id, a_id, a_name, a_vil, a_role, n_title, n_cat, n_content, n_date = notice
                is_author = st.session_state.user and (st.session_state.user["id"] == a_id or st.session_state.user["role"] == "Admin")

                cat_color = "#dc3545" if "Urgent" in n_cat else ("#28a745" if "Farming" in n_cat else "#0b5d3b")

                with st.container():
                    st.markdown(f"""
                    <div class="notice-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <h3 style="margin: 0; color: {cat_color};">📌 {n_title}</h3>
                            <span style="background: #eef2f0; color: #333; padding: 3px 10px; border-radius: 10px; font-size: 13px; font-weight: 600;">{n_cat}</span>
                        </div>
                        <p style="font-size: 15px; color: #222; margin-bottom: 12px; line-height: 1.5;">{n_content}</p>
                        <p style="font-size: 13px; color: #777; margin: 0;">
                            Posted by <strong>{a_name}</strong> ({a_vil}) [{a_role}] • <em>{n_date}</em>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    if is_author:
                        if st.button("🗑️ Delete Notice", key=f"del_notice_{n_id}", type="secondary"):
                            delete_announcement(n_id, st.session_state.user["id"], is_admin=(st.session_state.user["role"] == "Admin"))
                            st.warning("Notice deleted.")
                            st.rerun()

                    st.write("---")

    with notice_tab2:
        if not st.session_state.user:
            st.warning("🔒 You must be logged in to post an announcement.")
            if st.button("🔐 Go to Login", key="notice_login_redirect"):
                go_to("Login")
        else:
            st.subheader("Share an Announcement with the Village")
            with st.form("new_notice_form"):
                new_n_title = st.text_input("Notice Title", placeholder="e.g. Free Soil Testing Camp / Harvester Required Urgently")
                new_n_cat = st.selectbox(
                    "Notice Category",
                    ["General", "Urgent Request", "Farming Alert", "Community Event"]
                )
                new_n_content = st.text_area("Message / Content", placeholder="Provide complete details, dates, or contact info for fellow villagers...")
                post_notice_btn = st.form_submit_button("📢 Publish Announcement", use_container_width=True)

                if post_notice_btn:
                    if not new_n_title or not new_n_content:
                        st.error("Please enter both title and content.")
                    else:
                        add_announcement(
                            author_id=st.session_state.user["id"],
                            author_name=st.session_state.user["name"],
                            author_village=st.session_state.user["village"],
                            author_role=st.session_state.user["role"],
                            title=new_n_title,
                            category=new_n_cat,
                            content=new_n_content
                        )
                        st.success("🎉 Announcement published successfully!")
                        st.rerun()


# ==================================================
# ADMIN DASHBOARD PAGE
# ==================================================

elif st.session_state.page == "Admin":

    if not is_admin:
        st.error("🚨 Access Denied! You must be logged in as an Admin to view this page.")
    else:
        st.markdown('<div class="section-title">🛡️ Admin Dashboard</div>', unsafe_allow_html=True)

        admin_tab1, admin_tab2 = st.tabs(["👥 Registered Accounts", "🗑️ Manage Resource Listings"])

        # --- ADMIN TAB 1: USER ACCOUNTS ---
        with admin_tab1:
            st.subheader("All Registered Users")
            all_users = get_all_users()

            if not all_users:
                st.info("No registered users found.")
            else:
                user_data = []
                for u in all_users:
                    user_data.append({
                        "ID": u[0],
                        "Name": u[1],
                        "Email": u[2],
                        "Phone": u[3],
                        "Village": u[4],
                        "Role": u[5]
                    })
                st.dataframe(user_data, use_container_width=True)

        # --- ADMIN TAB 2: MANAGE LISTINGS ---
        with admin_tab2:
            st.subheader("Active Resource Listings Moderation")
            all_listings = get_resources()

            if not all_listings:
                st.info("No listings available in database.")
            else:
                for item in all_listings:
                    item_id, title, category, village, desc, owner_name, owner_phone, status, owner_id, price = item
                    with st.container():
                        col_info, col_act = st.columns([4, 1])
                        with col_info:
                            st.markdown(f"**[{category}] {title}** — Posted by *{owner_name}* ({village}) • 💰 **{price}** ({status})")
                            st.caption(f"Details: {desc}")
                        with col_act:
                            if st.button("🗑️ Delete", key=f"admin_del_{item_id}", type="primary"):
                                delete_resource(item_id)
                                st.success(f"Listing '{title}' deleted successfully!")
                                st.rerun()
                        st.write("---")


# ==================================================
# LOGIN PAGE
# ==================================================

elif st.session_state.page == "Login":

    left, middle, right = st.columns([1, 2, 1])

    with middle:
        st.markdown("""
        <style>
       /*Improve top navigation visibility*/ 
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    justify-content: center;
    flex-wrap: wrap;
}

/* Make navigation labels clearer */
.stTabs [data-baseweb="tab"] {
    color: #1b4332 !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    padding: 12px 18px !important;
}

/* Highlight the selected navigation tab */
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    background-color: #2d6a4f !important;
    border-radius: 8px !important;
}

/* Improve contrast when hovering */
.stTabs [data-baseweb="tab"]:hover {
    color: #ffffff !important;
    background-color: #40916c !important;
}

/* Improve metric labels and values */
[data-testid="stMetricLabel"] {
    font-size: 16px !important;
    font-weight: 600 !important;
}

[data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: bold !important;
}
       </style> 
       """, unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email Address", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit = st.form_submit_button("🔐 Login", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    user = authenticate_user(email, password)
                    if user:
                        st.session_state.user = {
                            "id": user[0],
                            "name": user[1],
                            "email": user[2],
                            "phone": user[3],
                            "role": user[4],
                            "village": user[5]
                        }
                        st.success(f"Welcome back, {user[1]}! 🎉")
                        go_to("Marketplace")
                    else:
                        st.error("Invalid email or password.")

        st.write("")
        st.write("Don't have an account?")
        if st.button("Create New Account", use_container_width=True, key="go_to_reg"):
            go_to("Register")


# ==================================================
# REGISTER PAGE
# ==================================================

elif st.session_state.page == "Register":

    left, middle, right = st.columns([1, 2, 1])

    with middle:
        st.markdown("""
        <div class="form-box">
            <div class="form-title">📝 Create Account</div>
            <div class="form-subtitle">Join the Smart Village community</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("register_form"):
            name = st.text_input("Full Name", placeholder="Enter your full name")
            email = st.text_input("Email Address", placeholder="Enter your email")
            phone = st.text_input("Phone Number", placeholder="Enter your phone number")
            village = st.text_input("Village", placeholder="Enter your village")
            password = st.text_input("Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            role = st.selectbox("Register As", ["User", "Admin"])
            agree = st.checkbox("I agree to the terms and conditions")

            submit = st.form_submit_button("📝 Create Account", use_container_width=True)

            if submit:
                if not name:
                    st.error("Please enter your name.")
                elif not email:
                    st.error("Please enter your email.")
                elif not phone:
                    st.error("Please enter your phone number.")
                elif not village:
                    st.error("Please enter your village.")
                elif not password:
                    st.error("Please create a password.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                elif not agree:
                    st.error("Please agree to the terms and conditions.")
                else:
                    success, message = register_user(name, email, phone, village, password, role)
                    if success:
                        st.success(message)
                        go_to("Login")
                    else:
                        st.error(message)

        st.write("")
        st.write("Already have an account?")
        if st.button("🔐 Login Here", use_container_width=True, key="go_to_login"):
            go_to("Login")


# ==================================================
# FOOTER
# ==================================================

st.markdown("""
<div class="footer">
    <h3>🌾 Smart Village Resource Sharing Portal</h3>
    <p>Building stronger communities through technology and resource sharing.</p>
    <p>© 2026 Smart Village</p>
</div>
""", unsafe_allow_html=True)