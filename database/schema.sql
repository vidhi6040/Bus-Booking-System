CREATE DATABASE IF NOT EXISTS bus_booking_db;
USE bus_booking_db;

CREATE TABLE IF NOT EXISTS users (
 id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL,
 email VARCHAR(150) NOT NULL UNIQUE, phone VARCHAR(20),
 password_hash VARCHAR(255) NOT NULL,
 role ENUM('passenger','operator','admin') DEFAULT 'passenger',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS operators (
 id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL,
 phone VARCHAR(20), email VARCHAR(150)
);
CREATE TABLE IF NOT EXISTS stops (
 id INT AUTO_INCREMENT PRIMARY KEY, city VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS buses (
 id INT AUTO_INCREMENT PRIMARY KEY, operator_id INT NOT NULL,
 bus_name VARCHAR(100) NOT NULL, bus_number VARCHAR(30) NOT NULL UNIQUE,
 bus_type VARCHAR(30) NOT NULL, total_seats INT NOT NULL,
 FOREIGN KEY(operator_id) REFERENCES operators(id)
);
CREATE TABLE IF NOT EXISTS trips (
 id INT AUTO_INCREMENT PRIMARY KEY, bus_id INT NOT NULL,
 origin_id INT NOT NULL, destination_id INT NOT NULL,
 departure DATETIME NOT NULL, arrival DATETIME NOT NULL,
 fare DECIMAL(10,2) NOT NULL,
 status ENUM('Scheduled','Cancelled','Completed') DEFAULT 'Scheduled',
 cancellation_hours INT DEFAULT 24, refund_percent DECIMAL(5,2) DEFAULT 80,
 FOREIGN KEY(bus_id) REFERENCES buses(id),
 FOREIGN KEY(origin_id) REFERENCES stops(id),
 FOREIGN KEY(destination_id) REFERENCES stops(id),
 INDEX trip_search_idx(origin_id,destination_id,departure)
);
CREATE TABLE IF NOT EXISTS bookings (
 id INT AUTO_INCREMENT PRIMARY KEY, pnr VARCHAR(20) NOT NULL UNIQUE,
 user_id INT NOT NULL, trip_id INT NOT NULL,
 passenger_name VARCHAR(100) NOT NULL, passenger_age INT NOT NULL,
 passenger_gender ENUM('Male','Female','Other') NOT NULL,
 passenger_phone VARCHAR(20) NOT NULL, seat_number VARCHAR(10) NOT NULL,
 amount DECIMAL(10,2) NOT NULL,
 status ENUM('CONFIRMED','CANCELLED') DEFAULT 'CONFIRMED',
 refund_status ENUM('NOT_APPLICABLE','PROCESSED') DEFAULT 'NOT_APPLICABLE',
 refund_amount DECIMAL(10,2) DEFAULT 0,
 booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, cancelled_at DATETIME NULL,
 active_seat_key VARCHAR(40) GENERATED ALWAYS AS
 (CASE WHEN status='CONFIRMED' THEN CONCAT(trip_id,'-',seat_number) ELSE NULL END) STORED,
 UNIQUE KEY one_confirmed_seat(active_seat_key),
 FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(trip_id) REFERENCES trips(id),
 INDEX booking_user_idx(user_id), INDEX booking_trip_idx(trip_id)
);
CREATE TABLE IF NOT EXISTS audit_logs (
 id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NULL,
 action VARCHAR(80) NOT NULL, details VARCHAR(500),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);


USE bus_booking_db;

-- 1. Add more cities (existing cities will not be duplicated)
INSERT IGNORE INTO stops (city) VALUES
('Delhi'),
('Chandigarh'),
('Jaipur'),
('Amritsar'),
('Ludhiana'),
('Jalandhar');

-- 2. Get an existing operator ID
SET @operator_id = (SELECT id FROM operators LIMIT 1);

-- 3. Add more buses
INSERT INTO buses
(operator_id, bus_name, bus_number, bus_type, total_seats)
VALUES
(@operator_id, 'Green Express', 'PB01GR101', 'AC Sleeper', 40),
(@operator_id, 'City Travels', 'PB01GR102', 'AC Seater', 35),
(@operator_id, 'Royal Roadways', 'PB01GR103', 'Non AC', 45);

-- 4. Add trips for Green Express
SET @bus1 = (SELECT id FROM buses WHERE bus_number = 'PB01GR101' LIMIT 1);

INSERT INTO trips
(bus_id, origin_id, destination_id, departure, arrival, fare)
VALUES
(@bus1,
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 (SELECT id FROM stops WHERE city='Chandigarh' LIMIT 1),
 '2026-12-01 08:00:00', '2026-12-01 13:00:00', 650),

(@bus1,
 (SELECT id FROM stops WHERE city='Chandigarh' LIMIT 1),
 (SELECT id FROM stops WHERE city='Amritsar' LIMIT 1),
 '2026-12-02 09:00:00', '2026-12-02 13:30:00', 450),

(@bus1,
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 (SELECT id FROM stops WHERE city='Jaipur' LIMIT 1),
 '2026-12-03 07:00:00', '2026-12-03 12:00:00', 550),

(@bus1,
 (SELECT id FROM stops WHERE city='Ludhiana' LIMIT 1),
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 '2026-12-04 21:00:00', '2026-12-05 05:00:00', 800),

(@bus1,
 (SELECT id FROM stops WHERE city='Jalandhar' LIMIT 1),
 (SELECT id FROM stops WHERE city='Chandigarh' LIMIT 1),
 '2026-12-05 08:00:00', '2026-12-05 12:00:00', 350);

-- 5. Add trips for City Travels
SET @bus2 = (SELECT id FROM buses WHERE bus_number = 'PB01GR102' LIMIT 1);

INSERT INTO trips
(bus_id, origin_id, destination_id, departure, arrival, fare)
VALUES
(@bus2,
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 (SELECT id FROM stops WHERE city='Amritsar' LIMIT 1),
 '2026-12-06 06:00:00', '2026-12-06 15:00:00', 900),

(@bus2,
 (SELECT id FROM stops WHERE city='Jaipur' LIMIT 1),
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 '2026-12-07 10:00:00', '2026-12-07 15:00:00', 500),

(@bus2,
 (SELECT id FROM stops WHERE city='Chandigarh' LIMIT 1),
 (SELECT id FROM stops WHERE city='Ludhiana' LIMIT 1),
 '2026-12-08 08:00:00', '2026-12-08 11:00:00', 300),

(@bus2,
 (SELECT id FROM stops WHERE city='Amritsar' LIMIT 1),
 (SELECT id FROM stops WHERE city='Jalandhar' LIMIT 1),
 '2026-12-09 09:00:00', '2026-12-09 11:00:00', 250),

(@bus2,
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 (SELECT id FROM stops WHERE city='Ludhiana' LIMIT 1),
 '2026-12-10 07:00:00', '2026-12-10 14:00:00', 700);

-- 6. Add trips for Royal Roadways
SET @bus3 = (SELECT id FROM buses WHERE bus_number = 'PB01GR103' LIMIT 1);

INSERT INTO trips
(bus_id, origin_id, destination_id, departure, arrival, fare)
VALUES
(@bus3,
 (SELECT id FROM stops WHERE city='Jalandhar' LIMIT 1),
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 '2026-12-11 20:00:00', '2026-12-12 06:00:00', 750),

(@bus3,
 (SELECT id FROM stops WHERE city='Ludhiana' LIMIT 1),
 (SELECT id FROM stops WHERE city='Amritsar' LIMIT 1),
 '2026-12-12 08:00:00', '2026-12-12 11:00:00', 280),

(@bus3,
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 (SELECT id FROM stops WHERE city='Chandigarh' LIMIT 1),
 '2026-12-13 06:00:00', '2026-12-13 11:00:00', 500),

(@bus3,
 (SELECT id FROM stops WHERE city='Amritsar' LIMIT 1),
 (SELECT id FROM stops WHERE city='Delhi' LIMIT 1),
 '2026-12-14 19:00:00', '2026-12-15 05:00:00', 850),

(@bus3,
 (SELECT id FROM stops WHERE city='Chandigarh' LIMIT 1),
 (SELECT id FROM stops WHERE city='Jaipur' LIMIT 1),
 '2026-12-15 07:00:00', '2026-12-15 15:00:00', 700);
