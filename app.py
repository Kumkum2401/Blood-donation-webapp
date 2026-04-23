import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g, session

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "blood_donation.db")


# ---------------- COMPATIBILITY ----------------
def get_compatible_blood(bg):
    data = {
        "A+": ["A+", "A-", "O+", "O-"],
        "A-": ["A-", "O-"],
        "B+": ["B+", "B-", "O+", "O-"],
        "B-": ["B-", "O-"],
        "AB+": ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
        "AB-": ["A-", "B-", "O-", "AB-"],
        "O+": ["O+", "O-"],
        "O-": ["O-"]
    }
    return data.get(bg.upper(), [])


# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS donors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        blood_group TEXT,
        contact TEXT,
        city TEXT
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

    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    );
    """)
    conn.commit()
    conn.close()


# ---------------- APP ----------------
def create_app():
    app = Flask(__name__)
    app.secret_key = "secret"

    @app.before_request
    def open_db():
        g.db = get_db()

    @app.teardown_appcontext
    def close_db(e=None):
        db = g.pop("db", None)
        if db:
            db.close()

    # HOME
    @app.route("/")
    def home():
        donors_count = g.db.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
        req_count = g.db.execute("SELECT COUNT(*) FROM emergency_requests").fetchone()[0]

        ap_count = g.db.execute("SELECT COUNT(*) FROM donors WHERE blood_group='A+'").fetchone()[0]
        bp_count = g.db.execute("SELECT COUNT(*) FROM donors WHERE blood_group='B+'").fetchone()[0]
        op_count = g.db.execute("SELECT COUNT(*) FROM donors WHERE blood_group='O+'").fetchone()[0]
        abp_count = g.db.execute("SELECT COUNT(*) FROM donors WHERE blood_group='AB+'").fetchone()[0]

        city_data = g.db.execute("""
            SELECT city, COUNT(*) as total 
            FROM donors 
            GROUP BY city 
            ORDER BY total DESC
        """).fetchall()

        return render_template("index.html",
            donors_count=donors_count,
            requests_count=req_count,
            ap_count=ap_count,
            bp_count=bp_count,
            op_count=op_count,
            abp_count=abp_count,
            cities=city_data
        )

    # ---------------- AUTH ----------------

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            try:
                g.db.execute(
                    "INSERT INTO users(name, email, password) VALUES (?, ?, ?)",
                    (
                        request.form["name"],
                        request.form["email"],
                        request.form["password"]
                    )
                )
                g.db.commit()
                flash("Account Created!", "success")
                return redirect(url_for("login"))
            except:
                flash("Email already exists!", "error")

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
                return redirect(url_for("profile"))
            else:
                flash("Invalid credentials!", "error")

        return render_template("login.html")

    @app.route("/profile")
    def profile():
        if "user_id" not in session:
            return redirect(url_for("login"))

        return render_template("profile.html", name=session["user_name"])

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ---------------- DONOR ----------------

    @app.route("/register", methods=["GET", "POST"])
    def register_donor():
        if request.method == "POST":
            g.db.execute("""
                INSERT INTO donors(name, age, blood_group, contact, city)
                VALUES (?, ?, ?, ?, ?)
            """, (
                request.form["name"],
                request.form["age"],
                request.form["blood_group"],
                request.form["contact"],
                request.form["city"]
            ))
            g.db.commit()
            flash("Donor Registered!", "success")
            return redirect(url_for("register_donor"))

        return render_template("register.html")

    @app.route("/search")
    def search_donors():
        bg = request.args.get("blood_group", "").upper()
        city = request.args.get("city", "")

        query = "SELECT * FROM donors WHERE 1=1"
        params = []

        if bg:
            query += " AND blood_group=?"
            params.append(bg)

        if city:
            query += " AND city LIKE ?"
            params.append(f"%{city}%")

        donors = g.db.execute(query, params).fetchall()

        return render_template("search.html",
            donors=donors,
            selected_group=bg,
            selected_city=city
        )

    # ---------------- EMERGENCY ----------------

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
            flash("Request Sent!", "success")
            return redirect(url_for("emergency_request"))

        data = g.db.execute("SELECT * FROM emergency_requests ORDER BY id DESC").fetchall()
        return render_template("emergency.html", requests=data)

    # ---------------- OTHER ----------------

    @app.route("/donors")
    def donors_list():
        data = g.db.execute("SELECT * FROM donors ORDER BY id DESC").fetchall()
        return render_template("donors.html", donors=data)

    @app.route("/compatibility", methods=["GET", "POST"])
    def compatibility_checker():
        result = []
        selected = None

        if request.method == "POST":
            selected = request.form["blood_group"]
            compatible = get_compatible_blood(selected)

            if compatible:
                query = "SELECT * FROM donors WHERE blood_group IN ({})".format(
                    ",".join(["?"] * len(compatible))
                )
                result = g.db.execute(query, compatible).fetchall()

        return render_template("compatibility.html", donors=result, selected=selected)

    return app


# ---------------- RUN ----------------
app = create_app()

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)