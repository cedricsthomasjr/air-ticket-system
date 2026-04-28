# Air Ticket Reservation System

Flask + MySQL web app for the Intro to Databases air ticket reservation project.

## Tech Stack

* **Backend:** Python and Flask
* **Database:** MySQL
* **Templating:** Jinja2 HTML
* **Configuration:** python-dotenv

## Database

The database is MySQL and uses the Part 2 schema in `sql/schema.sql`. Seed data lives in `sql/seed.sql`.

The app can initialize or reset the configured MySQL database from those files:

```
/reset-db
```

Default database settings can be supplied with environment variables:

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=air_ticket_system
SECRET_KEY=dev_secret
```

## How to Run

```
pip install -r requirements.txt
python app.py
```

Open:

```
http://127.0.0.1:5000
```

## Demo Credentials

Customer:

```
cj@nyu.edu / pass123
```

Airline staff:

```
admin1 / adminpass
```

## Main Features

* Public flight search
* Customer registration, login, flight search, ticket purchase, itinerary filtering, and ratings
* Airline staff registration, flight management, status updates, airplane creation, flight details, and reports
* MySQL-backed schema with composite flight keys matching the Part 2 design
