CREATE DATABASE IF NOT EXISTS transitops;
USE transitops;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  company VARCHAR(100) NOT NULL,
  role VARCHAR(50) DEFAULT 'Operations Manager',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vehicles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  registration_number VARCHAR(50) NOT NULL UNIQUE,
  vehicle_name VARCHAR(100) NOT NULL,
  vehicle_type VARCHAR(50) NOT NULL,
  region VARCHAR(100) NOT NULL DEFAULT 'Central',
  max_load_capacity INT NOT NULL,
  odometer INT DEFAULT 0,
  acquisition_cost DECIMAL(12,2) NOT NULL,
  status VARCHAR(20) DEFAULT 'Available',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drivers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  license_number VARCHAR(50) NOT NULL UNIQUE,
  license_category VARCHAR(50) NOT NULL,
  license_expiry_date DATE NOT NULL,
  contact_number VARCHAR(20) NOT NULL,
  safety_score DECIMAL(3,1) DEFAULT 5.0,
  status VARCHAR(20) DEFAULT 'Available',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trips (
  id INT AUTO_INCREMENT PRIMARY KEY,
  source VARCHAR(100) NOT NULL,
  destination VARCHAR(100) NOT NULL,
  vehicle_id INT NOT NULL,
  driver_id INT NOT NULL,
  cargo_weight INT NOT NULL,
  planned_distance INT NOT NULL,
  actual_distance INT,
  status VARCHAR(20) DEFAULT 'Draft',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

CREATE TABLE IF NOT EXISTS maintenance_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id INT NOT NULL,
  maintenance_type VARCHAR(100) NOT NULL,
  description TEXT,
  cost DECIMAL(10,2) NOT NULL,
  status VARCHAR(20) DEFAULT 'In Progress',
  start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  end_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS fuel_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id INT NOT NULL,
  liters_filled DECIMAL(8,2) NOT NULL,
  cost DECIMAL(10,2) NOT NULL,
  fuel_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS expenses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id INT NOT NULL,
  expense_type VARCHAR(100) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  description TEXT,
  expense_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS vehicle_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id INT NOT NULL,
  document_type VARCHAR(50) NOT NULL,
  document_path VARCHAR(255) NOT NULL,
  expiry_date DATE,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS driver_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  driver_id INT NOT NULL,
  document_type VARCHAR(50) NOT NULL,
  document_path VARCHAR(255) NOT NULL,
  expiry_date DATE,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

CREATE TABLE IF NOT EXISTS email_reminders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  recipient_email VARCHAR(100) NOT NULL,
  reminder_type VARCHAR(50) NOT NULL,
  entity_id INT NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS routes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  route_name VARCHAR(100) NOT NULL,
  origin VARCHAR(100) NOT NULL,
  destination VARCHAR(100) NOT NULL,
  vehicle_count INT DEFAULT 1,
  status VARCHAR(20) DEFAULT 'Active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  alert_type VARCHAR(50) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contact_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  company VARCHAR(100) NOT NULL,
  message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample Data
INSERT INTO vehicles (registration_number, vehicle_name, vehicle_type, region, max_load_capacity, acquisition_cost, status) VALUES
('VAN-001', 'Van Alpha', 'Van', 'Central', 500, 25000.00, 'Available'),
('TRUCK-001', 'Truck Beta', 'Truck', 'North', 1500, 55000.00, 'Available'),
('BIKE-001', 'Bike Gamma', 'Motorcycle', 'East', 100, 8000.00, 'Available'),
('VAN-002', 'Van Delta', 'Van', 'South', 500, 25000.00, 'In Shop');

INSERT INTO drivers (name, license_number, license_category, license_expiry_date, contact_number, safety_score, status) VALUES
('Alex Johnson', 'DL001', 'HMV', '2027-12-31', '555-0001', 4.8, 'Available'),
('Sara Smith', 'DL002', 'LMV', '2026-06-30', '555-0002', 4.9, 'Available'),
('Mike Brown', 'DL003', 'HMV', '2025-03-15', '555-0003', 3.5, 'Suspended'),
('Emma Davis', 'DL004', 'LMV', '2028-08-20', '555-0004', 4.7, 'Available');

INSERT INTO trips (source, destination, vehicle_id, driver_id, cargo_weight, planned_distance, status) VALUES
('Downtown', 'West Terminal', 1, 1, 450, 50, 'Completed'),
('Harbor Gate', 'Airport', 2, 2, 1200, 80, 'Completed');

INSERT INTO fuel_logs (vehicle_id, liters_filled, cost, fuel_date) VALUES
(1, 50.00, 6250.00, '2026-07-10'),
(2, 80.00, 9600.00, '2026-07-11');

INSERT INTO routes (route_name, origin, destination, vehicle_count, status) VALUES
('North Loop', 'Downtown', 'West Terminal', 8, 'Active'),
('Harbor Express', 'Harbor Gate', 'Airport', 5, 'Monitoring'),
('Metro Link', 'Central Hub', 'University District', 6, 'Active');

INSERT INTO alerts (alert_type, severity, message) VALUES
('Route Rebalance', 'Medium', 'Route 15 has been rebalanced to reduce delay.'),
('Fuel Threshold', 'High', 'Fleet 4 has reached the fuel threshold.'),
('Maintenance Warning', 'Medium', 'Vehicle 12 is due for maintenance in 24 hours.');

INSERT INTO maintenance_logs (vehicle_id, maintenance_type, description, cost, status, start_date, end_date) VALUES
(4, 'Engine Diagnostics', 'Full engine check and sensor calibration.', 980.00, 'In Progress', '2026-07-11 09:00:00', NULL),
(2, 'Brake Service', 'Brake pad replacement and fluid top-up.', 420.00, 'Closed', '2026-06-18 08:30:00', '2026-06-18 14:15:00');

INSERT INTO expenses (vehicle_id, expense_type, amount, description, expense_date) VALUES
(1, 'Toll', 65.00, 'Highway tolls for urban delivery run.', '2026-07-10'),
(2, 'Repair', 320.50, 'Minor suspension repair after rough terrain route.', '2026-07-09'),
(3, 'Insurance', 180.00, 'Quarterly motorcycle insurance premium.', '2026-07-05');

INSERT INTO vehicle_documents (vehicle_id, document_type, document_path, expiry_date) VALUES
(1, 'Registration', '/uploads/vehicle_1_registration.pdf', '2027-03-01'),
(2, 'Insurance', '/uploads/vehicle_2_insurance.pdf', '2026-12-31'),
(4, 'Service Record', '/uploads/vehicle_4_service.pdf', '2027-01-01');

INSERT INTO driver_documents (driver_id, document_type, document_path, expiry_date) VALUES
(1, 'License', '/uploads/driver_1_license.pdf', '2027-12-31'),
(2, 'License', '/uploads/driver_2_license.pdf', '2026-06-30'),
(4, 'Medical Certificate', '/uploads/driver_4_medical.pdf', '2027-10-15');

INSERT INTO email_reminders (recipient_email, reminder_type, entity_id, entity_type, sent_at) VALUES
('admin@transitops.com', 'license_expiry', 2, 'driver', '2026-06-05 10:00:00'),
('admin@transitops.com', 'maintenance_due', 4, 'vehicle', '2026-07-10 09:15:00');

INSERT INTO contact_requests (full_name, email, company, message, created_at) VALUES
('Mia Carter', 'mia.carter@logistics.com', 'Metro Freight', 'Interested in a demo for multi-route dispatch capabilities.', '2026-07-08 16:20:00');
