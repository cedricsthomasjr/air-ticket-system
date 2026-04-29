# Demo Notes

## Run the Application

From the project folder:

```bash
venv/bin/python -m flask --app app run --port 5001
```

Then open:

```text
http://127.0.0.1:5001
```

## Reset the MySQL Database

The app can reset the MySQL database from `sql/schema.sql` and `sql/seed.sql`:

```text
http://127.0.0.1:5001/reset-db
```

## Demo Accounts

Customer:

```text
cj@nyu.edu / pass123
```

Airline staff:

```text
admin1 / adminpass
```

## Suggested Customer Test Cases

1. Log in as `cj@nyu.edu`.
2. Search future flights by source `JFK` and destination `PVG`.
3. Purchase a future flight with card information.
4. Open "My Flights" and filter by date, source, and destination.
5. Open "Rate Flights" and submit or update a rating for a completed purchased flight.
6. Log out and confirm the goodbye page appears.

## Suggested Staff Test Cases

1. Log in as `admin1`.
2. Open the staff dashboard and review operational summary cards.
3. Open "Flights" and filter by date, source, and destination.
4. Update a flight status.
5. Open a flight detail page and review customers and ratings.
6. Add a new airplane.
7. Add a new airport code.
8. Create a new flight using existing airports and an owned airplane.
9. Open "Customers" and review frequent customer data.
10. Open "Reports" and review totals, monthly chart, status counts, top routes, and top customers.

## Database Notes

- Flights are identified by the composite key `(airline_name, flight_number, departure_datetime)`.
- Tickets reference flights with the same composite key.
- Ratings are stored in the `Rating` table and use `(customer_email, airline_name, flight_number, departure_datetime)` as the primary key.
- Staff users only manage flights and airplanes for their own airline.
