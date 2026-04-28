# Use Cases and Main Queries

All application SQL uses MySQL Connector prepared statements with `%s` placeholders.

## Public User

### View Public Info
Searches future flights from `Flight`, joined with `Airport` and `Airplane`, filtered by source/destination city or airport and optional dates.

```sql
SELECT ...
FROM Flight f
JOIN Airport dep ON dep.airport_code = f.departure_airport_code
JOIN Airport arr ON arr.airport_code = f.arrival_airport_code
JOIN Airplane a ON a.airline_name = f.airline_name AND a.airplane_id = f.airplane_id
WHERE f.departure_datetime > NOW()
  AND (dep.airport_code LIKE %s OR dep.city LIKE %s)
  AND (arr.airport_code LIKE %s OR arr.city LIKE %s);
```

### Register
Inserts into either `Customer` or `Airline_Staff` with `md5(password)` stored.

### Login
Checks either `Customer.email` or `Airline_Staff.username` with the MD5 password hash.

## Customer

### View My Flights
Shows flights purchased by the logged-in customer using `Ticket` joined to `Flight`.

### Search and Purchase Tickets
Search uses the public future-flight query. Purchase checks seat availability, prevents duplicate customer tickets, then inserts into `Ticket`.

### Ratings and Comments
Shows past purchased flights and inserts/updates `Rating` using the Part 2 composite flight key.

```sql
INSERT INTO Rating (customer_email, airline_name, flight_number, departure_datetime, rating, comment)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE rating = VALUES(rating), comment = VALUES(comment);
```

## Airline Staff

### View Flights
Shows flights for the staff member's airline, defaulting to the next 30 days, with source/destination/date filters.

### View Customers of a Flight
Joins `Ticket` to `Customer` for one composite flight key.

### Create Flights
Checks that both airport codes exist and the selected airplane belongs to the staff member's airline, then inserts into `Flight`.

### Change Flight Status
Checks the flight belongs to the staff member's airline, then updates `Flight.status`.

### Add Airplane
Inserts into `Airplane` using the staff member's airline and displays all airplanes for that airline.

### View Flight Ratings
Reads `Rating` rows for one flight and calculates `AVG(rating)`.

### Reports
Counts tickets and sums `Flight.base_price` over a selected purchase-date range, grouped by month.
