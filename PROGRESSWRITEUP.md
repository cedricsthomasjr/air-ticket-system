# Part 3 Progress Report - Air Ticket Reservation System.

## 1. Overview

This project is a web-based Air Ticket Reservation System, which will enable the customers to search and view flights, and the airline staff manage flight operations. The system uses role-based access control and session-based authentication.

## 2. Implemented Features

### Authentication

- Customer and airline staff login.
- Flask sessions session management.
- Role-based authorization to limit routes.

### Customer Features

- Search for future flights based on source and destination
- View purchased flights

### Airline Staff Features

- See flights in the 30 days.
- Create new flights

## 3. Database Design

The system is based on a relational schema which comprises the following tables:

- airline
- customer
- airline_staff
- airplane
- flight
- ticket

Key relationships:

Flights are associated with customers by way of tickets.  
Flights are related to airlines.  
Airline employees are associated with a particular airline.

Foreign key constraints are used to enforce relationships between tables.

## 4. Example Queries

### Search Flights

```sql
SELECT * FROM flight
WHERE departuretime > CURRENTTIME
AND source_airport LIKE ?
AND destination_airport LIKE ?
ORDER BY departure_time;
```
