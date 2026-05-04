# MySQL Setup and Flight Import

This version of the app uses MySQL through `mysql-connector-python` and the Part 2 table definitions in `sql/schema.sql`.

## 1. Configure MySQL

Copy `.env.example` to `.env` and edit the credentials:

```bash
cp .env.example .env
```

Common local settings:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=air_ticket_system
```

## 2. Create/reset the database

From the `air-ticket-system` folder:

```bash
venv/bin/python -c "from app import init_db; init_db()"
```

This runs:

- `sql/schema.sql`
- `sql/seed.sql`

## 3. Import supported flights

Edit `data/supported_flights.csv`, then run:

```bash
venv/bin/python scripts/import_flights.py
```

To reset MySQL and import the CSV in one command:

```bash
venv/bin/python scripts/import_flights.py --init-db
```

Required CSV columns:

- `airline_name`
- `source_city`
- `destination_city`
- `source_airport`
- `destination_airport`
- `departure_time`
- `arrival_time`
- `price`

Optional CSV columns:

- `flight_number`
- `status`
- `airplane_id`
- `num_seats`
- `manufacturer`
- `manufacture_date`

If `airplane_id` is blank, the importer finds or creates an airplane for that airline using `num_seats` and `manufacturer`.

## 4. Run the app

```bash
venv/bin/python -m flask --app app run --port 5001
```

Demo accounts after seeding:

- Customer: `testcustomer@nyu.edu / 1234`
- Staff: `admin / abcd`
