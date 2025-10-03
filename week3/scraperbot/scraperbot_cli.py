#!/usr/bin/env python3
"""
Clean Interactive ScraperBot CLI
This version provides a clean interactive experience
Usage: python3 clean_interactive.py <url>
"""

import subprocess
import sys
import argparse
from pathlib import Path


def ensure_mysql_running():
    """Ensure MySQL container is running"""
    script_dir = Path(__file__).parent
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=scraper_mysql",
                "--filter",
                "status=running",
                "--quiet",
            ],
            capture_output=True,
            text=True,
        )
        if not result.stdout.strip():
            print("🔄 Starting MySQL container...")
            subprocess.run(["docker-compose", "up", "-d", "mysql"], cwd=script_dir, check=True)
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


def run_interactive_session(url: str):
    """Run the interactive scraperbot session"""
    script_dir = Path(__file__).parent

    print("🤖 Interactive ScraperBot CLI")
    print("=" * 50)
    print(f"🌐 URL: {url}")

    # Step 1: Run scraper to populate database
    print("\n📊 Step 1: Scraping and analyzing website...")
    try:
        # Use a timeout to prevent hanging
        result = subprocess.run(
            [
                "docker-compose",
                "run",
                "--rm",
                "scraper",
                "timeout",
                "180",
                "bash",
                "-c",
                f'echo "{url}" | python3 scraperbot.py',
            ],
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=200,
        )

        # Check if scraping was successful by looking for success indicators
        if "Database schema created and populated successfully!" in result.stdout:
            print("✅ Scraping completed successfully!")
        elif result.returncode != 0:
            print("❌ Scraping may have failed. Let's try to continue anyway...")
            print("Output:", result.stdout[-500:])  # Show last 500 chars
        else:
            print("✅ Scraping process completed!")

    except subprocess.TimeoutExpired:
        print("⚠️  Scraping timed out, but database may still be populated")
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        return False

    print("\n🔍 Step 2: Interactive Q&A Session")
    print("💡 Ask questions about the scraped data")
    print("💡 Type 'quit', 'exit', or 'q' to end")
    print("=" * 50)

    # Step 2: Interactive question loop
    while True:
        try:
            question = input("\n❓ Your question: ").strip()

            if not question:
                continue

            if question.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break

            print("🤔 Thinking...")

            # Escape question for safe shell usage
            safe_question = question.replace('"', '\\"').replace("'", "'\"'\"'")

            # Run question in container
            try:
                result = subprocess.run(
                    [
                        "docker-compose",
                        "run",
                        "--rm",
                        "scraper",
                        "bash",
                        "-c",
                        f"""
python3 -c "
import asyncio
import sys
import os
sys.path.append('/app')

async def ask_question():
    from scraperbot import question_to_sql_workflow, translate_response_workflow
    from database_tools import DatabaseTools
    
    question = '{safe_question}'
    
    db_host = os.environ.get('DB_HOST', 'mysql')
    db_connection = f'mysql://root:scraper_root_pass@{{db_host}}:3306/scraper_db'
    
    try:
        db_tools = DatabaseTools(db_connection)
        
        # Check what tables exist
        schema = db_tools.get_database_schema()
        if schema['success'] and schema['schema']['tables']:
            table_names = [t['name'] for t in schema['schema']['tables']]
            print(f'📋 Available tables: {{table_names}}')
        else:
            print('⚠️  No tables found in database')
            return
        
        # Process the question
        sql_query, query_result = await question_to_sql_workflow(question, db_tools)
        
        if query_result and query_result.get('success'):
            answer = await translate_response_workflow(question, sql_query, query_result, db_tools)
            print(f'\\n📊 {{answer}}')
            print(f'\\n🔧 SQL: {{sql_query}}')
        else:
            error = query_result.get('error', 'Unknown error') if query_result else 'No result'
            print(f'❌ Could not answer: {{error}}')
            
    except Exception as e:
        print(f'❌ Error: {{e}}')

asyncio.run(ask_question())
"
                    """,
                    ],
                    cwd=script_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Print the output from the container
                if result.stdout:
                    print(result.stdout)
                if result.stderr and result.returncode != 0:
                    print(f"Error: {result.stderr}")

            except subprocess.TimeoutExpired:
                print("⏰ Question timed out. Try a simpler question.")
            except Exception as e:
                print(f"❌ Error: {e}")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break

    return True


def main():
    parser = argparse.ArgumentParser(description="Interactive ScraperBot CLI")
    parser.add_argument("url", help="URL to scrape")

    args = parser.parse_args()

    # Ensure MySQL is running
    if not ensure_mysql_running():
        sys.exit(1)

    try:
        run_interactive_session(args.url)
    except KeyboardInterrupt:
        print("\n👋 Cancelled")
        sys.exit(0)


if __name__ == "__main__":
    main()
