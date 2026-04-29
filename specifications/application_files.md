# Application Files

This document lists the files in the application and briefly explains what each file does.

## Root Files

- `app.py`: Main Flask application. Defines routes, session login/logout logic, role-based authorization, MySQL connection helpers, database initialization, and all customer/staff/public use-case queries.
- `requirements.txt`: Python package dependencies needed to run the Flask app, including Flask, MySQL Connector, and python-dotenv.
- `README.md`: Main project overview, technology stack, database notes, run instructions, and demo credentials.
- `MYSQL_SETUP.md`: MySQL setup instructions, database reset instructions, CSV import instructions, and run command examples.
- `PROJECT_FILES.md`: Earlier project file summary.
- `USE_CASE_QUERIES.md`: Earlier short use-case and query summary.
- `PROGRESSWRITEUP.md`: Progress writeup from earlier development.

## Database and Data Files

- `sql/schema.sql`: MySQL schema for the Part 2 database design. Creates `Airline`, `Airport`, `Customer`, `Airline_Staff`, `Staff_Phone`, `Airplane`, `Flight`, `Ticket`, and `Rating`.
- `sql/seed.sql`: Sample data for JetBlue, airports, customers, staff, airplanes, flights, tickets, and ratings.
- `data/supported_flights.csv`: Example CSV input file for importing additional supported flights.

## Scripts

- `scripts/import_flights.py`: Command-line CSV importer. Reads `data/supported_flights.csv`, validates flight data, creates missing airlines/airports/airplanes where appropriate, and inserts flights into MySQL.

## Shared Templates

- `templates/base.html`: Shared layout for every page. Contains the navigation bar, flash-message display, global CSS, responsive layout styles, tables, buttons, forms, cards, and common UI classes.
- `templates/partials/flight_search_form.html`: Reusable flight-search form used by public and customer flight search pages.
- `templates/partials/flight_market.html`: Reusable flight-result cards with route information, seat availability, price, status, and purchase controls for logged-in customers.

## Public Templates

- `templates/index.html`: Public landing/home page with links to browse flights, register, and log in.
- `templates/public_search.html`: Public flight-search page. Allows anonymous users to search future flights before logging in.
- `templates/login.html`: Login page for both customers and airline staff.
- `templates/register.html`: Registration page for customers and airline staff. Customer registration collects profile/passport information; staff registration collects staff identity, airline, email, birth date, and phone information.
- `templates/goodbye.html`: Logout confirmation page with links back to login and home.

## Customer Templates

- `templates/customer_home.html`: Customer dashboard. Shows customer actions and upcoming purchased tickets.
- `templates/search_flights.html`: Logged-in customer flight-search page. Customers can search flights and purchase tickets with payment information.
- `templates/my_flights.html`: Customer itinerary page. Shows purchased flights and supports filters for date, source, and destination.
- `templates/ratings.html`: Customer ratings page. Shows past purchased flights and lets the customer add or update ratings/comments.

## Airline Staff Templates

- `templates/staff_home.html`: Staff dashboard. Shows airline operational summary cards and links to staff workflows.
- `templates/staff_flights.html`: Staff flight-management page. Lists airline flights with filters, tickets sold, open seats, status update form, and detail links.
- `templates/staff_flight_detail.html`: Staff detail page for one flight. Shows flight stats, ticketed customers, phone numbers, ratings, comments, and average rating.
- `templates/create_flight.html`: Staff form for creating a new flight. Uses existing airports and staff-airline-owned airplanes.
- `templates/add_airplane.html`: Staff form for adding an airplane to the staff member's airline and viewing the airline fleet.
- `templates/add_airport.html`: Staff form for adding airport codes to the `Airport` table and viewing all airports.
- `templates/staff_customers.html`: Staff customer analytics page. Shows customers who purchased tickets for the staff member's airline and highlights the most frequent customer.
- `templates/reports.html`: Staff reporting page. Shows ticket totals, sales totals, monthly ticket chart, status counts, top routes, and top customers.

## Generated or Local-Only Files

- `.env`: Local environment variables if created by the developer. This file should not be committed.
- `venv/`: Local Python virtual environment if created by the developer. This folder should not be committed.
- `__pycache__/`: Python bytecode cache created when running the app. This folder should not be committed.
