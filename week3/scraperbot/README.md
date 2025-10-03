# ScraperBot

An AI-powered web scraper that automatically extracts structured data from any website and creates a queryable database run within a Docker container.

## What it does

1. **Analyzes** any website's HTML structure
2. **Extracts** structured data using AI (books, quotes, articles, etc.)
3. **Stores** data in MySQL database with appropriate schema
4. **Answers** natural language questions about the data

## Examples

**Books:** "How many books cost over £50?"  
**Quotes:** "Show me quotes by Albert Einstein"  
**Articles:** "What articles were published today?"

## Core Files

- `scraperbot_cli.py` - CLI interface to the Docker container running the scraperbot
- `scraperbot.py` - Core scraping and AI logic
- `database_tools.py` - Database operations
- `tools.py` - OpenAI function definitions

## Requirements

- Docker & Docker Compose
- OpenAI API key

## Setup & Container Startup

### 1. Start the MySQL Container

```bash
# Start MySQL database container in the background
docker-compose up -d mysql

# Check that the container is running
docker ps
```

### 2. Set OpenAI API Key

```bash
# Option 1: Export environment variable
export OPENAI_API_KEY="your-key-here"

# Option 2: Create .env file in project root
echo "OPENAI_API_KEY=your-key-here" > .env
```

### 3. Run the ScraperBot (container must be running)

```bash
# Use the main CLI interface
python3 scraperbot_cli.py <website-url>

# Examples
python3 scraperbot_cli.py https://books.toscrape.com
python3 scraperbot_cli.py https://quotes.toscrape.com
```

### Container Management

```bash
# Stop the containers
docker-compose down

# View container logs
docker-compose logs mysql

# Restart containers
docker-compose restart
```

The system automatically adapts to different website types and extracts meaningful structured data that you can query with natural language.
