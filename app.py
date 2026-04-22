import os
import sqlite3
from datetime import datetime

from flask import Flask, flash, g, redirect, render_template, request, url_for


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "blood_donation.db")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key",
        DATABASE=DEFAULT_DB_PATH,
    )

    if test_config:
        app.config.update(test_config)

    @app.before_request
    def open_db_connection():
        g.db = get_db(app.config["DATABASE"])

    @app.teardown_request
    def close_db_connection(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/")
    def home():
    donors_count = g.db.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
    requests_count = g.db.execute("SELECT COUNT(*) FROM emergency_requests").fetchone()[0]

    ap_count = g.db.execute("SELECT COUNT(*) FROM donors WHERE blood_group='A+'").fetchone()[0]
    bp_count = g.db.execute("SELECT COUNT(*) FROM donors WHERE blood_group='B+'").fetchone()[0]
    op_count = g.db.execute("SELECT COUNT(*) FROM donors WHERE blood_group='O+'").fetchone()[0]
    abp_count = g.db.execute("SELECT COUNT(*) FROM donors WHERE blood_group='AB+'").fetchone()[0]

    return render_template(
        "index.html",
        donors_count=donors_count,
        requests_count=requests_count,
        ap_count=ap_count,
        bp_count=bp_count,
        op_count=op_count,
        abp_count=abp_count
    )

    @app.route("/register", methods=["GET", "POST"])
    def register_donor():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            age = request.form.get("age", "").strip()
            blood_group = request.form.get("blood_group", "").strip().upper()
            contact = request.form.get("contact", "").strip()
            city = request.form.get("city", "").strip()

            if not all([name, age, blood_group, contact, city]):
                flash("Please fill in all donor details.", "error")
                return redirect(url_for("register_donor"))

            try:
                age_int = int(age)
                if age_int < 18:
                    flash("Donor must be at least 18 years old.", "error")
                    return redirect(url_for("register_donor"))
            except ValueError:
                flash("Age must be a number.", "error")
                return redirect(url_for("register_donor"))

            g.db.execute(
                """
                INSERT INTO donors (name, age, blood_group, contact, city)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, age_int, blood_group, contact, city),
            )
            g.db.commit()
            flash("Donor registered successfully!", "success")
            return redirect(url_for("register_donor"))

        return render_template("register.html")

    @app.route("/search", methods=["GET"])
    def search_donors():
        blood_group = request.args.get("blood_group", "").strip().upper()
        donors = []

        if blood_group:
            donors = g.db.execute(
                "SELECT * FROM donors WHERE blood_group = ? ORDER BY name",
                (blood_group,),
            ).fetchall()

        return render_template("search.html", donors=donors, selected_group=blood_group)

    @app.route("/emergency", methods=["GET", "POST"])
    def emergency_request():
        if request.method == "POST":
            patient_name = request.form.get("patient_name", "").strip()
            blood_group = request.form.get("blood_group", "").strip().upper()
            units_needed = request.form.get("units_needed", "").strip()
            hospital = request.form.get("hospital", "").strip()
            contact = request.form.get("contact", "").strip()
            message = request.form.get("message", "").strip()

            if not all([patient_name, blood_group, units_needed, hospital, contact]):
                flash("Please fill in all required emergency details.", "error")
                return redirect(url_for("emergency_request"))

            g.db.execute(
                """
                INSERT INTO emergency_requests
                (patient_name, blood_group, units_needed, hospital, contact, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_name,
                    blood_group,
                    units_needed,
                    hospital,
                    contact,
                    message,
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            g.db.commit()
            flash("Emergency request submitted successfully.", "success")
            return redirect(url_for("emergency_request"))

        recent_requests = g.db.execute(
            "SELECT * FROM emergency_requests ORDER BY id DESC LIMIT 10"
        ).fetchall()
        return render_template("emergency.html", requests=recent_requests)

    @app.route("/donors")
    def donors_list():
        donors = g.db.execute("SELECT * FROM donors ORDER BY id DESC").fetchall()
        return render_template("donors.html", donors=donors)

    return app


def get_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    conn = get_db(db_path)
    conn.executescript(
        """
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
        """
    )
    conn.commit()
    conn.close()


app = create_app()
init_db(app.config["DATABASE"])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
