from datetime import datetime, timedelta
from functools import wraps
import hashlib
import os
import re

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


def drop_existing_tables(cursor):
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table_name in (
        "Rating",
        "Ticket",
        "Flight",
        "Airplane",
        "Staff_Phone",
        "Airline_Staff",
        "Customer",
        "Airport",
        "Airline",
        "review",
        "ticket",
        "flight",
        "airplane",
        "airline_staff",
        "customer",
        "airline",
    ):
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def init_db():
    db_name = os.getenv("MYSQL_DATABASE", "air_ticket_system")
    conn = get_db_connection(include_database=False)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cursor.execute(f"USE `{db_name}`")
    drop_existing_tables(cursor)
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


def format_dt(value):
    """Internal formatter — keeps the YYYY-MM-DD HH:MM:SS form used by flight_key."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def display_dt(value):
    """Human-readable datetime for templates: 'May 1, 2026 · 14:30'."""
    if isinstance(value, datetime):
        return value.strftime("%b %-d, %Y · %H:%M")
    if value:
        return str(value)
    return ""


app.jinja_env.filters["dt"] = display_dt


def parse_datetime_local(value):
    value = value.strip().replace("T", " ")
    if len(value) == 16:
        value += ":00"
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def make_flight_key(row):
    return "::".join(
        [
            row["airline_name"],
            row["flight_number"],
            format_dt(row["departure_time"]),
        ]
    )


def parse_flight_key(flight_key):
    airline_name, flight_number, departure_time = flight_key.split("::", 2)
    return airline_name, flight_number, departure_time


def normalize_flights(rows):
    for row in rows:
        row["flight_key"] = make_flight_key(row)
        row["status_label"] = row["status"].replace("-", " ").title()
    return rows


def flight_select_sql(where_clause):
    return f"""
        SELECT
            f.airline_name,
            f.flight_number,
            f.departure_datetime AS departure_time,
            f.arrival_datetime AS arrival_time,
            f.base_price AS price,
            f.status,
            f.airplane_id,
            dep.airport_code AS source_airport,
            dep.city AS source_city,
            arr.airport_code AS destination_airport,
            arr.city AS destination_city,
            a.num_seats,
            COUNT(t.ticket_id) AS tickets_sold,
            (a.num_seats - COUNT(t.ticket_id)) AS seats_available
        FROM Flight f
        JOIN Airport dep ON dep.airport_code = f.departure_airport_code
        JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
        LEFT JOIN Airplane a ON a.airline_name = f.airline_name AND a.airplane_id = f.airplane_id
        LEFT JOIN Ticket t ON t.airline_name = f.airline_name
             AND t.flight_number = f.flight_number
             AND t.departure_datetime = f.departure_datetime
        WHERE {where_clause}
        GROUP BY
            f.airline_name, f.flight_number, f.departure_datetime,
            f.arrival_datetime, f.base_price, f.status, f.airplane_id,
            dep.airport_code, dep.city, arr.airport_code, arr.city,
            a.num_seats
    """


def flight_search_query(source, destination, depart_date=None, return_date=None, airline_name=None):
    where = """
        f.departure_datetime > NOW()
        AND (dep.airport_code LIKE %s OR dep.city LIKE %s)
        AND (arr.airport_code LIKE %s OR arr.city LIKE %s)
    """
    params = [f"%{source}%", f"%{source}%", f"%{destination}%", f"%{destination}%"]
    if depart_date:
        where += " AND DATE(f.departure_datetime) = %s"
        params.append(depart_date)
    if return_date:
        where += " AND DATE(f.departure_datetime) <= %s"
        params.append(return_date)
    if airline_name:
        where += " AND f.airline_name = %s"
        params.append(airline_name)
    sql = flight_select_sql(where) + " ORDER BY f.departure_datetime ASC"
    return sql, params


def require_staff_airline_flight(cursor, airline_name, flight_number, departure_time):
    cursor.execute(
        flight_select_sql(
            """
            f.airline_name = %s
            AND f.flight_number = %s
            AND f.departure_datetime = %s
            AND f.airline_name = %s
            """
        ),
        (airline_name, flight_number, departure_time, session.get("airline_name")),
    )
    flight = cursor.fetchone()
    if flight:
        normalize_flights([flight])
    return flight


@app.route("/")
def index():
    ensure_db_exists()
    return render_template("index.html")


@app.route("/reset-db")
def reset_db():
    init_db()
    flash("MySQL database reset with your Part 2 schema and sample data.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_type") == "customer":
        return redirect(url_for("customer_home"))
    if session.get("user_type") == "staff":
        return redirect(url_for("staff_home"))
    ensure_db_exists()

    if request.method == "POST":
        user_type = request.form["user_type"]
        identifier = request.form["identifier"].strip()
        password = md5_hash(request.form["password"])

        conn = get_db_connection()
        cursor = dict_cursor(conn)

        if user_type == "customer":
            cursor.execute(
                "SELECT * FROM Customer WHERE email = %s AND password = %s",
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
                "SELECT * FROM Airline_Staff WHERE username = %s AND password = %s",
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


def normalize_phone(raw):
    """Strip all non-digit characters except a leading +."""
    raw = raw.strip()
    if raw.startswith("+"):
        return "+" + re.sub(r"\D", "", raw[1:])
    return re.sub(r"\D", "", raw)


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_type") == "customer":
        return redirect(url_for("customer_home"))
    if session.get("user_type") == "staff":
        return redirect(url_for("staff_home"))
    ensure_db_exists()
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute("SELECT airline_name FROM Airline ORDER BY airline_name")
    airlines = cursor.fetchall()

    if request.method == "POST":
        form_data = request.form

        # --- Validation (outside try so errors don't get swallowed) ---
        if request.form.get("password") != request.form.get("confirm_password"):
            flash("Passwords do not match.")
            cursor.close()
            conn.close()
            return render_template("register.html", airlines=airlines, form_data=form_data)

        user_type = request.form.get("user_type", "customer")

        if user_type == "customer":
            required = ["email", "name", "phone_number",
                        "passport_number", "passport_expiration",
                        "passport_country", "date_of_birth"]
            if not all(request.form.get(f, "").strip() for f in required):
                flash("Please fill in all required fields (marked with *).")
                cursor.close()
                conn.close()
                return render_template("register.html", airlines=airlines, form_data=form_data)
        else:
            required = ["username", "first_name", "last_name",
                        "date_of_birth", "airline_name", "staff_email",
                        "staff_phone_number"]
            if not all(request.form.get(f, "").strip() for f in required):
                flash("Please fill in all required fields (marked with *).")
                cursor.close()
                conn.close()
                return render_template("register.html", airlines=airlines, form_data=form_data)

        # --- Insert ---
        password = md5_hash(request.form["password"])
        try:
            if user_type == "customer":
                phone = normalize_phone(request.form.get("phone_number", ""))
                cursor.execute(
                    """
                    INSERT INTO Customer (
                        email, password, name, building_number, street, city, state,
                        phone_number, passport_number, passport_expiration,
                        passport_country, date_of_birth
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request.form["email"].strip(),
                        password,
                        request.form["name"].strip(),
                        request.form.get("building_number", "").strip() or None,
                        request.form.get("street", "").strip() or None,
                        request.form.get("city", "").strip() or None,
                        request.form.get("state", "").strip() or None,
                        phone or None,
                        request.form["passport_number"].strip(),
                        request.form["passport_expiration"],
                        request.form["passport_country"].strip(),
                        request.form["date_of_birth"],
                    ),
                )
            else:
                username = request.form["username"].strip()
                staff_phone = normalize_phone(request.form.get("staff_phone_number", ""))
                cursor.execute(
                    """
                    INSERT INTO Airline_Staff
                    (username, password, first_name, last_name, date_of_birth, email, airline_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        username,
                        password,
                        request.form["first_name"].strip(),
                        request.form["last_name"].strip(),
                        request.form["date_of_birth"],
                        request.form["staff_email"].strip(),
                        request.form["airline_name"],
                    ),
                )
                cursor.execute(
                    "INSERT INTO Staff_Phone (username, phone_number) VALUES (%s, %s)",
                    (username, staff_phone),
                )
            conn.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            conn.rollback()
            flash("That email or username is already registered.")
        except Exception as e:
            conn.rollback()
            flash(f"Registration failed: {e}")
        finally:
            cursor.close()
            conn.close()
        return render_template("register.html", airlines=airlines, form_data=form_data)

    cursor.close()
    conn.close()
    return render_template("register.html", airlines=airlines, form_data=None)


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
    flights = normalize_flights(cursor.fetchall())
    cursor.close()
    conn.close()
    return render_template("public_search.html", flights=flights)


@app.route("/logout")
def logout():
    session.clear()
    return render_template("goodbye.html")


@app.route("/customer/home")
@login_required(role="customer")
def customer_home():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        flight_select_sql(
            """
            EXISTS (
                SELECT 1 FROM Ticket t
                WHERE t.airline_name = f.airline_name
                  AND t.flight_number = f.flight_number
                  AND t.departure_datetime = f.departure_datetime
                  AND t.customer_email = %s
            )
            AND f.departure_datetime > NOW()
            """
        )
        + " ORDER BY f.departure_datetime ASC LIMIT 5",
        (session["user_id"],),
    )
    upcoming = normalize_flights(cursor.fetchall())
    cursor.close()
    conn.close()
    return render_template("customer_home.html", name=session.get("display_name"), upcoming=upcoming)


@app.route("/staff/home")
@login_required(role="staff")
def staff_home():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT COUNT(*) AS upcoming_flights
        FROM Flight
        WHERE airline_name = %s AND departure_datetime > NOW()
        """,
        (session["airline_name"],),
    )
    upcoming_flights = cursor.fetchone()["upcoming_flights"]
    cursor.execute(
        "SELECT COUNT(*) AS fleet_count, COALESCE(SUM(num_seats), 0) AS total_seats FROM Airplane WHERE airline_name = %s",
        (session["airline_name"],),
    )
    fleet = cursor.fetchone()
    cursor.execute(
        """
        SELECT COUNT(t.ticket_id) AS recent_tickets, COALESCE(SUM(f.base_price), 0) AS recent_sales
        FROM Ticket t
        JOIN Flight f ON f.airline_name = t.airline_name
             AND f.flight_number = t.flight_number
             AND f.departure_datetime = t.departure_datetime
        WHERE f.airline_name = %s AND t.purchase_datetime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """,
        (session["airline_name"],),
    )
    recent_sales = cursor.fetchone()
    cursor.execute(
        """
        SELECT AVG(r.rating) AS avg_rating
        FROM Rating r
        WHERE r.airline_name = %s
        """,
        (session["airline_name"],),
    )
    avg_rating = cursor.fetchone()["avg_rating"]
    cursor.close()
    conn.close()
    return render_template(
        "staff_home.html",
        name=session.get("display_name"),
        airline=session.get("airline_name"),
        upcoming_flights=upcoming_flights,
        fleet=fleet,
        recent_sales=recent_sales,
        avg_rating=avg_rating,
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
    flights = normalize_flights(cursor.fetchall())
    cursor.close()
    conn.close()

    return render_template("search_flights.html", flights=flights)


@app.route("/customer/my-flights")
@login_required(role="customer")
def my_flights():
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    where = """
        EXISTS (
            SELECT 1 FROM Ticket t
            WHERE t.airline_name = f.airline_name
              AND t.flight_number = f.flight_number
              AND t.departure_datetime = f.departure_datetime
              AND t.customer_email = %s
        )
    """
    params = [session["user_id"]]
    # Spec: default view is future flights only; date filters override this
    if not start_date and not end_date:
        where += " AND f.departure_datetime > NOW()"
    if start_date:
        where += " AND DATE(f.departure_datetime) >= %s"
        params.append(start_date)
    if end_date:
        where += " AND DATE(f.departure_datetime) <= %s"
        params.append(end_date)
    if source:
        where += " AND (dep.airport_code LIKE %s OR dep.city LIKE %s)"
        params.extend([f"%{source}%", f"%{source}%"])
    if destination:
        where += " AND (arr.airport_code LIKE %s OR arr.city LIKE %s)"
        params.extend([f"%{destination}%", f"%{destination}%"])

    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        flight_select_sql(where)
        + " ORDER BY f.departure_datetime ASC",
        params,
    )
    flights = normalize_flights(cursor.fetchall())
    cursor.close()
    conn.close()
    return render_template("my_flights.html", flights=flights, now=datetime.now())


@app.route("/customer/ratings")
@login_required(role="customer")
def ratings():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT
            f.airline_name,
            f.flight_number,
            f.departure_datetime AS departure_time,
            f.arrival_datetime AS arrival_time,
            f.base_price AS price,
            f.status,
            dep.airport_code AS source_airport,
            dep.city AS source_city,
            arr.airport_code AS destination_airport,
            arr.city AS destination_city,
            r.rating,
            r.comment
        FROM Ticket t
        JOIN Flight f ON f.airline_name = t.airline_name
             AND f.flight_number = t.flight_number
             AND f.departure_datetime = t.departure_datetime
        JOIN Airport dep ON dep.airport_code = f.departure_airport_code
        JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
        LEFT JOIN Rating r ON r.airline_name = f.airline_name
             AND r.flight_number = f.flight_number
             AND r.departure_datetime = f.departure_datetime
             AND r.customer_email = t.customer_email
        WHERE t.customer_email = %s AND f.departure_datetime < NOW()
        ORDER BY f.departure_datetime DESC
        """,
        (session["user_id"],),
    )
    past_flights = normalize_flights(cursor.fetchall())
    cursor.close()
    conn.close()
    return render_template("ratings.html", flights=past_flights)


@app.route("/customer/purchase", methods=["POST"])
@app.route("/customer/purchase/<path:flight_key>", methods=["POST"])
@login_required(role="customer")
def purchase_ticket(flight_key=None):
    if flight_key:
        airline_name, flight_number, departure_time = parse_flight_key(flight_key)
    else:
        airline_name = request.form["airline_name"]
        flight_number = request.form["flight_number"]
        departure_time = request.form["departure_datetime"]

    payment_fields = ["card_type", "card_number", "name_on_card", "card_expiration"]
    if not all(request.form.get(field, "").strip() for field in payment_fields):
        flash("Payment information is required to purchase a ticket.")
        return redirect(request.referrer or url_for("search_flights"))

    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        flight_select_sql(
            """
            f.airline_name = %s
            AND f.flight_number = %s
            AND f.departure_datetime = %s
            AND f.departure_datetime > NOW()
            """
        ),
        (airline_name, flight_number, departure_time),
    )
    flight = cursor.fetchone()
    if not flight:
        flash("That future flight is not available for purchase.")
    elif flight["tickets_sold"] >= flight["num_seats"]:
        flash("That flight is sold out.")
    else:
        cursor.execute(
            """
            SELECT 1 FROM Ticket
            WHERE customer_email = %s
              AND airline_name = %s
              AND flight_number = %s
              AND departure_datetime = %s
            """,
            (session["user_id"], airline_name, flight_number, departure_time),
        )
        if cursor.fetchone():
            flash("You already purchased a ticket for that flight.")
        else:
            cursor.execute(
                """
                INSERT INTO Ticket (
                    customer_email, airline_name, flight_number, departure_datetime,
                    card_type, card_number, name_on_card, card_expiration, purchase_datetime
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    session["user_id"],
                    airline_name,
                    flight_number,
                    departure_time,
                    request.form["card_type"],
                    request.form["card_number"].strip(),
                    request.form["name_on_card"].strip(),
                    request.form["card_expiration"],
                ),
            )
            conn.commit()
            flash("Ticket purchased successfully.")
    cursor.close()
    conn.close()
    return redirect(request.referrer or url_for("my_flights"))


@app.route("/customer/review/<path:flight_key>", methods=["POST"])
@login_required(role="customer")
def review_flight(flight_key):
    airline_name, flight_number, departure_time = parse_flight_key(flight_key)
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT 1
        FROM Ticket t
        JOIN Flight f ON f.airline_name = t.airline_name
             AND f.flight_number = t.flight_number
             AND f.departure_datetime = t.departure_datetime
        WHERE t.customer_email = %s
          AND f.airline_name = %s
          AND f.flight_number = %s
          AND f.departure_datetime = %s
          AND f.departure_datetime < NOW()
        """,
        (session["user_id"], airline_name, flight_number, departure_time),
    )
    if not cursor.fetchone():
        flash("You can only review past flights you purchased.")
    else:
        cursor.execute(
            """
            INSERT INTO Rating (customer_email, airline_name, flight_number, departure_datetime, rating, comment)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                rating = VALUES(rating),
                comment = VALUES(comment)
            """,
            (
                session["user_id"],
                airline_name,
                flight_number,
                departure_time,
                int(request.form["rating"]),
                request.form.get("comment", "").strip(),
            ),
        )
        conn.commit()
        flash("Review saved.")
    cursor.close()
    conn.close()
    return redirect(request.referrer or url_for("ratings"))


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
        flight_select_sql(
            """
            f.airline_name = %s
            AND DATE(f.departure_datetime) BETWEEN %s AND %s
            AND (dep.airport_code LIKE %s OR dep.city LIKE %s)
            AND (arr.airport_code LIKE %s OR arr.city LIKE %s)
            """
        )
        + " ORDER BY f.departure_datetime ASC",
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
    flights = normalize_flights(cursor.fetchall())
    # Attach avg ratings to each flight
    cursor.execute(
        """
        SELECT flight_number, departure_datetime,
               ROUND(AVG(rating), 1) AS avg_rating,
               COUNT(rating)         AS review_count
        FROM Rating
        WHERE airline_name = %s
        GROUP BY flight_number, departure_datetime
        """,
        (session["airline_name"],),
    )
    rating_map = {
        (r["flight_number"], r["departure_datetime"]): r
        for r in cursor.fetchall()
    }
    for f in flights:
        r = rating_map.get((f["flight_number"], f["departure_time"]), {})
        f["avg_rating"]   = r.get("avg_rating")
        f["review_count"] = r.get("review_count", 0)
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
        """
        SELECT airplane_id, manufacturer, num_seats
        FROM Airplane
        WHERE airline_name = %s
        ORDER BY airplane_id
        """,
        (session["airline_name"],),
    )
    airplanes = cursor.fetchall()
    cursor.execute("SELECT airport_code, city, country FROM Airport ORDER BY airport_code")
    airports = cursor.fetchall()

    if request.method == "POST":
        try:
            departure_airport = (
                request.form.get("departure_airport_code")
                or request.form.get("source")
                or ""
            ).strip().upper()
            arrival_airport = (
                request.form.get("arrival_airport_code")
                or request.form.get("destination")
                or ""
            ).strip().upper()
            departure_time = parse_datetime_local(request.form["departure_time"])
            arrival_time = parse_datetime_local(request.form["arrival_time"])
            flight_number = request.form["flight_number"].strip().upper()
            base_price = request.form["price"]
            airplane_id = request.form["airplane_id"]
            status = request.form.get("status", "on-time")
            if status not in ("on-time", "delayed", "cancelled"):
                raise ValueError("Status must be on-time, delayed, or cancelled.")
            if not flight_number:
                raise ValueError("Flight number is required.")
            if departure_airport == arrival_airport:
                raise ValueError("Departure and arrival airports must be different.")
            if arrival_time <= departure_time:
                raise ValueError("Arrival time must be after departure time.")
            if float(base_price) < 0:
                raise ValueError("Base price cannot be negative.")
        except (KeyError, ValueError):
            flash("Please enter a valid flight number, route, schedule, status, and price.")
            cursor.close()
            conn.close()
            return redirect(url_for("create_flight"))

        cursor.execute(
            "SELECT 1 FROM Airplane WHERE airline_name = %s AND airplane_id = %s",
            (session["airline_name"], airplane_id),
        )
        if not cursor.fetchone():
            flash("You can only assign airplanes owned by your airline.")
            cursor.close()
            conn.close()
            return redirect(url_for("create_flight"))

        cursor.execute(
            "SELECT airport_code FROM Airport WHERE airport_code IN (%s, %s)",
            (departure_airport, arrival_airport),
        )
        existing_airports = {row["airport_code"] for row in cursor.fetchall()}
        if {departure_airport, arrival_airport} - existing_airports:
            flash("Both departure and arrival airport codes must already exist.")
            cursor.close()
            conn.close()
            return redirect(url_for("create_flight"))

        try:
            cursor.execute(
                """
                INSERT INTO Flight (
                    airline_name, flight_number, departure_datetime, departure_airport_code,
                    arrival_airport_code, arrival_datetime, base_price, status, airplane_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session["airline_name"],
                    flight_number,
                    departure_time,
                    departure_airport,
                    arrival_airport,
                    arrival_time,
                    base_price,
                    status,
                    airplane_id,
                ),
            )
            conn.commit()
            flash("Flight created successfully.")
            return redirect(url_for("staff_flights"))
        except mysql.connector.IntegrityError:
            conn.rollback()
            flash("A flight with that airline, flight number, and departure time already exists.")

    cursor.close()
    conn.close()
    return render_template("create_flight.html", airplanes=airplanes, airports=airports)


@app.route("/staff/flight/<airline_name>/<flight_number>/<path:departure_datetime>")
@login_required(role="staff")
def staff_flight_detail(airline_name, flight_number, departure_datetime):
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    flight = require_staff_airline_flight(cursor, airline_name, flight_number, departure_datetime)
    if not flight:
        cursor.close()
        conn.close()
        flash("Flight not found for your airline.")
        return redirect(url_for("staff_flights"))
    cursor.execute(
        """
        SELECT c.email, c.name, c.phone_number, t.purchase_datetime
        FROM Ticket t
        JOIN Customer c ON c.email = t.customer_email
        WHERE t.airline_name = %s AND t.flight_number = %s AND t.departure_datetime = %s
        ORDER BY t.purchase_datetime DESC
        """,
        (airline_name, flight_number, departure_datetime),
    )
    customers = cursor.fetchall()
    cursor.execute(
        """
        SELECT r.rating, r.comment, c.name, c.email
        FROM Rating r
        JOIN Customer c ON c.email = r.customer_email
        WHERE r.airline_name = %s AND r.flight_number = %s AND r.departure_datetime = %s
        ORDER BY r.rating DESC
        """,
        (airline_name, flight_number, departure_datetime),
    )
    reviews = cursor.fetchall()
    cursor.execute(
        """
        SELECT AVG(rating) AS avg_rating
        FROM Rating
        WHERE airline_name = %s AND flight_number = %s AND departure_datetime = %s
        """,
        (airline_name, flight_number, departure_datetime),
    )
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


@app.route("/staff/update-status/<airline_name>/<flight_number>/<path:departure_datetime>", methods=["POST"])
@login_required(role="staff")
def update_status(airline_name, flight_number, departure_datetime):
    status = request.form["status"]
    if status not in ("on-time", "delayed", "cancelled"):
        flash("Invalid status.")
        return redirect(url_for("staff_flights"))
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    flight = require_staff_airline_flight(cursor, airline_name, flight_number, departure_datetime)
    if not flight:
        flash("You can only update flights for your airline.")
    else:
        cursor.execute(
            """
            UPDATE Flight
            SET status = %s
            WHERE airline_name = %s AND flight_number = %s AND departure_datetime = %s
            """,
            (status, airline_name, flight_number, departure_datetime),
        )
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
        try:
            num_seats = int(request.form["num_seats"])
            if num_seats <= 0:
                raise ValueError
            manufacture_date = request.form["manufacture_date"]
            if not manufacture_date:
                raise ValueError
            cursor.execute(
                "SELECT COALESCE(MAX(airplane_id), 0) + 1 AS next_id FROM Airplane WHERE airline_name = %s",
                (session["airline_name"],),
            )
            airplane_id = cursor.fetchone()["next_id"]
            cursor.execute(
                """
                INSERT INTO Airplane (airline_name, airplane_id, num_seats, manufacturer, manufacture_date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    session["airline_name"],
                    airplane_id,
                    num_seats,
                    request.form.get("manufacturer", "").strip() or "Unknown",
                    manufacture_date,
                ),
            )
            conn.commit()
            flash(f"Airplane {airplane_id} added.")
        except ValueError:
            conn.rollback()
            flash("Please enter a positive seat count and manufacture date.")
    cursor.execute(
        "SELECT * FROM Airplane WHERE airline_name = %s ORDER BY airplane_id",
        (session["airline_name"],),
    )
    airplanes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("add_airplane.html", airplanes=airplanes)


@app.route("/staff/add-airport", methods=["GET", "POST"])
@login_required(role="staff")
def add_airport():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    if request.method == "POST":
        airport_code = request.form.get("airport_code", "").strip().upper()
        city = request.form.get("city", "").strip()
        country = request.form.get("country", "").strip()
        airport_type = request.form.get("airport_type", "").strip().lower()
        if len(airport_code) != 3 or not city or not country or not airport_type:
            flash("Airport code, city, country, and type are required.")
        else:
            try:
                cursor.execute(
                    """
                    INSERT INTO Airport (airport_code, city, country, airport_type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (airport_code, city, country, airport_type),
                )
                conn.commit()
                flash(f"Airport {airport_code} added.")
            except mysql.connector.IntegrityError:
                conn.rollback()
                flash("That airport code already exists.")
    cursor.execute("SELECT * FROM Airport ORDER BY airport_code")
    airports = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("add_airport.html", airports=airports)


@app.route("/staff/customers")
@login_required(role="staff")
def staff_customers():
    today = datetime.now().date()
    raw_start  = request.args.get("start_date", "").strip()
    raw_end    = request.args.get("end_date",   "").strip()
    start_date = raw_start or "2000-01-01"
    end_date   = raw_end   or today.isoformat()

    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute(
        """
        SELECT c.email, c.name, c.phone_number, COUNT(t.ticket_id) AS tickets_purchased,
               MAX(t.purchase_datetime) AS last_purchase
        FROM Ticket t
        JOIN Customer c ON c.email = t.customer_email
        JOIN Flight f ON f.airline_name = t.airline_name
             AND f.flight_number = t.flight_number
             AND f.departure_datetime = t.departure_datetime
        WHERE f.airline_name = %s
          AND DATE(t.purchase_datetime) BETWEEN %s AND %s
        GROUP BY c.email, c.name, c.phone_number
        ORDER BY tickets_purchased DESC, last_purchase DESC
        """,
        (session["airline_name"], start_date, end_date),
    )
    customers = cursor.fetchall()
    frequent_customer = customers[0] if customers else None
    cursor.close()
    conn.close()
    return render_template(
        "staff_customers.html",
        customers=customers,
        frequent_customer=frequent_customer,
        start_date=raw_start,
        end_date=raw_end,
    )


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
        SELECT COUNT(t.ticket_id) AS total_tickets, COALESCE(SUM(f.base_price), 0) AS total_sales
        FROM Ticket t
        JOIN Flight f ON f.airline_name = t.airline_name
             AND f.flight_number = t.flight_number
             AND f.departure_datetime = t.departure_datetime
        WHERE f.airline_name = %s AND DATE(t.purchase_datetime) BETWEEN %s AND %s
        """,
        (session["airline_name"], start_date, end_date),
    )
    totals = cursor.fetchone()
    cursor.execute(
        """
        SELECT DATE_FORMAT(t.purchase_datetime, '%Y-%m') AS month,
               COUNT(t.ticket_id) AS tickets_sold,
               COALESCE(SUM(f.base_price), 0) AS sales
        FROM Ticket t
        JOIN Flight f ON f.airline_name = t.airline_name
             AND f.flight_number = t.flight_number
             AND f.departure_datetime = t.departure_datetime
        WHERE f.airline_name = %s AND DATE(t.purchase_datetime) BETWEEN %s AND %s
        GROUP BY month
        ORDER BY month
        """,
        (session["airline_name"], start_date, end_date),
    )
    monthly = cursor.fetchall()
    cursor.execute(
        """
        SELECT CONCAT(dep.airport_code, ' to ', arr.airport_code) AS route,
               COUNT(t.ticket_id) AS tickets_sold,
               COALESCE(SUM(f.base_price), 0) AS sales
        FROM Ticket t
        JOIN Flight f ON f.airline_name = t.airline_name
             AND f.flight_number = t.flight_number
             AND f.departure_datetime = t.departure_datetime
        JOIN Airport dep ON dep.airport_code = f.departure_airport_code
        JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
        WHERE f.airline_name = %s AND DATE(t.purchase_datetime) BETWEEN %s AND %s
        GROUP BY route
        ORDER BY tickets_sold DESC, sales DESC
        LIMIT 5
        """,
        (session["airline_name"], start_date, end_date),
    )
    top_routes = cursor.fetchall()
    cursor.execute(
        """
        SELECT c.email, c.name, COUNT(t.ticket_id) AS tickets_sold
        FROM Ticket t
        JOIN Customer c ON c.email = t.customer_email
        JOIN Flight f ON f.airline_name = t.airline_name
             AND f.flight_number = t.flight_number
             AND f.departure_datetime = t.departure_datetime
        WHERE f.airline_name = %s AND DATE(t.purchase_datetime) BETWEEN %s AND %s
        GROUP BY c.email, c.name
        ORDER BY tickets_sold DESC, c.name
        LIMIT 5
        """,
        (session["airline_name"], start_date, end_date),
    )
    top_customers = cursor.fetchall()
    cursor.execute(
        """
        SELECT status, COUNT(*) AS flight_count
        FROM Flight
        WHERE airline_name = %s
        GROUP BY status
        ORDER BY status
        """,
        (session["airline_name"],),
    )
    status_counts = cursor.fetchall()
    # Rating stats for this airline (all time, not date-filtered)
    cursor.execute(
        """
        SELECT
            COALESCE(AVG(rating), 0)                                    AS avg_rating,
            COUNT(rating)                                               AS total_reviews,
            SUM(rating = 5)                                             AS five_star,
            SUM(rating = 4)                                             AS four_star,
            SUM(rating = 3)                                             AS three_star,
            SUM(rating = 2)                                             AS two_star,
            SUM(rating = 1)                                             AS one_star
        FROM Rating
        WHERE airline_name = %s
        """,
        (session["airline_name"],),
    )
    rating_stats = cursor.fetchone()
    # Per-flight average — most recent 10 rated flights
    cursor.execute(
        """
        SELECT r.flight_number,
               CONCAT(dep.airport_code, ' → ', arr.airport_code) AS route,
               DATE(r.departure_datetime)                              AS flight_date,
               ROUND(AVG(r.rating), 1)                                AS avg_rating,
               COUNT(r.rating)                                        AS review_count
        FROM Rating r
        JOIN Flight f   ON f.airline_name       = r.airline_name
                       AND f.flight_number      = r.flight_number
                       AND f.departure_datetime = r.departure_datetime
        JOIN Airport dep ON dep.airport_code = f.departure_airport_code
        JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
        WHERE r.airline_name = %s
        GROUP BY r.flight_number, r.departure_datetime, route
        ORDER BY r.departure_datetime DESC
        LIMIT 10
        """,
        (session["airline_name"],),
    )
    flight_ratings = cursor.fetchall()
    # Individual reviews — most recent 15
    cursor.execute(
        """
        SELECT r.rating,
               r.comment,
               c.name                                                  AS customer_name,
               r.flight_number,
               CONCAT(dep.airport_code, ' → ', arr.airport_code) AS route,
               DATE(r.departure_datetime)                              AS flight_date
        FROM Rating r
        JOIN Customer c ON c.email = r.customer_email
        JOIN Flight f   ON f.airline_name       = r.airline_name
                       AND f.flight_number      = r.flight_number
                       AND f.departure_datetime = r.departure_datetime
        JOIN Airport dep ON dep.airport_code = f.departure_airport_code
        JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
        WHERE r.airline_name = %s
        ORDER BY r.departure_datetime DESC
        LIMIT 15
        """,
        (session["airline_name"],),
    )
    recent_reviews = cursor.fetchall()
    chart_months = [row["month"] for row in monthly]
    chart_tickets = [int(row["tickets_sold"]) for row in monthly]
    cursor.close()
    conn.close()
    return render_template(
        "reports.html",
        totals=totals,
        monthly=monthly,
        top_routes=top_routes,
        top_customers=top_customers,
        status_counts=status_counts,
        rating_stats=rating_stats,
        flight_ratings=flight_ratings,
        recent_reviews=recent_reviews,
        chart_months=chart_months,
        chart_tickets=chart_tickets,
        start_date=start_date,
        end_date=end_date,
    )


if __name__ == "__main__":
    ensure_db_exists()
    port = int(os.getenv("FLASK_RUN_PORT", os.getenv("PORT", "5001")))
    app.run(debug=True, port=port)
