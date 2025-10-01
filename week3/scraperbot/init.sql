-- Initialize the scraper database
-- Tables will be created dynamically by the AI based on scraped content

-- Create root user that can connect from external hosts
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'scraper_root_pass';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;

-- Create localhost-specific root user
CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY 'scraper_root_pass';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;

-- The user 'scraper_user' is automatically created by docker-compose MYSQL_USER/MYSQL_PASSWORD env vars
-- Create additional host-specific users for external connections
CREATE USER IF NOT EXISTS 'scraper_user'@'localhost' IDENTIFIED BY 'scraper_pass';
CREATE USER IF NOT EXISTS 'scraper_user'@'127.0.0.1' IDENTIFIED BY 'scraper_pass';
CREATE USER IF NOT EXISTS 'scraper_user'@'%' IDENTIFIED BY 'scraper_pass';

-- Grant privileges to all user variants
GRANT ALL PRIVILEGES ON scraper_db.* TO 'scraper_user'@'%';
GRANT ALL PRIVILEGES ON scraper_db.* TO 'scraper_user'@'localhost';
GRANT ALL PRIVILEGES ON scraper_db.* TO 'scraper_user'@'127.0.0.1';

FLUSH PRIVILEGES;