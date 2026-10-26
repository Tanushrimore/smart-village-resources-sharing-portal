import streamlit as st
import sqlite3
import hashlib

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
    """Create the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
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
        SELECT id, name, email, role, village FROM users 
        WHERE email = ? AND password = ?
    ''', (email.lower().strip(), hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user

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

.stApp {
    background-color: #f5faf7;
}

.block-container {
    padding-top: 1.5rem;
    padding-left: 7%;
    padding-right: 7%;
}

/* Navbar */
.navbar {
    background-color: #0b5d3b;
    padding: 18px 30px;
    border-radius: 15px;
    margin-bottom: 20px;
}

.logo {
    color: white;
    font-size: 26px;
    font-weight: bold;
}

/* Hero */
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
    padding: 25px;
    border-radius: 18px;
    border: 1px solid #dce8df;
    min-height: 180px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    text-align: center;
}

/* Login/Register box */
.form-box {
    background-color: white;
    padding: 25px;
    border-radius: 20px 20px 0 0;
    border: 1px solid #dce8df;
    border-bottom: none;
    box-shadow: 0 -5px 15px rgba(0,0,0,0.02);
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

/* Section */
.section-title {
    color: #145a32;
    font-size: 28px;
    font-weight: bold;
    margin-top: 35px;
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

</style>
""", unsafe_allow_html=True)


# ==================================================
# NAVBAR
# ==================================================

nav1, nav2, nav3, nav4 = st.columns([4, 1.2, 1.2, 1.2])

with nav1:
    st.markdown(
        '<div class="navbar"><div class="logo">🌾 Smart Village</div></div>',
        unsafe_allow_html=True
    )

with nav2:
    if st.button("🏠 Home", use_container_width=True, key="nav_home"):
        go_to("Home")

if st.session_state.user:
    with nav3:
        st.write(f"👋 Hi, **{st.session_state.user['name']}**")
    with nav4:
        if st.button("🚪 Logout", use_container_width=True, key="nav_logout"):
            logout()
else:
    with nav3:
        if st.button("🔐 Login", use_container_width=True, key="nav_login"):
            go_to("Login")
    with nav4:
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

    if not st.session_state.user:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        with c2:
            if st.button("🔐 Login", use_container_width=True, key="hero_login"):
                go_to("Login")
        with c3:
            if st.button("📝 Register", use_container_width=True, key="hero_register"):
                go_to("Register")

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
        <div class="card">
            <h2>🚜</h2>
            <h3>Farming</h3>
            <p>Tractors, pumps, and farming equipment.</p>
        </div>
        """, unsafe_allow_html=True)

    with r2:
        st.markdown("""
        <div class="card">
            <h2>🚗</h2>
            <h3>Vehicles</h3>
            <p>Vehicles and transportation resources.</p>
        </div>
        """, unsafe_allow_html=True)

    with r3:
        st.markdown("""
        <div class="card">
            <h2>📚</h2>
            <h3>Books</h3>
            <p>Educational books and study materials.</p>
        </div>
        """, unsafe_allow_html=True)

    with r4:
        st.markdown("""
        <div class="card">
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
# LOGIN PAGE
# ==================================================

elif st.session_state.page == "Login":

    left, middle, right = st.columns([1, 2, 1])

    with middle:
        st.markdown("""
        <div class="form-box">
            <div class="form-title">🔐 Login</div>
            <div class="form-subtitle">Login to your Smart Village account</div>
        </div>
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
                            "role": user[3],
                            "village": user[4]
                        }
                        st.success(f"Welcome back, {user[1]}! 🎉")
                        go_to("Home")
                    else:
                        st.error("Invalid email or password.")

        st.write("")
        st.write("Don't have an account?")
        if st.button("Create New Account", use_container_width=True, key="go_to_reg"):
            go_to("Register")


# ==================================================
# REGISTER PAGE
# ==================================================
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
