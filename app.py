from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from functools import wraps
import sqlite3
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret")
DATABASE = "air_ticket_system.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript(
        """
        DROP TABLE IF EXISTS ticket;
        DROP TABLE IF EXISTS flight;
        DROP TABLE IF EXISTS airplane;
        DROP TABLE IF EXISTS customer;
        DROP TABLE IF EXISTS airline_staff;
        DROP TABLE IF EXISTS airline;

        CREATE TABLE airline (
            airline_name TEXT PRIMARY KEY
        );

        CREATE TABLE customer (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE airline_staff (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            airline_name TEXT NOT NULL,
            FOREIGN KEY (airline_name) REFERENCES airline(airline_name)
        );

        CREATE TABLE airplane (
            airplane_id INTEGER PRIMARY KEY AUTOINCREMENT,
            airline_name TEXT NOT NULL,
            num_seats INTEGER NOT NULL,
            manufacturer TEXT,
            FOREIGN KEY (airline_name) REFERENCES airline(airline_name)
        );

        CREATE TABLE flight (
            flight_id INTEGER PRIMARY KEY AUTOINCREMENT,
            airline_name TEXT NOT NULL,
            source_airport TEXT NOT NULL,
            destination_airport TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'On Time',
            airplane_id INTEGER,
            FOREIGN KEY (airline_name) REFERENCES airline(airline_name),
            FOREIGN KEY (airplane_id) REFERENCES airplane(airplane_id)
        );

        CREATE TABLE ticket (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_email TEXT NOT NULL,
            flight_id INTEGER NOT NULL,
            purchase_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_email) REFERENCES customer(email),
            FOREIGN KEY (flight_id) REFERENCES flight(flight_id)
        );
        """
    )

    cursor.executescript(
        """
        INSERT INTO airline (airline_name) VALUES
        ('SkyJet'),
        ('BlueCloud');

        INSERT INTO customer (email, name, password) VALUES
        ('cj@example.com', 'CJ Thomas', 'test123'),
        ('alex@example.com', 'Alex Johnson', 'test123');

        INSERT INTO airline_staff (username, password, first_name, last_name, airline_name) VALUES
        ('staff1', 'admin123', 'Maya', 'Lee', 'SkyJet'),
        ('staff2', 'admin123', 'Chris', 'Wong', 'BlueCloud');

        INSERT INTO airplane (airline_name, num_seats, manufacturer) VALUES
        ('SkyJet', 180, 'Boeing'),
        ('BlueCloud', 220, 'Airbus');

        INSERT INTO flight (airline_name, source_airport, destination_airport, departure_time, arrival_time, price, status, airplane_id) VALUES
        ('SkyJet', 'JFK', 'LAX', '2026-04-22 09:00:00', '2026-04-22 12:00:00', 320.00, 'On Time', 1),
        ('SkyJet', 'JFK', 'MIA', '2026-04-23 14:00:00', '2026-04-23 17:00:00', 180.00, 'Delayed', 1),
        ('BlueCloud', 'EWR', 'ATL', '2026-04-24 08:30:00', '2026-04-24 11:00:00', 210.00, 'On Time', 2);

        INSERT INTO ticket (customer_email, flight_id) VALUES
        ('cj@example.com', 1),
        ('alex@example.com', 3);
        """
    )

    conn.commit()
    conn.close()

def ensure_db_exists():
    if not os.path.exists(DATABASE):
        init_db()


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_type" not in session:
                flash("Please log in first.")
                return redirect(url_for("login"))
            if role and session.get("user_type") != role:
                flash("Unauthorized access.")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.route("/")
def index():
    ensure_db_exists()
    return redirect(url_for("login"))


@app.route("/reset-db")
def reset_db():
    init_db()
    flash("Database reset with sample data.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_db_exists()

    if request.method == "POST":
        user_type = request.form["user_type"]
        identifier = request.form["identifier"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        if user_type == "customer":
            cursor.execute(
                "SELECT * FROM customer WHERE email = ? AND password = ?",
                (identifier, password),
            )
            user = cursor.fetchone()
            if user:
                session["user_type"] = "customer"
                session["user_id"] = user["email"]
                session["display_name"] = user["name"]
                conn.close()
                return redirect(url_for("customer_home"))

        elif user_type == "staff":
            cursor.execute(
                "SELECT * FROM airline_staff WHERE username = ? AND password = ?",
                (identifier, password),
            )
            user = cursor.fetchone()
            if user:
                session["user_type"] = "staff"
                session["user_id"] = user["username"]
                session["display_name"] = f"{user['first_name']} {user['last_name']}"
                session["airline_name"] = user["airline_name"]
                conn.close()
                return redirect(url_for("staff_home"))

        conn.close()
        flash("Invalid credentials.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("login"))


@app.route("/customer/home")
@login_required(role="customer")
def customer_home():
    return render_template("customer_home.html", name=session.get("display_name"))


@app.route("/staff/home")
@login_required(role="staff")
def staff_home():
    return render_template(
        "staff_home.html",
        name=session.get("display_name"),
        airline=session.get("airline_name"),
    )


@app.route("/customer/search", methods=["GET", "POST"])
@login_required(role="customer")
def search_flights():
    flights = []
    if request.method == "POST":
        source = request.form.get("source", "").strip()
        destination = request.form.get("destination", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM flight
            WHERE departure_time > datetime('now')
              AND source_airport LIKE ?
              AND destination_airport LIKE ?
            ORDER BY departure_time ASC
            """,
            (f"%{source}%", f"%{destination}%"),
        )
        flights = cursor.fetchall()
        conn.close()

    return render_template("search_flights.html", flights=flights)


@app.route("/customer/my-flights")
@login_required(role="customer")
def my_flights():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT f.*
        FROM ticket t
        JOIN flight f ON t.flight_id = f.flight_id
        WHERE t.customer_email = ?
        ORDER BY f.departure_time ASC
        """,
        (session["user_id"],),
    )
    flights = cursor.fetchall()
    conn.close()
    return render_template("my_flights.html", flights=flights)


@app.route("/staff/flights")
@login_required(role="staff")
def staff_flights():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM flight
        WHERE airline_name = ?
          AND departure_time BETWEEN datetime('now') AND datetime('now', '+30 days')
        ORDER BY departure_time ASC
        """,
        (session["airline_name"],),
    )
    flights = cursor.fetchall()
    conn.close()
    return render_template("staff_flights.html", flights=flights)


@app.route("/staff/create-flight", methods=["GET", "POST"])
@login_required(role="staff")
def create_flight():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT airplane_id FROM airplane WHERE airline_name = ?",
        (session["airline_name"],),
    )
    airplanes = cursor.fetchall()

    if request.method == "POST":
        source = request.form["source"]
        destination = request.form["destination"]
        departure_time = request.form["departure_time"].replace("T", " ") + ":00"
        arrival_time = request.form["arrival_time"].replace("T", " ") + ":00"
        price = request.form["price"]
        airplane_id = request.form["airplane_id"]

        cursor.execute(
            """
            INSERT INTO flight
            (airline_name, source_airport, destination_airport, departure_time, arrival_time, price, status, airplane_id)
            VALUES (?, ?, ?, ?, ?, ?, 'On Time', ?)
            """,
            (
                session["airline_name"],
                source,
                                destination,
                departure_time,
                arrival_time,
                price,
                airplane_id,
            ),
        )
        conn.commit()
        conn.close()
        flash("Flight created successfully.")
        return redirect(url_for("staff_flights"))

    conn.close()
    return render_template("create_flight.html", airplanes=airplanes)


if __name__ == "__main__":
    ensure_db_exists()
    app.run(debug=True)