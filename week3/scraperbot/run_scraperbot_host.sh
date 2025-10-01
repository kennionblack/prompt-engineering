#!/bin/bash
# Simple ScraperBot wrapper that runs inside the container but accepts host input
# Usage: ./run_scraperbot_host.sh <url> [question]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 ScraperBot Host Runner${NC}"

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

# Run scraperbot inside container but with host input
echo -e "${GREEN}Starting ScraperBot in container...${NC}"
echo -e "${GREEN}URL: $URL${NC}"

if [ -n "$QUESTION" ]; then
    echo -e "${GREEN}Question: $QUESTION${NC}"
    echo -e "${YELLOW}Processing... This may take a while${NC}"
    # Run in container with both scraping and question
    docker-compose run --rm scraper bash -c "
        echo '$URL' | python3 scraperbot.py && echo 'Now asking: $QUESTION' && echo '$QUESTION' | python3 -c '
import asyncio
import sys
sys.path.append(\"/app\")
from scraperbot import question_to_sql_workflow, translate_response_workflow
from database_tools import DatabaseTools
import os

async def ask_question():
    question = input().strip()
    db_host = os.environ.get(\"DB_HOST\", \"mysql\")
    db_connection = f\"mysql://root:scraper_root_pass@{db_host}:3306/scraper_db\"
    
    try:
        db_tools = DatabaseTools(db_connection)
        sql_query, query_result = await question_to_sql_workflow(question, db_tools)
        
        if query_result and query_result.get(\"success\"):
            answer = await translate_response_workflow(question, sql_query, query_result, db_tools)
            print(f\"\\n📊 Answer: {answer}\")
        else:
            print(\"❌ Sorry, I could not process your question.\")
    except Exception as e:
        print(f\"Error: {e}\")

asyncio.run(ask_question())
'"
else
    # Just run scraping
    echo -e "${YELLOW}Processing... This may take a while${NC}"
    echo "$URL" | docker-compose run --rm scraper python3 scraperbot.py
fi

echo -e "${GREEN}✅ ScraperBot completed!${NC}"