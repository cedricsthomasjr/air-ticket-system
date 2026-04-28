from datetime import datetime, timedelta
from functools import wraps
import hashlib
import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
import mysql.connector
from mysql.connector import errorcode

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret")


def md5_hash(password):
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def mysql_config(include_database=True):
    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
    }
    if include_database:
        config["database"] = os.getenv("MYSQL_DATABASE", "air_ticket_system")
    return config


def get_db_connection(include_database=True):
    return mysql.connector.connect(**mysql_config(include_database=include_database))


def dict_cursor(conn):
    return conn.cursor(dictionary=True)


def execute_sql_file(cursor, path):
    with open(path, "r", encoding="utf-8") as sql_file:
        statements = [
            statement.strip()
            for statement in sql_file.read().split(";")
            if statement.strip()
        ]
    for statement in statements:
        cursor.execute(statement)


def init_db():
    db_name = os.getenv("MYSQL_DATABASE", "air_ticket_system")
    conn = get_db_connection(include_database=False)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cursor.execute(f"USE `{db_name}`")
    execute_sql_file(cursor, os.path.join(app.root_path, "sql", "schema.sql"))
    execute_sql_file(cursor, os.path.join(app.root_path, "sql", "seed.sql"))
    conn.commit()
    cursor.close()
    conn.close()


def ensure_db_exists():
    try:
        conn = get_db_connection()
        conn.close()
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            init_db()
        else:
            raise


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


def require_staff_airline_flight(cursor, flight_id):
    cursor.execute(
        "SELECT * FROM flight WHERE flight_id = %s AND airline_name = %s",
        (flight_id, session.get("airline_name")),
    )
    return cursor.fetchone()


def flight_search_query(source, destination, depart_date=None, return_date=None, airline_name=None):
    sql = """
        SELECT f.*, a.num_seats,
               COUNT(t.ticket_id) AS tickets_sold,
               (a.num_seats - COUNT(t.ticket_id)) AS seats_available
        FROM flight f
        LEFT JOIN airplane a ON f.airplane_id = a.airplane_id
        LEFT JOIN ticket t ON f.flight_id = t.flight_id
        WHERE f.departure_time > NOW()
          AND (f.source_airport LIKE %s OR f.source_city LIKE %s)
          AND (f.destination_airport LIKE %s OR f.destination_city LIKE %s)
    """
    params = [f"%{source}%", f"%{source}%", f"%{destination}%", f"%{destination}%"]
    if depart_date:
        sql += " AND DATE(f.departure_time) = %s"
        params.append(depart_date)
    if return_date:
        sql += " AND DATE(f.departure_time) <= %s"
        params.append(return_date)
    if airline_name:
        sql += " AND f.airline_name = %s"
        params.append(airline_name)
    sql += " GROUP BY f.flight_id ORDER BY f.departure_time ASC"
    return sql, params


@app.route("/")
def index():
    ensure_db_exists()
    return render_template("index.html")


@app.route("/reset-db")
def reset_db():
    init_db()
    flash("MySQL database reset with sample data.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_db_exists()

    if request.method == "POST":
        user_type = request.form["user_type"]
        identifier = request.form["identifier"].strip()
        password = md5_hash(request.form["password"])

        conn = get_db_connection()
        cursor = dict_cursor(conn)

        if user_type == "customer":
            cursor.execute(
                "SELECT * FROM customer WHERE email = %s AND password = %s",
                (identifier, password),
            )
            user = cursor.fetchone()
            if user:
                session["user_type"] = "customer"
                session["user_id"] = user["email"]
                session["display_name"] = user["name"]
                cursor.close()
                conn.close()
                return redirect(url_for("customer_home"))

        elif user_type == "staff":
            cursor.execute(
                "SELECT * FROM airline_staff WHERE username = %s AND password = %s",
                (identifier, password),
            )
            user = cursor.fetchone()
            if user:
                session["user_type"] = "staff"
                session["user_id"] = user["username"]
                session["display_name"] = f"{user['first_name']} {user['last_name']}"
                session["airline_name"] = user["airline_name"]
                cursor.close()
                conn.close()
                return redirect(url_for("staff_home"))

        cursor.close()
        conn.close()
        flash("Invalid credentials.")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    ensure_db_exists()
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute("SELECT airline_name FROM airline ORDER BY airline_name")
    airlines = cursor.fetchall()

    if request.method == "POST":
        user_type = request.form["user_type"]
        password = md5_hash(request.form["password"])
        try:
            if user_type == "customer":
                email = request.form.get("email", "").strip()
                name = request.form.get("name", "").strip()
                if not email or not name:
                    flash("Customer registration requires name and email.")
                    cursor.close()
                    conn.close()
                    return render_template("register.html", airlines=airlines)
                cursor.execute(
                    "INSERT INTO customer (email, name, password) VALUES (%s, %s, %s)",
                    (email, name, password),
                )
            else:
                username = request.form.get("username", "").strip()
                first_name = request.form.get("first_name", "").strip()
                last_name = request.form.get("last_name", "").strip()
                if not username or not first_name or not last_name:
                    flash("Staff registration requires username, first name, and last name.")
                    cursor.close()
                    conn.close()
                    return render_template("register.html", airlines=airlines)
                cursor.execute(
                    """
                    INSERT INTO airline_staff
                    (username, password, first_name, last_name, airline_name)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        username,
                        password,
                        first_name,
                        last_name,
                        request.form["airline_name"],
                    ),
                )
            conn.commit()
            flash("Registration successful. Please log in.")
            cursor.close()
            conn.close()
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            conn.rollback()
            flash("That email or username is already registered.")
            cursor.close()
            conn.close()
            return render_template("register.html", airlines=airlines)

    cursor.close()
    conn.close()
    return render_template("register.html", airlines=airlines)


@app.route("/public/search", methods=["GET", "POST"])
def public_search():
    ensure_db_exists()
    form = request.form if request.method == "POST" else {}
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    sql, params = flight_search_query(
        form.get("source", "").strip(),
        form.get("destination", "").strip(),
        form.get("departure_date") or None,
        form.get("return_date") or None,
    )
    cursor.execute(sql, params)
    flights = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("public_search.html", flights=flights)


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("login"))


@app.route("/customer/home")
@login_required(role="customer")
def customer_home():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT f.*
        FROM ticket t
        JOIN flight f ON t.flight_id = f.flight_id
        WHERE t.customer_email = %s AND f.departure_time > NOW()
        ORDER BY f.departure_time ASC
        LIMIT 5
        """,
        (session["user_id"],),
    )
    upcoming = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("customer_home.html", name=session.get("display_name"), upcoming=upcoming)


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
    form = request.form if request.method == "POST" else {}
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    sql, params = flight_search_query(
        form.get("source", "").strip(),
        form.get("destination", "").strip(),
        form.get("departure_date") or None,
        form.get("return_date") or None,
    )
    cursor.execute(sql, params)
    flights = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("search_flights.html", flights=flights)


@app.route("/customer/my-flights")
@login_required(role="customer")
def my_flights():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT f.*, r.rating, r.comment
        FROM ticket t
        JOIN flight f ON t.flight_id = f.flight_id
        LEFT JOIN review r ON r.flight_id = f.flight_id AND r.customer_email = t.customer_email
        WHERE t.customer_email = %s
        ORDER BY f.departure_time ASC
        """,
        (session["user_id"],),
    )
    flights = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        "my_flights.html",
        flights=flights,
        now=datetime.now(),
    )


@app.route("/customer/purchase/<int:flight_id>", methods=["POST"])
@login_required(role="customer")
def purchase_ticket(flight_id):
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT f.*, a.num_seats, COUNT(t.ticket_id) AS tickets_sold
        FROM flight f
        LEFT JOIN airplane a ON f.airplane_id = a.airplane_id
        LEFT JOIN ticket t ON f.flight_id = t.flight_id
        WHERE f.flight_id = %s AND f.departure_time > NOW()
        GROUP BY f.flight_id
        """,
        (flight_id,),
    )
    flight = cursor.fetchone()
    if not flight:
        flash("That future flight is not available for purchase.")
    elif flight["num_seats"] is not None and flight["tickets_sold"] >= flight["num_seats"]:
        flash("That flight is sold out.")
    else:
        cursor.execute(
            "SELECT 1 FROM ticket WHERE customer_email = %s AND flight_id = %s",
            (session["user_id"], flight_id),
        )
        if cursor.fetchone():
            flash("You already purchased a ticket for that flight.")
        else:
            cursor.execute(
                "INSERT INTO ticket (customer_email, flight_id) VALUES (%s, %s)",
                (session["user_id"], flight_id),
            )
            conn.commit()
            flash("Ticket purchased successfully.")
    cursor.close()
    conn.close()
    return redirect(url_for("my_flights"))


@app.route("/customer/review/<int:flight_id>", methods=["POST"])
@login_required(role="customer")
def review_flight(flight_id):
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT f.flight_id
        FROM ticket t
        JOIN flight f ON f.flight_id = t.flight_id
        WHERE t.customer_email = %s AND f.flight_id = %s AND f.departure_time < NOW()
        """,
        (session["user_id"], flight_id),
    )
    if not cursor.fetchone():
        flash("You can only review past flights you purchased.")
    else:
        cursor.execute(
            """
            INSERT INTO review (customer_email, flight_id, rating, comment)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                rating = VALUES(rating),
                comment = VALUES(comment),
                created_at = CURRENT_TIMESTAMP
            """,
            (
                session["user_id"],
                flight_id,
                int(request.form["rating"]),
                request.form.get("comment", "").strip(),
            ),
        )
        conn.commit()
        flash("Review saved.")
    cursor.close()
    conn.close()
    return redirect(url_for("my_flights"))


@app.route("/staff/flights")
@login_required(role="staff")
def staff_flights():
    default_start = datetime.now().date().isoformat()
    default_end = (datetime.now() + timedelta(days=30)).date().isoformat()
    start_date = request.args.get("start_date") or default_start
    end_date = request.args.get("end_date") or default_end
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT f.*, COUNT(t.ticket_id) AS tickets_sold
        FROM flight f
        LEFT JOIN ticket t ON f.flight_id = t.flight_id
        WHERE f.airline_name = %s
          AND DATE(f.departure_time) BETWEEN %s AND %s
          AND (f.source_airport LIKE %s OR f.source_city LIKE %s)
          AND (f.destination_airport LIKE %s OR f.destination_city LIKE %s)
        GROUP BY f.flight_id
        ORDER BY departure_time ASC
        """,
        (
            session["airline_name"],
            start_date,
            end_date,
            f"%{source}%",
            f"%{source}%",
            f"%{destination}%",
            f"%{destination}%",
        ),
    )
    flights = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        "staff_flights.html",
        flights=flights,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/staff/create-flight", methods=["GET", "POST"])
@login_required(role="staff")
def create_flight():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        "SELECT airplane_id FROM airplane WHERE airline_name = %s",
        (session["airline_name"],),
    )
    airplanes = cursor.fetchall()

    if request.method == "POST":
        source = request.form["source"].strip()
        destination = request.form["destination"].strip()
        source_city = request.form.get("source_city", "").strip()
        destination_city = request.form.get("destination_city", "").strip()
        departure_time = request.form["departure_time"].replace("T", " ") + ":00"
        arrival_time = request.form["arrival_time"].replace("T", " ") + ":00"
        price = request.form["price"]
        airplane_id = request.form["airplane_id"]

        cursor.execute(
            "SELECT 1 FROM airplane WHERE airplane_id = %s AND airline_name = %s",
            (airplane_id, session["airline_name"]),
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            flash("You can only assign airplanes owned by your airline.")
            return redirect(url_for("create_flight"))

        cursor.execute(
            """
            INSERT INTO flight (
                airline_name, source_city, destination_city, source_airport, destination_airport,
                departure_time, arrival_time, price, status, airplane_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'On Time', %s)
            """,
            (
                session["airline_name"],
                source_city,
                destination_city,
                source,
                destination,
                departure_time,
                arrival_time,
                price,
                airplane_id,
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Flight created successfully.")
        return redirect(url_for("staff_flights"))

    cursor.close()
    conn.close()
    return render_template("create_flight.html", airplanes=airplanes)


@app.route("/staff/flight/<int:flight_id>")
@login_required(role="staff")
def staff_flight_detail(flight_id):
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    flight = require_staff_airline_flight(cursor, flight_id)
    if not flight:
        cursor.close()
        conn.close()
        flash("Flight not found for your airline.")
        return redirect(url_for("staff_flights"))
    cursor.execute(
        """
        SELECT c.email, c.name, t.purchase_time
        FROM ticket t
        JOIN customer c ON c.email = t.customer_email
        WHERE t.flight_id = %s
        ORDER BY t.purchase_time DESC
        """,
        (flight_id,),
    )
    customers = cursor.fetchall()
    cursor.execute(
        """
        SELECT r.rating, r.comment, r.created_at, c.name, c.email
        FROM review r
        JOIN customer c ON c.email = r.customer_email
        WHERE r.flight_id = %s
        ORDER BY r.created_at DESC
        """,
        (flight_id,),
    )
    reviews = cursor.fetchall()
    cursor.execute("SELECT AVG(rating) AS avg_rating FROM review WHERE flight_id = %s", (flight_id,))
    avg_rating = cursor.fetchone()["avg_rating"]
    cursor.close()
    conn.close()
    return render_template(
        "staff_flight_detail.html",
        flight=flight,
        customers=customers,
        reviews=reviews,
        avg_rating=avg_rating,
    )


@app.route("/staff/update-status/<int:flight_id>", methods=["POST"])
@login_required(role="staff")
def update_status(flight_id):
    status = request.form["status"]
    if status not in ("On Time", "Delayed", "Cancelled"):
        flash("Invalid status.")
        return redirect(url_for("staff_flights"))
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    flight = require_staff_airline_flight(cursor, flight_id)
    if not flight:
        flash("You can only update flights for your airline.")
    else:
        cursor.execute("UPDATE flight SET status = %s WHERE flight_id = %s", (status, flight_id))
        conn.commit()
        flash("Flight status updated.")
    cursor.close()
    conn.close()
    return redirect(url_for("staff_flights"))


@app.route("/staff/add-airplane", methods=["GET", "POST"])
@login_required(role="staff")
def add_airplane():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    if request.method == "POST":
        cursor.execute(
            "INSERT INTO airplane (airline_name, num_seats, manufacturer) VALUES (%s, %s, %s)",
            (
                session["airline_name"],
                int(request.form["num_seats"]),
                request.form.get("manufacturer", "").strip(),
            ),
        )
        conn.commit()
        flash("Airplane added.")
    cursor.execute(
        "SELECT * FROM airplane WHERE airline_name = %s ORDER BY airplane_id",
        (session["airline_name"],),
    )
    airplanes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("add_airplane.html", airplanes=airplanes)


@app.route("/staff/reports")
@login_required(role="staff")
def reports():
    today = datetime.now().date()
    default_start = (today - timedelta(days=365)).isoformat()
    start_date = request.args.get("start_date") or default_start
    end_date = request.args.get("end_date") or today.isoformat()
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT COUNT(t.ticket_id) AS total_tickets, COALESCE(SUM(f.price), 0) AS total_sales
        FROM ticket t
        JOIN flight f ON f.flight_id = t.flight_id
        WHERE f.airline_name = %s AND DATE(t.purchase_time) BETWEEN %s AND %s
        """,
        (session["airline_name"], start_date, end_date),
    )
    totals = cursor.fetchone()
    cursor.execute(
        """
        SELECT DATE_FORMAT(t.purchase_time, '%Y-%m') AS month,
               COUNT(t.ticket_id) AS tickets_sold,
               COALESCE(SUM(f.price), 0) AS sales
        FROM ticket t
        JOIN flight f ON f.flight_id = t.flight_id
        WHERE f.airline_name = %s AND DATE(t.purchase_time) BETWEEN %s AND %s
        GROUP BY month
        ORDER BY month
        """,
        (session["airline_name"], start_date, end_date),
    )
    monthly = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        "reports.html",
        totals=totals,
        monthly=monthly,
        start_date=start_date,
        end_date=end_date,
    )


if __name__ == "__main__":
    ensure_db_exists()
    app.run(debug=True)
