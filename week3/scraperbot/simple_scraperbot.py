#!/usr/bin/env python3
"""
Simple ScraperBot host runner that executes the container-based version
Usage: python3 simple_scraperbot.py <url> [--question "question"]
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_scraperbot(url: str, question: str = None):
    """Run scraperbot using docker-compose"""
    script_dir = Path(__file__).parent
    
    print(f"🤖 ScraperBot Simple Runner")
    print(f"URL: {url}")
    if question:
        print(f"Question: {question}")
    
    # Ensure MySQL is running
    print("Ensuring MySQL container is running...")
    try:
        subprocess.run(
            ["docker-compose", "up", "-d", "mysql"],
            cwd=script_dir,
            check=True,
            capture_output=True
        )
        print("MySQL container is ready")
    except subprocess.CalledProcessError as e:
        print(f"Failed to start MySQL: {e}")
        return False
    
    # Run the scraperbot in container
    print("Starting scraping process...")
    try:
        if question:
            # Create a script that does both scraping and questioning
            container_script = f'''
echo "{url}" | python3 scraperbot.py
if [ $? -eq 0 ]; then
    echo "Scraping completed. Now answering question..."
    echo "{question}" > /tmp/question.txt
    python3 -c "
import asyncio
import sys
sys.path.append('/app')
from scraperbot import question_to_sql_workflow, translate_response_workflow
from database_tools import DatabaseTools
import os

async def ask_question():
    with open('/tmp/question.txt', 'r') as f:
        question = f.read().strip()
    
    db_host = os.environ.get('DB_HOST', 'mysql')
    db_connection = f'mysql://root:scraper_root_pass@{{db_host}}:3306/scraper_db'
    
    try:
        db_tools = DatabaseTools(db_connection)
        print(f'Answering: {{question}}')
        sql_query, query_result = await question_to_sql_workflow(question, db_tools)
        
        if query_result and query_result.get('success'):
            answer = await translate_response_workflow(question, sql_query, query_result, db_tools)
            print(f'\\n📊 Answer: {{answer}}')
        else:
            print('❌ Sorry, I could not process your question.')
    except Exception as e:
        print(f'Error answering question: {{e}}')

asyncio.run(ask_question())
"
fi
'''
        else:
            container_script = f'echo "{url}" | python3 scraperbot.py'
        
        result = subprocess.run(
            ["docker-compose", "run", "--rm", "scraper", "bash", "-c", container_script],
            cwd=script_dir,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ ScraperBot completed successfully!")
            return True
        else:
            print("❌ ScraperBot encountered an error")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error running scraperbot: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return False

def main():
    parser = argparse.ArgumentParser(description="Simple ScraperBot runner")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--question", "-q", help="Question to ask about the scraped data")
    
    args = parser.parse_args()
    
    success = run_scraperbot(args.url, args.question)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()