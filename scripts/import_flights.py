import argparse
import csv
from datetime import datetime
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app import get_db_connection, init_db


REQUIRED_COLUMNS = {
    "airline_name",
    "source_city",
    "destination_city",
    "source_airport",
    "destination_airport",
    "departure_time",
    "arrival_time",
    "price",
}
VALID_STATUSES = {"On Time", "Delayed", "Cancelled"}


def parse_datetime(value):
    value = value.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    raise ValueError(f"Invalid datetime '{value}'. Use YYYY-MM-DD HH:MM:SS.")


def validate_columns(fieldnames):
    missing = REQUIRED_COLUMNS - set(fieldnames or [])
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")


def get_or_create_airplane(cursor, row):
    airplane_id = (row.get("airplane_id") or "").strip()
    airline_name = row["airline_name"].strip()
    if airplane_id:
        cursor.execute(
            "SELECT airplane_id FROM airplane WHERE airplane_id = %s AND airline_name = %s",
            (airplane_id, airline_name),
        )
        airplane = cursor.fetchone()
        if not airplane:
            raise ValueError(f"Airplane {airplane_id} does not belong to {airline_name}.")
        return airplane["airplane_id"]

    num_seats = int((row.get("num_seats") or "180").strip())
    manufacturer = (row.get("manufacturer") or "Unknown").strip()
    cursor.execute(
        """
        SELECT airplane_id
        FROM airplane
        WHERE airline_name = %s AND num_seats = %s AND manufacturer = %s
        LIMIT 1
        """,
        (airline_name, num_seats, manufacturer),
    )
    airplane = cursor.fetchone()
    if airplane:
        return airplane["airplane_id"]

    cursor.execute(
        "INSERT INTO airplane (airline_name, num_seats, manufacturer) VALUES (%s, %s, %s)",
        (airline_name, num_seats, manufacturer),
    )
    return cursor.lastrowid


def flight_exists(cursor, row, departure_time):
    cursor.execute(
        """
        SELECT flight_id
        FROM flight
        WHERE airline_name = %s
          AND source_airport = %s
          AND destination_airport = %s
          AND departure_time = %s
        LIMIT 1
        """,
        (
            row["airline_name"].strip(),
            row["source_airport"].strip().upper(),
            row["destination_airport"].strip().upper(),
            departure_time,
        ),
    )
    return cursor.fetchone() is not None


def import_flights(csv_path, skip_duplicates=True):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    inserted = 0
    skipped = 0

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        validate_columns(reader.fieldnames)

        for line_number, row in enumerate(reader, start=2):
            try:
                airline_name = row["airline_name"].strip()
                status = (row.get("status") or "On Time").strip()
                if status not in VALID_STATUSES:
                    raise ValueError(f"Status must be one of {', '.join(sorted(VALID_STATUSES))}.")

                departure_time = parse_datetime(row["departure_time"])
                arrival_time = parse_datetime(row["arrival_time"])
                if arrival_time <= departure_time:
                    raise ValueError("Arrival time must be after departure time.")

                cursor.execute(
                    "INSERT IGNORE INTO airline (airline_name) VALUES (%s)",
                    (airline_name,),
                )
                airplane_id = get_or_create_airplane(cursor, row)

                if skip_duplicates and flight_exists(cursor, row, departure_time):
                    skipped += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO flight (
                        airline_name, source_city, destination_city, source_airport, destination_airport,
                        departure_time, arrival_time, price, status, airplane_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        airline_name,
                        row["source_city"].strip(),
                        row["destination_city"].strip(),
                        row["source_airport"].strip().upper(),
                        row["destination_airport"].strip().upper(),
                        departure_time,
                        arrival_time,
                        row["price"].strip(),
                        status,
                        airplane_id,
                    ),
                )
                inserted += 1
            except Exception as exc:
                conn.rollback()
                cursor.close()
                conn.close()
                raise ValueError(f"Line {line_number}: {exc}") from exc

    conn.commit()
    cursor.close()
    conn.close()
    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(description="Import supported flights from CSV into MySQL.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=os.path.join(PROJECT_ROOT, "data", "supported_flights.csv"),
        help="Path to CSV file. Defaults to data/supported_flights.csv.",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Create/reset the MySQL database from sql/schema.sql and sql/seed.sql before importing.",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Insert flights even if the same airline, route, and departure time already exists.",
    )
    args = parser.parse_args()

    if args.init_db:
        init_db()

    inserted, skipped = import_flights(args.csv_path, skip_duplicates=not args.allow_duplicates)
    print(f"Imported {inserted} flight(s). Skipped {skipped} duplicate(s).")


if __name__ == "__main__":
    main()
