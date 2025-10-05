CREATE TABLE IF NOT EXISTS audiences (
  id TINYINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  audience_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS series (
  id SMALLINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  series_name VARCHAR(255) NOT NULL,
  max_count TINYINT UNSIGNED
);
-- ALTER TABLE series ADD INDEX idx_series_name (series_name);

CREATE TABLE IF NOT EXISTS user_roles (
  id TINYINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  role_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS campus (
  id TINYINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  campus_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS location (
  id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  campus_id TINYINT UNSIGNED NOT NULL,
  location_name VARCHAR(255) NOT NULL,
  in_audit BOOLEAN NOT NULL DEFAULT 0,
  FOREIGN KEY (campus_id) REFERENCES campus(id)
);

CREATE TABLE IF NOT EXISTS genre (
  id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  genre_name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tag (
  id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  tag_name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS books (
  id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  book_title VARCHAR(255) NOT NULL,
  isbn_list VARCHAR(255), -- this unfortunately needs to be nullable because some books come in without an isbn
  author VARCHAR(255),
  primary_genre_id INT UNSIGNED NOT NULL,
  audience_id TINYINT UNSIGNED NOT NULL,
  pages SMALLINT,
  series_id SMALLINT UNSIGNED,
  series_number TINYINT UNSIGNED,
  publish_date SMALLINT UNSIGNED,
  short_description TEXT,
  language VARCHAR(31),
  img_callback VARCHAR(255),
  FOREIGN KEY (primary_genre_id) REFERENCES genre(id),
  FOREIGN KEY (audience_id) REFERENCES audiences(id),
  FOREIGN KEY (series_id) REFERENCES series(id)
);
-- ALTER TABLE books ADD INDEX idx_name (book_title);

CREATE TABLE IF NOT EXISTS book_genre (
  id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  book_id INT UNSIGNED NOT NULL,
  genre_id INT UNSIGNED NOT NULL,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
  FOREIGN KEY (genre_id) REFERENCES genre(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS book_tag (
  id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  book_id INT UNSIGNED NOT NULL,
  tag_id INT UNSIGNED NOT NULL,
  FOREIGN KEY (book_id) REFERENCES books(id),
  FOREIGN KEY (tag_id) REFERENCES tag(id)
);

CREATE TABLE IF NOT EXISTS inventory (
  qr VARCHAR(15) PRIMARY KEY,
  book_id INT UNSIGNED NOT NULL,
  location_id INT UNSIGNED NOT NULL,
  campus_id TINYINT UNSIGNED NOT NULL,
  is_checked_out BOOLEAN NOT NULL DEFAULT 0,
  FOREIGN KEY (book_id) REFERENCES books(id),
  FOREIGN KEY (campus_id) REFERENCES campus(id),
  FOREIGN KEY (location_id) REFERENCES location(id)
);
-- ALTER TABLE inventory ADD INDEX idx_location (location_id);
-- ALTER TABLE inventory ADD INDEX idx_campus_id (campus_id);
-- ALTER TABLE inventory ADD INDEX idx_ttl (ttl);

CREATE TABLE IF NOT EXISTS audit (
  id TINYINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  campus_id TINYINT UNSIGNED NOT NULL,
  start_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_date DATETIME,
  FOREIGN KEY (campus_id) REFERENCES campus(id)
);

CREATE TABLE IF NOT EXISTS audit_entry (
  qr VARCHAR(15) NOT NULL,
  audit_id TINYINT UNSIGNED NOT NULL,
  state ENUM('Missing', 'Misplaced', 'Found', 'Extra'),
  PRIMARY KEY (qr, audit_id),
  FOREIGN KEY (qr) REFERENCES inventory(qr),
  FOREIGN KEY (audit_id) REFERENCES audit(id)
);

CREATE TABLE IF NOT EXISTS checkout (
  checkout_id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  qr VARCHAR(15) NOT NULL,
  campus_id TINYINT UNSIGNED NOT NULL,
  book_id INT UNSIGNED NOT NULL,
  FOREIGN KEY (book_id) REFERENCES books(id),
  FOREIGN KEY (campus_id) REFERENCES campus(id)
);
-- ALTER TABLE checkout ADD INDEX idx_qr (qr);
-- ALTER TABLE checkout ADD INDEX idx_book_id (book_id);

CREATE TABLE IF NOT EXISTS suggestions (
  suggestion_id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  content TEXT NOT NULL,
  campus_id TINYINT UNSIGNED NOT NULL,
  FOREIGN KEY (campus_id) REFERENCES campus(id)
);

CREATE TABLE IF NOT EXISTS users (
  username VARCHAR(255) PRIMARY KEY,
  password_hash VARCHAR(255) NOT NULL,
  role_id TINYINT UNSIGNED NOT NULL,
  email VARCHAR(255),
  campus_id TINYINT UNSIGNED NOT NULL,
  FOREIGN KEY (role_id) REFERENCES user_roles(id),
  FOREIGN KEY (campus_id) REFERENCES campus(id)
);

CREATE TABLE IF NOT EXISTS shopping_list (
  book_id INT UNSIGNED PRIMARY KEY,
  campus_id TINYINT UNSIGNED NOT NULL,
  FOREIGN KEY (campus_id) REFERENCES campus(id),
  FOREIGN KEY (book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS restock_list (
  book_id INT UNSIGNED PRIMARY KEY,
  campus_id TINYINT UNSIGNED NOT NULL,
  quantity INT NOT NULL,
  FOREIGN KEY (campus_id) REFERENCES campus(id),
  FOREIGN KEY (book_id) REFERENCES books(id)
);