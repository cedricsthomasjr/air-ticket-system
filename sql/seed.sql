-- ============================================================
-- DEMO SEED — Test Scenarios 05/01/2026
-- Mapped to your exact schema (air_ticket_system)
-- Run this AFTER backing up and truncating all tables
-- ============================================================

-- -------------------------------------------------------
-- 0. TRUNCATE (FK-safe order)
-- -------------------------------------------------------
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE Rating;
TRUNCATE TABLE Ticket;
TRUNCATE TABLE Flight;
TRUNCATE TABLE Airplane;
TRUNCATE TABLE Staff_Phone;
TRUNCATE TABLE Airline_Staff;
TRUNCATE TABLE Airport;
TRUNCATE TABLE Customer;
TRUNCATE TABLE Airline;
SET FOREIGN_KEY_CHECKS = 1;

-- -------------------------------------------------------
-- 1. AIRLINE
-- -------------------------------------------------------
INSERT INTO Airline (airline_name) VALUES
('United');

-- -------------------------------------------------------
-- 2. AIRPORTS
-- -------------------------------------------------------
INSERT INTO Airport (airport_code, city, country, airport_type) VALUES
('JFK', 'NYC',           'USA',   'Both'),
('BOS', 'Boston',        'USA',   'Both'),
('PVG', 'Shanghai',      'China', 'Both'),
('BEI', 'Beijing',       'China', 'Both'),
('SFO', 'San Francisco', 'USA',   'Both'),
('LAX', 'Los Angeles',   'USA',   'Both'),
('HKA', 'Hong Kong',     'China', 'Both'),
('SHN', 'Shenzhen',      'China', 'Both');

-- -------------------------------------------------------
-- 3. CUSTOMERS
-- Passwords are MD5('1234') = 81dc9bdb52d04dc20036dbd8313ed055
-- -------------------------------------------------------
INSERT INTO Customer (email, password, name, building_number, street, city, state, phone_number, passport_number, passport_expiration, passport_country, date_of_birth) VALUES
('testcustomer@nyu.edu', '81dc9bdb52d04dc20036dbd8313ed055', 'Jon Snow',   '1555', 'Jay St',     'Brooklyn', 'New York', '123-4321-4321', '54321', '2025-12-24', 'USA', '1999-12-19'),
('user1@nyu.edu',        '81dc9bdb52d04dc20036dbd8313ed055', 'Alice Bob',  '5405', 'Jay Street', 'Brooklyn', 'New York', '123-4322-4322', '54322', '2025-12-25', 'USA', '1999-11-19'),
('user3@nyu.edu',        '81dc9bdb52d04dc20036dbd8313ed055', 'Trudy Jones','1890', 'Jay Street', 'Brooklyn', 'New York', '123-4324-4324', '54324', '2025-09-24', 'USA', '1999-09-19');

-- -------------------------------------------------------
-- 4. AIRLINE STAFF
-- Password is MD5('abcd') = e2fc714c4727ee9395f324cd2e7f331f
-- -------------------------------------------------------
INSERT INTO Airline_Staff (username, password, first_name, last_name, date_of_birth, email, airline_name) VALUES
('admin', 'e2fc714c4727ee9395f324cd2e7f331f', 'Roe', 'Jones', '1978-05-25', 'staff@nyu.edu', 'United');

INSERT INTO Staff_Phone (username, phone_number) VALUES
('admin', '111-2222-3333'),
('admin', '444-5555-6666');

-- -------------------------------------------------------
-- 5. AIRPLANES
-- -------------------------------------------------------
INSERT INTO Airplane (airline_name, airplane_id, num_seats, manufacturer, manufacture_date) VALUES
('United', 1, 4,  'Boeing', '2012-04-10'),
('United', 2, 4,  'Airbus', '2012-04-10'),
('United', 3, 50, 'Boeing', '2012-04-10');

-- -------------------------------------------------------
-- 6. FLIGHTS
-- -------------------------------------------------------
INSERT INTO Flight (airline_name, flight_number, departure_datetime, departure_airport_code, arrival_airport_code, arrival_datetime, base_price, status, airplane_id) VALUES
('United', '102', '2026-01-14 13:25:25', 'SFO', 'LAX', '2026-01-14 16:50:25', 300.00,  'on-time', 3),
('United', '104', '2026-02-14 13:25:25', 'PVG', 'BEI', '2026-02-14 16:50:25', 300.00,  'on-time', 3),
('United', '206', '2026-05-19 13:25:25', 'SFO', 'LAX', '2026-05-19 16:50:25', 350.00,  'on-time', 2),
('United', '207', '2026-06-19 13:25:25', 'LAX', 'SFO', '2026-06-19 16:50:25', 300.00,  'on-time', 2),
('United', '296', '2025-12-28 13:25:25', 'PVG', 'SFO', '2025-12-28 16:50:25', 3000.00, 'on-time', 1),
('United', '715', '2026-01-25 10:25:25', 'PVG', 'BEI', '2026-01-25 13:50:25', 500.00,  'delayed', 1);

-- -------------------------------------------------------
-- 7. TICKETS
-- Ticket table combines ticket + purchase info.
-- card_expiration stored as DATE (YYYY-MM-01).
-- purchase_datetime = purchase_date + purchase_time from PDF.
--
-- NOTE: Ticket 5 typo corrected per TA (2026-05-01 sign-up sheet):
-- departure_datetime = 2026-02-14 13:25:25 → flight 104.
-- -------------------------------------------------------
INSERT INTO Ticket (ticket_id, customer_email, airline_name, flight_number, departure_datetime, card_type, card_number, name_on_card, card_expiration, purchase_datetime) VALUES
(1,  'testcustomer@nyu.edu', 'United', '102', '2026-01-14 13:25:25', 'credit', '1111-2222-3333-4444', 'Test Customer 1', '2027-03-01', '2025-12-15 11:55:55'),
(2,  'user1@nyu.edu',        'United', '102', '2026-01-14 13:25:25', 'credit', '1111-2222-3333-5555', 'User 1',          '2027-03-01', '2025-12-20 11:55:55'),
(3,  'user1@nyu.edu',        'United', '104', '2026-02-14 13:25:25', 'credit', '1111-2222-3333-5555', 'User 1',          '2024-03-01', '2026-01-21 11:55:55'),
(4,  'testcustomer@nyu.edu', 'United', '104', '2026-02-14 13:25:25', 'credit', '1111-2222-3333-4444', 'Test Customer 1', '2027-03-01', '2026-01-28 11:55:55'),
(5,  'user3@nyu.edu',        'United', '104', '2026-02-14 13:25:25', 'credit', '1111-2222-3333-5555', 'User 3',          '2024-03-01', '2025-07-16 11:55:55'),
(6,  'testcustomer@nyu.edu', 'United', '715', '2026-01-25 10:25:25', 'credit', '1111-2222-3333-4444', 'Test Customer 1', '2024-03-01', '2025-05-20 11:55:55'),
(7,  'user3@nyu.edu',        'United', '206', '2026-05-19 13:25:25', 'credit', '1111-2222-3333-5555', 'User 3',          '2024-03-01', '2026-03-20 11:55:55'),
(8,  'user1@nyu.edu',        'United', '206', '2026-05-19 13:25:25', 'credit', '1111-2222-3333-5555', 'User 1',          '2024-03-01', '2026-02-21 11:55:55'),
(9,  'user1@nyu.edu',        'United', '207', '2026-06-19 13:25:25', 'credit', '1111-2222-3333-5555', 'User 1',          '2024-03-01', '2026-04-02 11:55:55'),
(10, 'testcustomer@nyu.edu', 'United', '207', '2026-06-19 13:25:25', 'credit', '1111-2222-3333-4444', 'Test Customer 1', '2024-03-01', '2026-03-25 11:55:55'),
(11, 'user1@nyu.edu',        'United', '296', '2025-12-28 13:25:25', 'credit', '1111-2222-3333-4444', 'Test Customer 1', '2024-03-01', '2025-02-22 11:55:55'),
(12, 'testcustomer@nyu.edu', 'United', '296', '2025-12-28 13:25:25', 'credit', '1111-2222-3333-4444', 'Test Customer 1', '2024-03-01', '2025-03-20 11:55:55');

-- -------------------------------------------------------
-- 8. RATINGS
-- -------------------------------------------------------
INSERT INTO Rating (customer_email, airline_name, flight_number, departure_datetime, rating, comment) VALUES
('testcustomer@nyu.edu', 'United', '102', '2026-01-14 13:25:25', 4, 'Very Comfortable'),
('user1@nyu.edu',        'United', '102', '2026-01-14 13:25:25', 5, 'Relaxing, check-in and onboarding very professional'),
('testcustomer@nyu.edu', 'United', '104', '2026-02-14 13:25:25', 1, 'Customer Care services are not good'),
('user1@nyu.edu',        'United', '104', '2026-02-14 13:25:25', 5, 'Comfortable journey and Professional');

-- -------------------------------------------------------
-- VERIFY COUNTS (run these SELECT checks after loading)
-- -------------------------------------------------------
-- SELECT COUNT(*) FROM Airline;        -- expected: 1
-- SELECT COUNT(*) FROM Airport;        -- expected: 8
-- SELECT COUNT(*) FROM Customer;       -- expected: 3
-- SELECT COUNT(*) FROM Airline_Staff;  -- expected: 1
-- SELECT COUNT(*) FROM Staff_Phone;    -- expected: 2
-- SELECT COUNT(*) FROM Airplane;       -- expected: 3
-- SELECT COUNT(*) FROM Flight;         -- expected: 6
-- SELECT COUNT(*) FROM Ticket;         -- expected: 12
-- SELECT COUNT(*) FROM Rating;         -- expected: 4
