import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g, session

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "blood_donation.db")

# ---------------- DATABASE SETUP ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    # Users table handles both Donors & Requesters now
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        age INTEGER,
        blood_group TEXT,
        contact TEXT,
        city TEXT,
        role TEXT DEFAULT 'Requester' 
    );

    CREATE TABLE IF NOT EXISTS emergency_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        blood_group TEXT,
        units_needed TEXT,
        hospital TEXT,
        contact TEXT,
        message TEXT,
        created_at TEXT
    );
    """)
    conn.commit()
    conn.close()

# ---------------- APP FACTORY ----------------
def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey123"

    @app.before_request
    def open_db():
        g.db = get_db()

    @app.teardown_appcontext
    def close_db(e=None):
        db = g.pop("db", None)
        if db:
            db.close()

    # --- HOME PAGE ---
    # --- HOME PAGE ---
    @app.route("/")
    def home():
        # Total counts
        donors_count = g.db.execute("SELECT COUNT(*) FROM users WHERE role='Donor'").fetchone()[0]
        req_count = g.db.execute("SELECT COUNT(*) FROM emergency_requests").fetchone()[0]

        # BLOOD GROUP STATS (Ye naya part hai jo missing tha)
        blood_groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
        stats = {}
        for bg in blood_groups:
            count = g.db.execute("SELECT COUNT(*) FROM users WHERE role='Donor' AND blood_group=?", (bg,)).fetchone()[0]
            stats[bg] = count

        city_data = g.db.execute("""
            SELECT city, COUNT(*) as total 
            FROM users 
            WHERE role='Donor' AND city IS NOT NULL AND city != ''
            GROUP BY city 
            ORDER BY total DESC
        """).fetchall()

        return render_template("index.html", 
                               donors_count=donors_count, 
                               requests_count=req_count, 
                               cities=city_data,
                               stats=stats) # Stats ko template mein pass kiya

    # --- AUTHENTICATION ---

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            try:
                g.db.execute(
                    """INSERT INTO users(name, email, password, age, blood_group, contact, city, role) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        request.form["name"],
                        request.form["email"],
                        request.form["password"],
                        request.form.get("age"),
                        request.form.get("blood_group"),
                        request.form.get("contact"),
                        request.form.get("city"),
                        request.form.get("role", "Requester")
                    )
                )
                g.db.commit()
                flash("Account Created Successfully! Please Login.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Email already registered! Try another.", "error")
            except Exception as e:
                flash("Something went wrong. Please try again.", "error")

        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = g.db.execute(
                "SELECT * FROM users WHERE email=? AND password=?",
                (request.form["email"], request.form["password"])
            ).fetchone()

            if user:
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_role"] = user["role"]
                flash(f"Welcome back, {user['name']}!", "success")
                return redirect(url_for("profile"))
            else:
                flash("Invalid Email or Password!", "error")

        return render_template("login.html")

    @app.route("/profile")
    def profile():
        if "user_id" not in session:
            return redirect(url_for("login"))
        
        user_data = g.db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        return render_template("profile.html", user=user_data)

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out successfully.", "success")
        return redirect(url_for("login"))

    # --- DONOR CORE FEATURES ---

    @app.route("/donors")
    def donors_list():
        # Fetches all users registered as Donors
        data = g.db.execute("SELECT * FROM users WHERE role='Donor' ORDER BY id DESC").fetchall()
        return render_template("donors.html", donors=data)

    @app.route("/search")
    def search_donors():
        bg = request.args.get("blood_group", "").upper()
        city = request.args.get("city", "").strip()

        query = "SELECT * FROM users WHERE role='Donor'"
        params = []

        if bg:
            query += " AND blood_group=?"
            params.append(bg.upper())#ensure blood group is uppercase for consistency
        if city:
            # LOWER() is used to make the search case-insensitive
            query += " AND LOWER(city) LIKE LOWER(?)"
            params.append(f"%{city.strip()}%")   #.strip() removes leading/trailing spaces to prevent search issues
        donors = g.db.execute(query, params).fetchall()
        return render_template("search.html", donors=donors, selected_group=bg)

    @app.route("/compatibility")
    def compatibility_checker():
        # Static mapping for compatibility
        compat_map = {
            "A+": ["A+", "A-", "O+", "O-"],
            "A-": ["A-", "O-"],
            "B+": ["B+", "B-", "O+", "O-"],
            "B-": ["B-", "O-"],
            "AB+": ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
            "AB-": ["A-", "B-", "O-", "AB-"],
            "O+": ["O+", "O-"],
            "O-": ["O-"]
        }
        
        selected_bg = request.args.get("blood_group", "").upper()
        compatible_donors = []

        if selected_bg in compat_map:
            groups = compat_map[selected_bg]
            placeholders = ",".join(["?"] * len(groups))
            query = f"SELECT * FROM users WHERE role='Donor' AND blood_group IN ({placeholders})"
            compatible_donors = g.db.execute(query, groups).fetchall()

        return render_template("compatibility.html", 
                               donors=compatible_donors, 
                               selected_group=selected_bg)

    # --- EMERGENCY SECTION ---

    @app.route("/emergency", methods=["GET", "POST"])
    def emergency_request():
        if request.method == "POST":
            g.db.execute("""
                INSERT INTO emergency_requests
                (patient_name, blood_group, units_needed, hospital, contact, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                request.form["patient_name"],
                request.form["blood_group"],
                request.form["units_needed"],
                request.form["hospital"],
                request.form["contact"],
                request.form["message"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            g.db.commit()
            flash("Emergency Alert Broadcasted!", "success")
            return redirect(url_for("emergency_request"))

        data = g.db.execute("SELECT * FROM emergency_requests ORDER BY id DESC").fetchall()
        return render_template("emergency.html", requests=data)

    return app

# ---------------- EXECUTION ----------------
app = create_app()

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)