INSERT INTO airline (airline_name) VALUES
('SkyJet'),
('BlueCloud');

INSERT INTO customer (email, name, password) VALUES
('cj@example.com', 'CJ Thomas', 'cc03e747a6afbbcbf8be7668acfebee5'),
('alex@example.com', 'Alex Johnson', 'cc03e747a6afbbcbf8be7668acfebee5');

INSERT INTO airline_staff (username, password, first_name, last_name, airline_name) VALUES
('staff1', '0192023a7bbd73250516f069df18b500', 'Maya', 'Lee', 'SkyJet'),
('staff2', '0192023a7bbd73250516f069df18b500', 'Chris', 'Wong', 'BlueCloud');

INSERT INTO airplane (airplane_id, airline_name, num_seats, manufacturer) VALUES
(1, 'SkyJet', 180, 'Boeing'),
(2, 'BlueCloud', 220, 'Airbus'),
(3, 'SkyJet', 90, 'Embraer');

INSERT INTO flight (
    airline_name, source_city, destination_city, source_airport, destination_airport,
    departure_time, arrival_time, price, status, airplane_id
) VALUES
('SkyJet', 'New York', 'Los Angeles', 'JFK', 'LAX', DATE_ADD(CURDATE(), INTERVAL 7 DAY) + INTERVAL 9 HOUR, DATE_ADD(CURDATE(), INTERVAL 7 DAY) + INTERVAL 12 HOUR, 320.00, 'On Time', 1),
('SkyJet', 'New York', 'Miami', 'JFK', 'MIA', DATE_ADD(CURDATE(), INTERVAL 8 DAY) + INTERVAL 14 HOUR, DATE_ADD(CURDATE(), INTERVAL 8 DAY) + INTERVAL 17 HOUR, 180.00, 'Delayed', 1),
('BlueCloud', 'Newark', 'Atlanta', 'EWR', 'ATL', DATE_ADD(CURDATE(), INTERVAL 9 DAY) + INTERVAL 8 HOUR + INTERVAL 30 MINUTE, DATE_ADD(CURDATE(), INTERVAL 9 DAY) + INTERVAL 11 HOUR, 210.00, 'On Time', 2),
('SkyJet', 'New York', 'Chicago', 'JFK', 'ORD', DATE_SUB(CURDATE(), INTERVAL 30 DAY) + INTERVAL 9 HOUR, DATE_SUB(CURDATE(), INTERVAL 30 DAY) + INTERVAL 11 HOUR + INTERVAL 20 MINUTE, 150.00, 'On Time', 3);

INSERT INTO ticket (customer_email, flight_id) VALUES
('cj@example.com', 1),
('cj@example.com', 4),
('alex@example.com', 3);
