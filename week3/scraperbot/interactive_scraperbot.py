#!/usr/bin/env python3
"""
Interactive ScraperBot CLI
This allows you to scrape a website and then ask multiple questions interactively.
Usage: python3 interactive_scraperbot.py <url>
"""

import os
import sys
import asyncio
import argparse
import subprocess
from pathlib import Path

# Add the scraperbot directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

def ensure_mysql_running():
    """Ensure MySQL container is running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=scraper_mysql", "--filter", "status=running", "--quiet"],
            capture_output=True,
            text=True
        )
        if not result.stdout.strip():
            print("🔄 Starting MySQL container...")
            subprocess.run(
                ["docker-compose", "up", "-d", "mysql"],
                cwd=script_dir,
                check=True
            )
            print("⏳ Waiting for MySQL to be ready...")
            import time
            time.sleep(15)
            print("✅ MySQL container is ready")
        else:
            print("✅ MySQL container is already running")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start MySQL container: {e}")
        return False

async def scrape_and_setup_database(url: str):
    """Scrape the website and set up the database"""
    print(f"🌐 Starting to scrape: {url}")
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        env_file = script_dir / ".." / ".." / ".env"
        load_dotenv(env_file)
    except ImportError:
        pass
    
    # Set DB_HOST for container networking
    os.environ["DB_HOST"] = "mysql"
    
    # Import scraperbot modules
    from scraperbot import scraper_workflow, validate_url
    from database_tools import DatabaseTools
    
    # Validate URL
    if not validate_url(url):
        print("❌ Invalid URL or unable to fetch content")
        return None
    
    # Setup database connection (using container network)
    db_host = os.environ.get("DB_HOST", "mysql")
    db_connection = f"mysql://root:scraper_root_pass@{db_host}:3306/scraper_db"
    
    try:
        db_tools = DatabaseTools(db_connection)
        print("✅ Database connection established!")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None
    
    # Run scraper workflow
    print("🤖 AI is analyzing and structuring the scraped data...")
    success = await scraper_workflow(url, db_tools)
    if not success:
        print("❌ Failed to scrape and analyze website content.")
        return None
    
    print("✅ Database created and populated successfully!")
    return db_tools

async def ask_question_interactive(question: str, db_tools):
    """Ask a question about the scraped data"""
    from scraperbot import question_to_sql_workflow, translate_response_workflow
    
    print(f"🔍 Processing question: {question}")
    
    # Convert question to SQL and execute
    sql_query, query_result = await question_to_sql_workflow(question, db_tools)
    
    if not query_result or not query_result.get("success"):
        print("❌ Sorry, I couldn't process your question. Please try rephrasing it.")
        return False
    
    # Translate results to natural language
    answer = await translate_response_workflow(question, sql_query, query_result, db_tools)
    
    # Display the answer
    print(f"\n📊 Answer: {answer}")
    print(f"🔧 SQL Query used: {sql_query}")
    print()
    
    return True

async def run_interactive_session(url: str):
    """Run the interactive scraperbot session inside a container"""
    
    # Run the scraping in container via docker-compose
    print("🚀 Running scraper in container...")
    
    scrape_script = f'''
import asyncio
import os
import sys
sys.path.append("/app")

# Load environment variables are already loaded by docker-compose
os.environ["DB_HOST"] = "mysql"

async def main():
    from scraperbot import scraper_workflow, validate_url
    from database_tools import DatabaseTools
    
    url = "{url}"
    print(f"🌐 Processing URL: {{url}}")
    
    if not validate_url(url):
        print("❌ Invalid URL")
        return False
    
    db_host = os.environ.get("DB_HOST", "mysql")
    db_connection = f"mysql://root:scraper_root_pass@{{db_host}}:3306/scraper_db"
    
    try:
        db_tools = DatabaseTools(db_connection)
        print("✅ Database connection established!")
    except Exception as e:
        print(f"❌ Database connection failed: {{e}}")
        return False
    
    success = await scraper_workflow(url, db_tools)
    if success:
        print("✅ Scraping completed successfully!")
        return True
    else:
        print("❌ Scraping failed")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
'''
    
    # Write the script to a temporary file and run it in container
    try:
        result = subprocess.run([
            "docker-compose", "run", "--rm", "scraper", 
            "python3", "-c", scrape_script
        ], cwd=script_dir, check=True)
        
        if result.returncode != 0:
            print("❌ Scraping failed in container")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running scraper in container: {e}")
        return False
    
    print("\n🎉 Scraping completed! Now you can ask questions about the data.")
    print("💡 Type 'quit', 'exit', or 'q' to end the session.")
    print("=" * 60)
    
    # Now start the interactive question loop
    while True:
        try:
            question = input("\n❓ Ask a question about the data: ").strip()
            
            if not question:
                print("💬 Please enter a question.")
                continue
                
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            # Run the question in container
            print("🤔 Thinking...")
            
            # Escape the question for safe inclusion in script
            escaped_question = question.replace('"', '\\"').replace("'", "\\'")
            question_script = f'''
import asyncio
import os
import sys
sys.path.append("/app")

async def main():
    from scraperbot import question_to_sql_workflow, translate_response_workflow
    from database_tools import DatabaseTools
    
    question = "{escaped_question}"
    
    db_host = os.environ.get("DB_HOST", "mysql")
    db_connection = f"mysql://root:scraper_root_pass@{{db_host}}:3306/scraper_db"
    
    try:
        db_tools = DatabaseTools(db_connection)
        sql_query, query_result = await question_to_sql_workflow(question, db_tools)
        
        if query_result and query_result.get("success"):
            answer = await translate_response_workflow(question, sql_query, query_result, db_tools)
            print(f"\\n📊 Answer: {{answer}}")
            print(f"🔧 SQL Query: {{sql_query}}")
        else:
            print("❌ Sorry, I couldn't process your question. Please try rephrasing it.")
            
    except Exception as e:
        print(f"❌ Error processing question: {{e}}")

asyncio.run(main())
'''
            
            try:
                subprocess.run([
                    "docker-compose", "run", "--rm", "scraper",
                    "python3", "-c", question_script
                ], cwd=script_dir, check=True)
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Error processing question: {e}")
                
        except KeyboardInterrupt:
            print("\n👋 Session interrupted. Goodbye!")
            break
        except EOFError:
            print("\n👋 End of input. Goodbye!")
            break
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Interactive ScraperBot CLI")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--ensure-mysql", action="store_true", help="Start MySQL container if not running (default: auto)")
    
    args = parser.parse_args()
    
    print("🤖 Interactive ScraperBot CLI")
    print("=" * 40)
    
    # Ensure MySQL is running
    if not ensure_mysql_running():
        sys.exit(1)
    
    # Run the interactive session
    try:
        success = asyncio.run(run_interactive_session(args.url))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()