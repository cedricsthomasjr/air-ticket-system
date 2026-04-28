SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS review;
DROP TABLE IF EXISTS ticket;
DROP TABLE IF EXISTS flight;
DROP TABLE IF EXISTS airplane;
DROP TABLE IF EXISTS airline_staff;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS airline;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE airline (
    airline_name VARCHAR(100) PRIMARY KEY
);

CREATE TABLE customer (
    email VARCHAR(255) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    password CHAR(32) NOT NULL
);

CREATE TABLE airline_staff (
    username VARCHAR(100) PRIMARY KEY,
    password CHAR(32) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    airline_name VARCHAR(100) NOT NULL,
    FOREIGN KEY (airline_name) REFERENCES airline(airline_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE airplane (
    airplane_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_name VARCHAR(100) NOT NULL,
    num_seats INT NOT NULL CHECK (num_seats > 0),
    manufacturer VARCHAR(100),
    FOREIGN KEY (airline_name) REFERENCES airline(airline_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE flight (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_name VARCHAR(100) NOT NULL,
    source_city VARCHAR(100) NOT NULL,
    destination_city VARCHAR(100) NOT NULL,
    source_airport VARCHAR(10) NOT NULL,
    destination_airport VARCHAR(10) NOT NULL,
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'On Time',
    airplane_id INT,
    CHECK (status IN ('On Time', 'Delayed', 'Cancelled')),
    CHECK (arrival_time > departure_time),
    FOREIGN KEY (airline_name) REFERENCES airline(airline_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (airplane_id) REFERENCES airplane(airplane_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    INDEX idx_flight_departure (departure_time),
    INDEX idx_flight_route (source_airport, destination_airport),
    INDEX idx_flight_airline (airline_name)
);

CREATE TABLE ticket (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_email VARCHAR(255) NOT NULL,
    flight_id INT NOT NULL,
    purchase_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_customer_flight (customer_email, flight_id),
    FOREIGN KEY (customer_email) REFERENCES customer(email)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (flight_id) REFERENCES flight(flight_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE review (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_email VARCHAR(255) NOT NULL,
    flight_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_customer_review (customer_email, flight_id),
    FOREIGN KEY (customer_email) REFERENCES customer(email)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (flight_id) REFERENCES flight(flight_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);
