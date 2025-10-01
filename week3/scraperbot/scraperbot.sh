#!/bin/bash
# ScraperBot Shell Wrapper
# Usage: ./scraperbot.sh <url> [question]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 ScraperBot Shell Wrapper${NC}"

# Check if URL is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Please provide a URL${NC}"
    echo "Usage: $0 <url> [question]"
    echo "Example: $0 https://books.toscrape.com/ 'How many books are there?'"
    exit 1
fi

URL="$1"
QUESTION="${2:-}"

# Check if MySQL container is running
echo -e "${YELLOW}Checking MySQL status...${NC}"
if ! docker ps --filter "name=scraper_mysql" --filter "status=running" --quiet | grep -q .; then
    echo -e "${YELLOW}Starting MySQL container...${NC}"
    docker-compose up -d mysql
    echo -e "${YELLOW}Waiting for MySQL to be ready...${NC}"
    sleep 15
else
    echo -e "${GREEN}MySQL container is running${NC}"
fi

# Set environment variables for host execution
export DB_HOST=localhost

# Load environment variables from repository root
if [ -f "../../.env" ]; then
    echo -e "${GREEN}Loading environment variables...${NC}"
    export $(grep -v '^#' ../../.env | xargs)
else
    echo -e "${RED}Warning: .env file not found at repository root${NC}"
fi

# Install dependencies if needed
if ! python3 -c "import openai, mysql.connector, requests, beautifulsoup4" 2>/dev/null; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip3 install -r requirements.txt
fi

# Run the scraperbot
echo -e "${GREEN}Starting ScraperBot...${NC}"
if [ -n "$QUESTION" ]; then
    echo -e "${GREEN}URL: $URL${NC}"
    echo -e "${GREEN}Question: $QUESTION${NC}"
    python3 scraperbot_cli.py "$URL" --question "$QUESTION"
else
    echo -e "${GREEN}URL: $URL${NC}"
    python3 scraperbot_cli.py "$URL"
fi