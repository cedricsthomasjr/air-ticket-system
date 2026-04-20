# Air Ticket Reservation System (Part 3 Progress Report)

## Overview

This project is a web-based Air Ticket Reservation System that allows both customers and airline staff to interact with flight data through a centralized platform.

The system supports:

* Customer flight search and booking history
* Airline staff flight management
* Role-based access control
* Session-based authentication

This implementation focuses on building the core backend logic, database schema, and essential user flows required for the final project.

---

## Tech Stack

* **Backend:** Python (Flask)
* **Database (Current):** SQLite
* **Templating:** Jinja2 (HTML)
* **Environment Management:** python-dotenv

---

## Database Design

The system uses a relational schema with the following tables:

* `airline`
* `customer`
* `airline_staff`
* `airplane`
* `flight`
* `ticket`

Relationships:

* Customers purchase tickets for flights
* Flights are operated by airlines
* Airline staff manage flights and airplanes

The schema is initialized automatically in the application using `init_db()`.

---

## Features Implemented

### Authentication

* Login system for both customers and airline staff
* Session-based authentication
* Role-based access control

### Customer Features

* Search for future flights
* View purchased flights

### Airline Staff Features

* View upcoming flights (next 30 days)
* Create new flights

---

## Dummy Data

Sample data is automatically generated when the database is initialized.

Includes:

* Airlines (SkyJet, BlueCloud)
* Customers
* Airline staff accounts
* Flights and tickets

You can reset the database at any time by visiting:

```
/reset-db
```

---

## How to Run the Project

1. Navigate to project folder:

```
cd air-ticket-system
```

2. Activate virtual environment:

```
source venv/bin/activate
```

3. Install dependencies:

```
pip install -r requirements.txt
```

4. Run the app:

```
python app.py
```

5. Open in browser:

```
http://127.0.0.1:5000
```

---

## Test Credentials

### Customer

* Email: `cj@example.com`
* Password: `test123`

### Airline Staff

* Username: `staff1`
* Password: `admin123`

---

## Progress Report Notes

For rapid development and testing, the current implementation uses **SQLite** as the database.

However, the system has been designed using a relational schema and SQL queries that are fully compatible with **MySQL**, which will be integrated in the final version of the project.

This approach allows for:

* Faster prototyping
* Easier debugging
* Immediate testing of application logic

---

## Next Steps (Planned Features)

* Ticket purchasing functionality
* Flight status updates (staff)
* Add airplane functionality
* Customer ratings and comments
* Reporting dashboard (tickets sold, analytics)

---

## File Structure

```
air-ticket-system/
├── app.py
├── air_ticket_system.db
├── requirements.txt
├── .env
└── templates/
    ├── base.html
    ├── login.html
    ├── customer_home.html
    ├── staff_home.html
    ├── search_flights.html
    ├── my_flights.html
    ├── staff_flights.html
    └── create_flight.html
```

---

## Summary

This progress report demonstrates a functional backend system with working routes, database schema, and user interactions. Core features for both customers and airline staff have been implemented and tested, forming a strong foundation for the final project.

---
