# Use Cases and SQL Queries

This document explains the main application use cases and the SQL queries executed by each use case. All user-controlled values are passed through MySQL Connector parameter placeholders (`%s`) rather than string formatting.

## Shared Database Helpers

### Database Connection

The app reads MySQL settings from environment variables and opens connections with `mysql.connector.connect`.

### Database Initialization

Use case: create or reset the database.

Executed by:

- App startup if the configured database does not exist.
- `/reset-db`.

Queries:

```sql
CREATE DATABASE IF NOT EXISTS `<MYSQL_DATABASE>`;
USE `<MYSQL_DATABASE>`;
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `<table_name>`;
SET FOREIGN_KEY_CHECKS = 1;
```

Then the app executes every statement in:

- `sql/schema.sql`
- `sql/seed.sql`

Explanation: this rebuilds the MySQL database using the Part 2 schema and loads demo data.

### Reusable Flight Selection Query

Many pages use the same flight query shape, with a different `WHERE` clause.

```sql
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
LEFT JOIN Airplane a
    ON a.airline_name = f.airline_name
   AND a.airplane_id = f.airplane_id
LEFT JOIN Ticket t
    ON t.airline_name = f.airline_name
   AND t.flight_number = f.flight_number
   AND t.departure_datetime = f.departure_datetime
WHERE <route-specific conditions>
GROUP BY
    f.airline_name, f.flight_number, f.departure_datetime,
    f.arrival_datetime, f.base_price, f.status, f.airplane_id,
    dep.airport_code, dep.city, arr.airport_code, arr.city,
    a.num_seats;
```

Explanation: this returns display-ready flight data, airport city/code data, airplane capacity, sold tickets, and remaining seats.

## Public Use Cases

### View Home Page

Route: `/`

Queries:

- No page-specific query.
- Calls `ensure_db_exists()`, which may initialize the database if it does not exist.

Explanation: displays the public home page.

### Search Public Flight Information

Route: `/public/search`

Query:

```sql
SELECT ...
FROM Flight f
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
LEFT JOIN Airplane a
    ON a.airline_name = f.airline_name
   AND a.airplane_id = f.airplane_id
LEFT JOIN Ticket t
    ON t.airline_name = f.airline_name
   AND t.flight_number = f.flight_number
   AND t.departure_datetime = f.departure_datetime
WHERE f.departure_datetime > NOW()
  AND (dep.airport_code LIKE %s OR dep.city LIKE %s)
  AND (arr.airport_code LIKE %s OR arr.city LIKE %s)
  AND DATE(f.departure_datetime) = %s              -- optional
  AND DATE(f.departure_datetime) <= %s             -- optional return-date upper bound
GROUP BY ...
ORDER BY f.departure_datetime ASC;
```

Explanation: anonymous users can search future flights by source/destination airport code or city and optional dates.

## Authentication Use Cases

### Register Customer

Route: `/register`

Lookup query used to populate staff airline options:

```sql
SELECT airline_name
FROM Airline
ORDER BY airline_name;
```

Insert query:

```sql
INSERT INTO Customer (
    email, password, name, building_number, street, city, state,
    phone_number, passport_number, passport_expiration,
    passport_country, date_of_birth
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
```

Explanation: stores the customer profile and passport data. Passwords are hashed in Python with MD5 before insertion.

### Register Airline Staff

Route: `/register`

Staff insert:

```sql
INSERT INTO Airline_Staff
    (username, password, first_name, last_name, date_of_birth, email, airline_name)
VALUES (%s, %s, %s, %s, %s, %s, %s);
```

Staff phone insert:

```sql
INSERT INTO Staff_Phone (username, phone_number)
VALUES (%s, %s);
```

Explanation: creates a staff account tied to one airline and stores the staff phone number in the separate `Staff_Phone` table.

### Login Customer

Route: `/login`

Query:

```sql
SELECT *
FROM Customer
WHERE email = %s AND password = %s;
```

Explanation: validates customer email/password and stores customer session fields.

### Login Airline Staff

Route: `/login`

Query:

```sql
SELECT *
FROM Airline_Staff
WHERE username = %s AND password = %s;
```

Explanation: validates staff username/password and stores staff session fields, including the staff member's airline.

### Logout

Route: `/logout`

Queries:

- No SQL query.

Explanation: clears the Flask session and renders the goodbye page.

## Customer Use Cases

### View Customer Home

Route: `/customer/home`

Query:

```sql
SELECT ...
FROM Flight f
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
LEFT JOIN Airplane a
    ON a.airline_name = f.airline_name
   AND a.airplane_id = f.airplane_id
LEFT JOIN Ticket t
    ON t.airline_name = f.airline_name
   AND t.flight_number = f.flight_number
   AND t.departure_datetime = f.departure_datetime
WHERE EXISTS (
    SELECT 1
    FROM Ticket t
    WHERE t.airline_name = f.airline_name
      AND t.flight_number = f.flight_number
      AND t.departure_datetime = f.departure_datetime
      AND t.customer_email = %s
)
AND f.departure_datetime > NOW()
GROUP BY ...
ORDER BY f.departure_datetime ASC
LIMIT 5;
```

Explanation: shows the customer's next five upcoming purchased flights.

### Search Flights as Customer

Route: `/customer/search`

Query: same as public flight search.

Explanation: logged-in customers search future flights and can purchase from the result cards.

### Purchase Ticket

Route: `/customer/purchase`

Flight availability query:

```sql
SELECT ...
FROM Flight f
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
LEFT JOIN Airplane a
    ON a.airline_name = f.airline_name
   AND a.airplane_id = f.airplane_id
LEFT JOIN Ticket t
    ON t.airline_name = f.airline_name
   AND t.flight_number = f.flight_number
   AND t.departure_datetime = f.departure_datetime
WHERE f.airline_name = %s
  AND f.flight_number = %s
  AND f.departure_datetime = %s
  AND f.departure_datetime > NOW()
GROUP BY ...;
```

Duplicate purchase check:

```sql
SELECT 1
FROM Ticket
WHERE customer_email = %s
  AND airline_name = %s
  AND flight_number = %s
  AND departure_datetime = %s;
```

Ticket insert:

```sql
INSERT INTO Ticket (
    customer_email, airline_name, flight_number, departure_datetime,
    card_type, card_number, name_on_card, card_expiration, purchase_datetime
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW());
```

Explanation: checks that the flight exists, is in the future, has remaining seats, and has not already been purchased by the same customer before inserting the ticket and payment information.

### View My Flights

Route: `/customer/my-flights`

Query:

```sql
SELECT ...
FROM Flight f
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
LEFT JOIN Airplane a
    ON a.airline_name = f.airline_name
   AND a.airplane_id = f.airplane_id
LEFT JOIN Ticket t
    ON t.airline_name = f.airline_name
   AND t.flight_number = f.flight_number
   AND t.departure_datetime = f.departure_datetime
WHERE EXISTS (
    SELECT 1
    FROM Ticket t
    WHERE t.airline_name = f.airline_name
      AND t.flight_number = f.flight_number
      AND t.departure_datetime = f.departure_datetime
      AND t.customer_email = %s
)
AND f.departure_datetime > NOW()                   -- default when no date filters are supplied
AND DATE(f.departure_datetime) >= %s                -- optional
AND DATE(f.departure_datetime) <= %s                -- optional
AND (dep.airport_code LIKE %s OR dep.city LIKE %s)  -- optional
AND (arr.airport_code LIKE %s OR arr.city LIKE %s)  -- optional
GROUP BY ...
ORDER BY f.departure_datetime ASC;
```

Explanation: shows purchased flights for the logged-in customer. By default it shows future flights; date filters can be used to include past flights.

### View Flights Eligible for Rating

Route: `/customer/ratings`

Query:

```sql
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
JOIN Flight f
    ON f.airline_name = t.airline_name
   AND f.flight_number = t.flight_number
   AND f.departure_datetime = t.departure_datetime
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
LEFT JOIN Rating r
    ON r.airline_name = f.airline_name
   AND r.flight_number = f.flight_number
   AND r.departure_datetime = f.departure_datetime
   AND r.customer_email = t.customer_email
WHERE t.customer_email = %s
  AND f.departure_datetime < NOW()
ORDER BY f.departure_datetime DESC;
```

Explanation: shows past purchased flights and any existing rating/comment by the customer.

### Submit or Update Rating

Route: `/customer/review/<flight_key>`

Eligibility query:

```sql
SELECT 1
FROM Ticket t
JOIN Flight f
    ON f.airline_name = t.airline_name
   AND f.flight_number = t.flight_number
   AND f.departure_datetime = t.departure_datetime
WHERE t.customer_email = %s
  AND f.airline_name = %s
  AND f.flight_number = %s
  AND f.departure_datetime = %s
  AND f.departure_datetime < NOW();
```

Rating upsert:

```sql
INSERT INTO Rating (
    customer_email, airline_name, flight_number, departure_datetime, rating, comment
)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    rating = VALUES(rating),
    comment = VALUES(comment);
```

Explanation: only customers who purchased a completed flight can rate it. The `Rating` primary key lets the app update an existing rating if one already exists.

## Airline Staff Use Cases

### View Staff Dashboard

Route: `/staff/home`

Upcoming flights:

```sql
SELECT COUNT(*) AS upcoming_flights
FROM Flight
WHERE airline_name = %s AND departure_datetime > NOW();
```

Fleet summary:

```sql
SELECT COUNT(*) AS fleet_count, COALESCE(SUM(num_seats), 0) AS total_seats
FROM Airplane
WHERE airline_name = %s;
```

Recent ticket sales:

```sql
SELECT COUNT(t.ticket_id) AS recent_tickets,
       COALESCE(SUM(f.base_price), 0) AS recent_sales
FROM Ticket t
JOIN Flight f
    ON f.airline_name = t.airline_name
   AND f.flight_number = t.flight_number
   AND f.departure_datetime = t.departure_datetime
WHERE f.airline_name = %s
  AND t.purchase_datetime >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```

Average rating:

```sql
SELECT AVG(r.rating) AS avg_rating
FROM Rating r
WHERE r.airline_name = %s;
```

Explanation: gives staff a quick summary of operations, fleet capacity, recent sales, and customer feedback.

### View and Filter Staff Flights

Route: `/staff/flights`

Query:

```sql
SELECT ...
FROM Flight f
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
LEFT JOIN Airplane a
    ON a.airline_name = f.airline_name
   AND a.airplane_id = f.airplane_id
LEFT JOIN Ticket t
    ON t.airline_name = f.airline_name
   AND t.flight_number = f.flight_number
   AND t.departure_datetime = f.departure_datetime
WHERE f.airline_name = %s
  AND DATE(f.departure_datetime) BETWEEN %s AND %s
  AND (dep.airport_code LIKE %s OR dep.city LIKE %s)
  AND (arr.airport_code LIKE %s OR arr.city LIKE %s)
GROUP BY ...
ORDER BY f.departure_datetime ASC;
```

Explanation: staff can view flights only for their airline and filter by date range and route.

### Create Flight

Route: `/staff/create-flight`

Airplane dropdown query:

```sql
SELECT airplane_id, manufacturer, num_seats
FROM Airplane
WHERE airline_name = %s
ORDER BY airplane_id;
```

Airport dropdown query:

```sql
SELECT airport_code, city, country
FROM Airport
ORDER BY airport_code;
```

Airplane ownership check:

```sql
SELECT 1
FROM Airplane
WHERE airline_name = %s AND airplane_id = %s;
```

Airport existence check:

```sql
SELECT airport_code
FROM Airport
WHERE airport_code IN (%s, %s);
```

Flight insert:

```sql
INSERT INTO Flight (
    airline_name, flight_number, departure_datetime, departure_airport_code,
    arrival_airport_code, arrival_datetime, base_price, status, airplane_id
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
```

Explanation: staff can create flights for their own airline only. The app validates airplane ownership, airport existence, route, schedule, status, and price before inserting.

### View Flight Detail

Route: `/staff/flight/<airline_name>/<flight_number>/<departure_datetime>`

Flight ownership/detail query:

```sql
SELECT ...
FROM Flight f
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
LEFT JOIN Airplane a
    ON a.airline_name = f.airline_name
   AND a.airplane_id = f.airplane_id
LEFT JOIN Ticket t
    ON t.airline_name = f.airline_name
   AND t.flight_number = f.flight_number
   AND t.departure_datetime = f.departure_datetime
WHERE f.airline_name = %s
  AND f.flight_number = %s
  AND f.departure_datetime = %s
  AND f.airline_name = %s
GROUP BY ...;
```

Customers on the flight:

```sql
SELECT c.email, c.name, c.phone_number, t.purchase_datetime
FROM Ticket t
JOIN Customer c ON c.email = t.customer_email
WHERE t.airline_name = %s
  AND t.flight_number = %s
  AND t.departure_datetime = %s
ORDER BY t.purchase_datetime DESC;
```

Ratings and comments:

```sql
SELECT r.rating, r.comment, c.name, c.email
FROM Rating r
JOIN Customer c ON c.email = r.customer_email
WHERE r.airline_name = %s
  AND r.flight_number = %s
  AND r.departure_datetime = %s
ORDER BY r.rating DESC;
```

Average rating:

```sql
SELECT AVG(rating) AS avg_rating
FROM Rating
WHERE airline_name = %s
  AND flight_number = %s
  AND departure_datetime = %s;
```

Explanation: staff can inspect one airline-owned flight, see ticketed customers, and review customer feedback.

### Update Flight Status

Route: `/staff/update-status/<airline_name>/<flight_number>/<departure_datetime>`

Flight ownership check: same as the flight detail ownership query.

Update query:

```sql
UPDATE Flight
SET status = %s
WHERE airline_name = %s
  AND flight_number = %s
  AND departure_datetime = %s;
```

Explanation: staff can change status to `on-time`, `delayed`, or `cancelled` for flights belonging to their own airline.

### Add Airplane

Route: `/staff/add-airplane`

Next airplane id:

```sql
SELECT COALESCE(MAX(airplane_id), 0) + 1 AS next_id
FROM Airplane
WHERE airline_name = %s;
```

Airplane insert:

```sql
INSERT INTO Airplane (
    airline_name, airplane_id, num_seats, manufacturer, manufacture_date
)
VALUES (%s, %s, %s, %s, %s);
```

Fleet list:

```sql
SELECT *
FROM Airplane
WHERE airline_name = %s
ORDER BY airplane_id;
```

Explanation: staff can add aircraft to their airline. The airplane key is `(airline_name, airplane_id)`, so IDs are generated per airline.

### Add Airport

Route: `/staff/add-airport`

Airport insert:

```sql
INSERT INTO Airport (airport_code, city, country, airport_type)
VALUES (%s, %s, %s, %s);
```

Airport list:

```sql
SELECT *
FROM Airport
ORDER BY airport_code;
```

Explanation: staff can add airports that can later be selected when creating flights.

### View Airline Customers

Route: `/staff/customers`

Query:

```sql
SELECT c.email, c.name, c.phone_number,
       COUNT(t.ticket_id) AS tickets_purchased,
       MAX(t.purchase_datetime) AS last_purchase
FROM Ticket t
JOIN Customer c ON c.email = t.customer_email
JOIN Flight f
    ON f.airline_name = t.airline_name
   AND f.flight_number = t.flight_number
   AND f.departure_datetime = t.departure_datetime
WHERE f.airline_name = %s
  AND (%s = '' OR DATE(t.purchase_datetime) >= %s)
  AND (%s = '' OR DATE(t.purchase_datetime) <= %s)
GROUP BY c.email, c.name, c.phone_number
ORDER BY tickets_purchased DESC, last_purchase DESC;
```

Explanation: staff can see customers who purchased tickets for their airline and identify the most frequent customer.

### View Reports

Route: `/staff/reports`

Totals query:

```sql
SELECT COUNT(t.ticket_id) AS total_tickets,
       COALESCE(SUM(f.base_price), 0) AS total_sales
FROM Ticket t
JOIN Flight f
    ON f.airline_name = t.airline_name
   AND f.flight_number = t.flight_number
   AND f.departure_datetime = t.departure_datetime
WHERE f.airline_name = %s
  AND DATE(t.purchase_datetime) BETWEEN %s AND %s;
```

Monthly ticket/sales query:

```sql
SELECT DATE_FORMAT(t.purchase_datetime, '%Y-%m') AS month,
       COUNT(t.ticket_id) AS tickets_sold,
       COALESCE(SUM(f.base_price), 0) AS sales
FROM Ticket t
JOIN Flight f
    ON f.airline_name = t.airline_name
   AND f.flight_number = t.flight_number
   AND f.departure_datetime = t.departure_datetime
WHERE f.airline_name = %s
  AND DATE(t.purchase_datetime) BETWEEN %s AND %s
GROUP BY month
ORDER BY month;
```

Top routes query:

```sql
SELECT CONCAT(dep.airport_code, ' to ', arr.airport_code) AS route,
       COUNT(t.ticket_id) AS tickets_sold,
       COALESCE(SUM(f.base_price), 0) AS sales
FROM Ticket t
JOIN Flight f
    ON f.airline_name = t.airline_name
   AND f.flight_number = t.flight_number
   AND f.departure_datetime = t.departure_datetime
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
WHERE f.airline_name = %s
  AND DATE(t.purchase_datetime) BETWEEN %s AND %s
GROUP BY route
ORDER BY tickets_sold DESC, sales DESC
LIMIT 5;
```

Top customers query:

```sql
SELECT c.email, c.name, COUNT(t.ticket_id) AS tickets_sold
FROM Ticket t
JOIN Customer c ON c.email = t.customer_email
JOIN Flight f
    ON f.airline_name = t.airline_name
   AND f.flight_number = t.flight_number
   AND f.departure_datetime = t.departure_datetime
WHERE f.airline_name = %s
  AND DATE(t.purchase_datetime) BETWEEN %s AND %s
GROUP BY c.email, c.name
ORDER BY tickets_sold DESC, c.name
LIMIT 5;
```

Flight status counts:

```sql
SELECT status, COUNT(*) AS flight_count
FROM Flight
WHERE airline_name = %s
GROUP BY status
ORDER BY status;
```

Explanation: reports show ticket totals, revenue totals, month-wise ticket counts, top routes, top customers, and overall status distribution for the staff member's airline.

## Import Script Use Case

### Import Supported Flights from CSV

Command:

```bash
venv/bin/python scripts/import_flights.py
```

Key queries:

```sql
INSERT IGNORE INTO Airline (airline_name)
VALUES (%s);
```

```sql
INSERT IGNORE INTO Airport (airport_code, city, country, airport_type)
VALUES (%s, %s, %s, %s);
```

```sql
SELECT airplane_id
FROM Airplane
WHERE airline_name = %s
  AND num_seats = %s
  AND manufacturer = %s
LIMIT 1;
```

```sql
SELECT COALESCE(MAX(airplane_id), 0) + 1 AS next_id
FROM Airplane
WHERE airline_name = %s;
```

```sql
INSERT INTO Airplane (airline_name, airplane_id, num_seats, manufacturer, manufacture_date)
VALUES (%s, %s, %s, %s, %s);
```

```sql
SELECT 1
FROM Flight
WHERE airline_name = %s
  AND flight_number = %s
  AND departure_datetime = %s
LIMIT 1;
```

```sql
INSERT INTO Flight (
    airline_name, flight_number, departure_datetime, departure_airport_code,
    arrival_airport_code, arrival_datetime, base_price, status, airplane_id
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
```

Explanation: the importer loads additional flights from a CSV file while avoiding duplicate flights by default.
