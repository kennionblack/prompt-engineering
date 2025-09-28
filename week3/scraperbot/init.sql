-- Initialize the scraper database
-- Tables will be created dynamically by the AI based on scraped content

-- Allow root to connect from external hosts for testing
ALTER USER 'root'@'%' IDENTIFIED BY 'scraper_root_pass';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;

-- The user 'scraper_user' is automatically created by docker-compose MYSQL_USER/MYSQL_PASSWORD env vars
-- Create additional localhost-specific user to handle MySQL 8.0 localhost connection issues
CREATE USER IF NOT EXISTS 'scraper_user'@'localhost' IDENTIFIED BY 'scraper_pass';
CREATE USER IF NOT EXISTS 'scraper_user'@'127.0.0.1' IDENTIFIED BY 'scraper_pass';

-- Grant privileges to all user variants
GRANT ALL PRIVILEGES ON scraper_db.* TO 'scraper_user'@'%';
GRANT ALL PRIVILEGES ON scraper_db.* TO 'scraper_user'@'localhost';
GRANT ALL PRIVILEGES ON scraper_db.* TO 'scraper_user'@'127.0.0.1';

FLUSH PRIVILEGES;