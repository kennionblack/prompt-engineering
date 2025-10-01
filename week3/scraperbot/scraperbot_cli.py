#!/usr/bin/env python3
"""
Command-line interface for scraperbot.
Usage: python3 scraperbot_cli.py <url> [--question "question text"]
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add the scraperbot directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = script_dir / ".." / ".." / ".env"
    load_dotenv(env_file)
except ImportError:
    pass

# Set DB_HOST to localhost for host execution
os.environ["DB_HOST"] = "localhost"

async def run_scraperbot_cli(url: str, question: str = None):
    """Run scraperbot with command line arguments"""
    from scraperbot import scraper_workflow, question_to_sql_workflow, translate_response_workflow, validate_url
    from database_tools import DatabaseTools
    
    print(f"ScraperBot CLI - Processing URL: {url}")
    
    # Validate URL
    if not validate_url(url):
        print("Error: Invalid URL or unable to fetch content")
        return False
    
    # Setup database connection
    db_host = os.environ.get("DB_HOST", "localhost")
    # Try scraper_user first, then fall back to root
    db_connection = f"mysql://scraper_user:scraper_pass@{db_host}:3306/scraper_db"
    
    try:
        db_tools = DatabaseTools(db_connection)
        print("Database connection established!")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        print("Make sure MySQL is running: docker-compose up -d mysql")
        return False
    
    # Run scraper workflow
    print("Starting web scraping and database creation...")
    success = await scraper_workflow(url, db_tools)
    if not success:
        print("Failed to scrape and analyze website content.")
        return False
    
    print("✅ Database created and populated successfully!")
    
    # If a question was provided, answer it
    if question:
        print(f"\nAnswering question: {question}")
        sql_query, query_result = await question_to_sql_workflow(question, db_tools)
        
        if query_result and query_result.get("success"):
            answer = await translate_response_workflow(question, sql_query, query_result, db_tools)
            print(f"\n📊 Answer: {answer}")
        else:
            print("❌ Sorry, I couldn't process your question.")
    else:
        print("\n✅ Scraping complete! You can now query the database.")
        print("To ask questions, run with: --question 'your question here'")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="ScraperBot CLI - Scrape websites and query data")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--question", "-q", help="Question to ask about the scraped data")
    parser.add_argument("--ensure-mysql", action="store_true", help="Start MySQL container if not running")
    
    args = parser.parse_args()
    
    # Start MySQL if requested
    if args.ensure_mysql:
        import subprocess
        try:
            subprocess.run(["docker-compose", "up", "-d", "mysql"], cwd=script_dir, check=True)
            print("Started MySQL container, waiting for readiness...")
            import time
            time.sleep(15)
        except subprocess.CalledProcessError as e:
            print(f"Failed to start MySQL: {e}")
            sys.exit(1)
    
    # Run the scraperbot
    try:
        success = asyncio.run(run_scraperbot_cli(args.url, args.question))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()