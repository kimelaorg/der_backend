from django.db import models

# Create your models here.


-- Create a database named 'personal_expenses_db' (optional, you might already have one)
-- The exact command depends on your SQL dialect (e.g., MySQL, PostgreSQL)
-- Example for MySQL:
-- CREATE DATABASE IF NOT EXISTS personal_expenses_db;
-- USE personal_expenses_db;

-- --------------------------------------------------------

-- Table structure for `Categories`
-- Stores different categories of expenses (e.g., Food, Transport, Bills)
CREATE TABLE IF NOT EXISTS Categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY, -- Use SERIAL or INTEGER PRIMARY KEY AUTOINCREMENT for PostgreSQL/SQLite
    category_name VARCHAR(50) NOT NULL UNIQUE,
    category_description VARCHAR(255)
);

-- --------------------------------------------------------

-- Table structure for `Expenses`
-- Stores individual daily expense records
CREATE TABLE IF NOT EXISTS Expenses (
    expense_id INT AUTO_INCREMENT PRIMARY KEY, -- Use SERIAL or INTEGER PRIMARY KEY AUTOINCREMENT for PostgreSQL/SQLite
    expense_date DATE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255),
    category_id INT NOT NULL,
    payment_method VARCHAR(50), -- e.g., Cash, Credit Card, Debit Card

    -- Add a foreign key constraint to link expenses to categories
    FOREIGN KEY (category_id) REFERENCES Categories(category_id)
);

-- --------------------------------------------------------

-- Optional: Insert some initial categories into the Categories table
INSERT INTO Categories (category_name, category_description) VALUES
('Food & Drink', 'Groceries, dining out, coffee'),
('Transportation', 'Public transit, gas, car maintenance'),
('Bills & Utilities', 'Rent, electricity, internet, phone bill'),
('Shopping', 'Clothing, electronics, household items'),
('Entertainment', 'Movies, concerts, streaming services'),
('Health & Wellness', 'Gym membership, medical expenses'),
('Miscellaneous', 'Other unexpected expenses');

-- --------------------------------------------------------

-- Example of how to insert a new daily expense record
-- You would replace the values with your actual daily spending data
INSERT INTO Expenses (expense_date, amount, description, category_id, payment_method) VALUES
('2025-11-07', 15.50, 'Lunch at local cafe', (SELECT category_id FROM Categories WHERE category_name = 'Food & Drink'), 'Debit Card');
