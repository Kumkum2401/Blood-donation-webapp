import os
import sqlite3
from datetime import datetime
from flask import Flask, flash, g, redirect, render_template, request, url_for


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "blood_donation.db")


# ------------------ COMPATIBILITY LOGIC ------------------
def get_compatible_blood(blood_group):
    compatibility = {
        "A+": ["A+", "A-", "O+", "O-"],
        "A-": ["A-", "O-"],
        "B+": ["B+", "B-", "O+", "O-"],
        "B-": ["B-", "O-"],
        "AB+": ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
        "AB-": ["A-", "B-", "O-", "AB-"],
        "O+": ["O+", "O-"],
        "O-": ["O-"]
    }
    return compatibility.get(blood_group.upper(), [])


# ------------------ DB ------------------
def get_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    conn = get_db(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            blood_group TEXT NOT NULL,
            contact TEXT NOT NULL,
            city TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS emergency_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            units_needed TEXT NOT NULL,
            hospital TEXT NOT NULL,
            contact TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ------------------ APP ------------------
def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key",
        DATABASE=DEFAULT_DB_PATH,
    )

    if test_config:
        app.config.update(test_config)

    # DB open
    @app.before_request
    def open_db():
        g.db = get_db(app.config["DATABASE"])

    # DB close
    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db:
            db.close()

    # ------------------ HOME ------------------
    @app.route("/")
    def home():
        donors_count = g.db.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
        requests_count = g.db.execute("SELECT COUNT(*) FROM emergency_requests").fetchone()[0]

        return render_template(
            "index.html",
            donors_count=donors_count,
            requests_count=requests_count
        )

    # ------------------ REGISTER ------------------
    @app.route("/register", methods=["GET", "POST"])
    def register_donor():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            age = request.form.get("age", "").strip()
            blood_group = request.form.get("blood_group", "").strip().upper()
            contact = request.form.get("contact", "").strip()
            city = request.form.get("city", "").strip()

            if not all([name, age, blood_group, contact, city]):
                flash("Please fill all fields", "error")
                return redirect(url_for("register_donor"))

            try:
                age = int(age)
                if age < 18:
                    flash("Age must be 18+", "error")
                    return redirect(url_for("register_donor"))
            except:
                flash("Invalid age", "error")
                return redirect(url_for("register_donor"))

            g.db.execute(
                "INSERT INTO donors (name, age, blood_group, contact, city) VALUES (?, ?, ?, ?, ?)",
                (name, age, blood_group, contact, city)
            )
            g.db.commit()

            flash("Donor registered successfully!", "success")
            return redirect(url_for("register_donor"))

        return render_template("register.html")

    # ------------------ SEARCH ------------------
    @app.route("/search")
    def search_donors():
        bg = request.args.get("blood_group", "").strip().upper()

        donors = []
        if bg:
            donors = g.db.execute(
                "SELECT * FROM donors WHERE blood_group=?",
                (bg,)
            ).fetchall()

        return render_template("search.html", donors=donors, selected_group=bg)

    # ------------------ EMERGENCY ------------------
    @app.route("/emergency", methods=["GET", "POST"])
    def emergency_request():
        if request.method == "POST":
            patient = request.form.get("patient_name")
            bg = request.form.get("blood_group")
            units = request.form.get("units_needed")
            hospital = request.form.get("hospital")
            contact = request.form.get("contact")
            message = request.form.get("message")

            g.db.execute("""
                INSERT INTO emergency_requests
                (patient_name, blood_group, units_needed, hospital, contact, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                patient,
                bg,
                units,
                hospital,
                contact,
                message,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ))

            g.db.commit()
            flash("Emergency request sent!", "success")
            return redirect(url_for("emergency_request"))

        requests = g.db.execute(
            "SELECT * FROM emergency_requests ORDER BY id DESC LIMIT 10"
        ).fetchall()

        return render_template("emergency.html", requests=requests)

    # ------------------ DONORS ------------------
    @app.route("/donors")
    def donors_list():
        donors = g.db.execute("SELECT * FROM donors ORDER BY id DESC").fetchall()
        return render_template("donors.html", donors=donors)

    # ------------------ COMPATIBILITY ------------------
    @app.route("/compatibility", methods=["GET", "POST"])
    def compatibility_checker():
        result = None
        selected = None

        if request.method == "POST":
            bg = request.form.get("blood_group", "").strip().upper()
            selected = bg

            if bg:
                compatible = get_compatible_blood(bg)

                if compatible:
                    result = g.db.execute(
                        "SELECT * FROM donors WHERE blood_group IN ({})".format(
                            ",".join(["?"] * len(compatible))
                        ),
                        compatible
                    ).fetchall()

        return render_template(
            "compatibility.html",
            donors=result,
            selected=selected
        )

    return app


# ------------------ RUN ------------------
app = create_app()
init_db(app.config["DATABASE"])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)