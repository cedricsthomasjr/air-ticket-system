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
VALID_STATUSES = {"on-time", "delayed", "cancelled"}


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


def get_next_airplane_id(cursor, airline_name):
    cursor.execute(
        "SELECT COALESCE(MAX(airplane_id), 0) + 1 AS next_id FROM Airplane WHERE airline_name = %s",
        (airline_name,),
    )
    return cursor.fetchone()["next_id"]


def get_or_create_airplane(cursor, row):
    airline_name = row["airline_name"].strip()
    airplane_id = (row.get("airplane_id") or "").strip()
    if airplane_id:
        cursor.execute(
            "SELECT airplane_id FROM Airplane WHERE airline_name = %s AND airplane_id = %s",
            (airline_name, airplane_id),
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
        FROM Airplane
        WHERE airline_name = %s AND num_seats = %s AND manufacturer = %s
        LIMIT 1
        """,
        (airline_name, num_seats, manufacturer),
    )
    airplane = cursor.fetchone()
    if airplane:
        return airplane["airplane_id"]

    airplane_id = get_next_airplane_id(cursor, airline_name)
    cursor.execute(
        """
        INSERT INTO Airplane (airline_name, airplane_id, num_seats, manufacturer, manufacture_date)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (airline_name, airplane_id, num_seats, manufacturer, row.get("manufacture_date") or "2020-01-01"),
    )
    return airplane_id


def flight_exists(cursor, row, departure_time):
    cursor.execute(
        """
        SELECT 1
        FROM Flight
        WHERE airline_name = %s
          AND flight_number = %s
          AND departure_datetime = %s
        LIMIT 1
        """,
        (row["airline_name"].strip(), row["flight_number"].strip(), departure_time),
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
                status = (row.get("status") or "on-time").strip().lower()
                if status == "on time":
                    status = "on-time"
                if status not in VALID_STATUSES:
                    raise ValueError(f"Status must be one of {', '.join(sorted(VALID_STATUSES))}.")

                if not (row.get("flight_number") or "").strip():
                    row["flight_number"] = f"{airline_name[:2].upper()}{line_number:03d}"

                departure_time = parse_datetime(row["departure_time"])
                arrival_time = parse_datetime(row["arrival_time"])
                if arrival_time <= departure_time:
                    raise ValueError("Arrival time must be after departure time.")

                cursor.execute("INSERT IGNORE INTO Airline (airline_name) VALUES (%s)", (airline_name,))
                cursor.execute(
                    """
                    INSERT IGNORE INTO Airport (airport_code, city, country, airport_type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        row["source_airport"].strip().upper(),
                        row["source_city"].strip(),
                        row.get("source_country") or "USA",
                        row.get("source_airport_type") or "domestic",
                    ),
                )
                cursor.execute(
                    """
                    INSERT IGNORE INTO Airport (airport_code, city, country, airport_type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        row["destination_airport"].strip().upper(),
                        row["destination_city"].strip(),
                        row.get("destination_country") or "USA",
                        row.get("destination_airport_type") or "domestic",
                    ),
                )
                airplane_id = get_or_create_airplane(cursor, row)

                if skip_duplicates and flight_exists(cursor, row, departure_time):
                    skipped += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO Flight (
                        airline_name, flight_number, departure_datetime, departure_airport_code,
                        arrival_airport_code, arrival_datetime, base_price, status, airplane_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        airline_name,
                        row["flight_number"].strip(),
                        departure_time,
                        row["source_airport"].strip().upper(),
                        row["destination_airport"].strip().upper(),
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
    parser = argparse.ArgumentParser(description="Import supported flights from CSV into the Part 2 MySQL schema.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=os.path.join(PROJECT_ROOT, "data", "supported_flights.csv"),
        help="Path to CSV file. Defaults to data/supported_flights.csv.",
    )
    parser.add_argument("--init-db", action="store_true", help="Reset MySQL before importing.")
    parser.add_argument("--allow-duplicates", action="store_true", help="Insert duplicate flights too.")
    args = parser.parse_args()

    if args.init_db:
        init_db()

    inserted, skipped = import_flights(args.csv_path, skip_duplicates=not args.allow_duplicates)
    print(f"Imported {inserted} flight(s). Skipped {skipped} duplicate(s).")


if __name__ == "__main__":
    main()
