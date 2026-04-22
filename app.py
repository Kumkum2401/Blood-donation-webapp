import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g

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
    """)
    conn.commit()
    conn.close()


# ---------------- APP ----------------
def create_app():
    app = Flask(__name__)
    app.secret_key = "secret"
    app.config["DATABASE"] = DB_PATH

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

        return render_template(
            "index.html",
            donors_count=donors_count,
            requests_count=req_count
        )

    # REGISTER
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

    # SEARCH
    @app.route("/search")
    def search_donors():
        bg = request.args.get("blood_group", "").upper()
        donors = []

        if bg:
            donors = g.db.execute(
                "SELECT * FROM donors WHERE blood_group=?",
                (bg,)
            ).fetchall()

        return render_template(
            "search.html", 
            donors=donors,
            selected_group=bg)
        

    # EMERGENCY
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

    # DONORS
    @app.route("/donors")
    def donors_list():
        data = g.db.execute("SELECT * FROM donors ORDER BY id DESC").fetchall()
        return render_template("donors.html", donors=data)

    # COMPATIBILITY
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
    app.run(debug=True)