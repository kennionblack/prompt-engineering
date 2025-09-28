# Containerized Web Scraper

A complete containerized web scraping solution with MySQL database integration.

## Quick Start

1. **Start the containers:**

   ```bash
   docker-compose up -d
   ```

2. **Run the demo:**

   ```bash
   docker-compose exec scraper python3 containerized_example.py
   ```

3. **Stop the containers:**
   ```bash
   docker-compose down
   ```

## What's Included

### Services

- **MySQL 8.0**: Database for storing scraped content and configurations
- **Python Scraper**: Application container with all scraping tools

### Components

- `example_scraper_enhanced.py`: Advanced scraper with site analysis
- `scraperbot.py`: Database tools and utilities
- `containerized_example.py`: Complete demonstration script

### Database Schema

- `scraped_content`: Stores URLs, titles, content, and metadata
- `scraper_configs`: Stores reusable scraping configurations

## Usage Examples

### Interactive Database Access

```bash
# Connect to MySQL directly
docker-compose exec mysql mysql -u scraper_user -p scraper_db

# Check database schema from Python
docker-compose exec scraper python3 -c "
from scraperbot import DatabaseTools
db = DatabaseTools('mysql://scraper_user:scraper_pass@mysql:3306/scraper_db')
print(db.get_database_schema())
"
```

### Custom Scraping

```bash
# Run your own scraping script
docker-compose exec scraper python3 your_script.py

# Copy files into the container
docker-compose cp your_script.py scraper:/app/
```

### Development Mode

```bash
# Mount your local directory for development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Configuration

### Environment Variables

- `DB_CONNECTION`: Database connection string (default: `mysql://scraper_user:scraper_pass@mysql:3306/scraper_db`)
- `MYSQL_ROOT_PASSWORD`: MySQL root password (default: `root_password`)
- `MYSQL_DATABASE`: Database name (default: `scraper_db`)
- `MYSQL_USER`: Database user (default: `scraper_user`)
- `MYSQL_PASSWORD`: User password (default: `scraper_pass`)

### Volume Mounts

- `mysql_data`: Persistent MySQL data storage
- `./:/app`: Application code (in development mode)

## Troubleshooting

### Container Issues

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs mysql
docker-compose logs scraper

# Restart services
docker-compose restart
```

### Database Issues

```bash
# Reset database
docker-compose down -v
docker-compose up -d

# Check database connection
docker-compose exec scraper python3 -c "
import mysql.connector
mysql.connector.connect(host='mysql', user='scraper_user', password='scraper_pass', database='scraper_db')
print('✅ Database connection successful')
"
```

### Network Issues

```bash
# Test container networking
docker-compose exec scraper ping mysql
docker-compose exec scraper nslookup mysql
```

## Files

| File                          | Purpose                              |
| ----------------------------- | ------------------------------------ |
| `docker-compose.yml`          | Multi-service container definition   |
| `Dockerfile`                  | Python application container         |
| `init.sql`                    | Database initialization script       |
| `requirements.txt`            | Python dependencies                  |
| `containerized_example.py`    | Complete demo script                 |
| `example_scraper_enhanced.py` | Advanced scraping with site analysis |
| `scraperbot.py`               | Database tools and utilities         |

## Development

To extend this setup:

1. Add your scraping scripts to the directory
2. Install additional Python packages in `requirements.txt`
3. Modify database schema in `init.sql`
4. Adjust container settings in `docker-compose.yml`

The containerized environment provides a clean, reproducible setup for web scraping projects with persistent data storage.
