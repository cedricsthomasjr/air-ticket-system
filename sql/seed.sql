INSERT INTO Airline VALUES ('JetBlue');

INSERT INTO Airport VALUES
('JFK', 'New York', 'USA', 'international'),
('PVG', 'Shanghai', 'China', 'international');

INSERT INTO Customer VALUES
('cj@nyu.edu', '32250170a0dca92d53ec9624f336ca24', 'CJ Thomas', '123', 'Main St', 'New York', 'NY', '1112223333', 'P123456', '2030-01-01', 'USA', '2003-05-10'),
('brooke@email.com', '32250170a0dca92d53ec9624f336ca24', 'Brooke Smith', '456', 'Park Ave', 'New York', 'NY', '2223334444', 'P654321', '2029-06-15', 'USA', '2002-08-20'),
('john@email.com', '32250170a0dca92d53ec9624f336ca24', 'John Doe', '789', 'Broadway', 'New York', 'NY', '3334445555', 'P999888', '2031-09-30', 'USA', '1998-12-12');

INSERT INTO Airline_Staff VALUES
('admin1', '25e4ee4e9229397b6b17776bfceaf8e7', 'Alice', 'Brown', '1985-04-10', 'alice@jetblue.com', 'JetBlue');

INSERT INTO Staff_Phone VALUES
('admin1', '9998887777'),
('admin1', '8887776666');

INSERT INTO Airplane VALUES
('JetBlue', 1, 180, 'Boeing', '2015-03-01'),
('JetBlue', 2, 200, 'Airbus', '2018-07-15'),
('JetBlue', 3, 150, 'Boeing', '2020-11-20');

INSERT INTO Flight VALUES
('JetBlue', 'JB101', '2026-06-01 08:00:00', 'JFK', 'PVG', '2026-06-01 20:00:00', 800.00, 'on-time', 1),
('JetBlue', 'JB102', '2026-06-10 09:00:00', 'PVG', 'JFK', '2026-06-10 21:00:00', 850.00, 'delayed', 2),
('JetBlue', 'JB103', '2025-12-01 10:00:00', 'JFK', 'PVG', '2025-12-01 22:00:00', 750.00, 'on-time', 3);

INSERT INTO Ticket VALUES
(1, 'cj@nyu.edu', 'JetBlue', 'JB101', '2026-06-01 08:00:00', 'credit', '123456789012', 'CJ Thomas', '2028-01-01', '2026-03-01 12:00:00'),
(2, 'brooke@email.com', 'JetBlue', 'JB102', '2026-06-10 09:00:00', 'debit', '987654321098', 'Brooke Smith', '2027-05-01', '2026-03-02 13:00:00'),
(3, 'john@email.com', 'JetBlue', 'JB103', '2025-12-01 10:00:00', 'credit', '111122223333', 'John Doe', '2029-09-01', '2025-11-20 14:00:00');

INSERT INTO Rating VALUES
('john@email.com', 'JetBlue', 'JB103', '2025-12-01 10:00:00', 4, 'Good flight'),
('cj@nyu.edu', 'JetBlue', 'JB101', '2026-06-01 08:00:00', 5, 'Excellent service');
