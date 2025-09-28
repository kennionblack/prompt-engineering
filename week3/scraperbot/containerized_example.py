#!/usr/bin/env python3
"""
Containerized Scraper Example
============================

This example demonstrates using the scraper wit    print("1. docker-compose exec scraper python3 -c \"from database_tools import DatabaseTools; db = DatabaseTools('mysql://scraper_user:scraper_pass@mysql:3306/scraper_db'); print(db.get_database_schema())\")")   print("1. docker-compose exec scraper python3 -c \"from database_tools import DatabaseTools; db = DatabaseTools('mysql://scraper_user:scraper_pass@mysql:3306/scraper_db'); print(db.get_database_schema())\")")   print("1. docker-compose exec scraper python3 -c \"from database_tools import DatabaseTools; db = DatabaseTools('mysql://scraper_user:scraper_pass@mysql:3306/scraper_db'); print(db.get_database_schema())\")") a containerized MySQL database.
Run with: docker-compose up -d && docker-compose exec scraper python3 containerized_example.py
"""

import os
import json
import time
from database_tools import DatabaseTools
from example_scraper_enhanced import WebScraper


def wait_for_database(max_attempts=30, delay=2):
    """Wait for the database to be ready"""
    db_connection = os.getenv(
        "DB_CONNECTION", "mysql://scraper_user:scraper_pass@mysql:3306/scraper_db"
    )

    for attempt in range(max_attempts):
        try:
            print(f"Attempting to connect to database (attempt {attempt + 1}/{max_attempts})...")
            db_tools = DatabaseTools(db_connection)
            print("✅ Database connection successful!")
            return db_tools
        except Exception as e:
            print(f"❌ Database not ready: {e}")
            if attempt < max_attempts - 1:
                print(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)

    raise ConnectionError("Could not connect to database after maximum attempts")


def demonstrate_containerized_scraping():
    """Demonstrate the complete containerized scraping workflow"""

    print("🐳 Containerized Web Scraper Demo")
    print("=" * 50)

    # Step 1: Connect to containerized database
    print("\n📊 Step 1: Connecting to containerized MySQL database...")
    db_tools = wait_for_database()

    # Step 2: Check database schema
    print("\n🗄️  Step 2: Checking database schema...")
    schema_result = db_tools.get_database_schema()
    if schema_result["success"]:
        schema = schema_result["schema"]
        print(f"Database: {schema['database']}")
        print(f"Tables found: {len(schema['tables'])}")
        for table in schema["tables"]:
            print(
                f"  - {table['name']}: {len(table['columns'])} columns, {len(table['sample_rows'])} sample rows"
            )
    else:
        print(f"❌ Failed to get schema: {schema_result['error']}")
        return

    # Step 3: Analyze and scrape a website
    print("\n🕷️  Step 3: Analyzing and scraping website...")
    scraper = WebScraper(delay=1.0)
    test_url = "https://httpbin.org/html"

    # Analyze the site
    analysis = scraper.analyze_site(test_url)
    if "error" not in analysis:
        print(f"✅ Site analysis successful:")
        print(f"   Title options: {len(analysis['title_options'])}")
        print(f"   Content options: {len(analysis['content_options'])}")

        # Get suggested configuration
        config = scraper.suggest_config(analysis)
        print(f"   Suggested config: {config}")

        # Scrape the content
        results = scraper.scrape_multiple([test_url], config)

        if results:
            result = results[0]
            print(f"✅ Scraping successful:")
            print(f"   Title: {result.title}")
            print(f"   Content length: {len(result.content)} characters")
            print(f"   Metadata: {len(result.metadata)} fields")

            # Step 4: Store in database
            print("\n💾 Step 4: Storing scraped data in database...")

            # Convert to database format
            data_to_store = {
                "url": result.url,
                "title": result.title,
                "content": result.content,
                "metadata": json.dumps(result.metadata),
                "scraped_at": result.scraped_at,
            }

            # Insert into database
            insert_query = """
            INSERT INTO scraped_content (url, title, content, metadata, scraped_at)
            VALUES (%(url)s, %(title)s, %(content)s, %(metadata)s, %(scraped_at)s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                content = VALUES(content),
                metadata = VALUES(metadata),
                scraped_at = VALUES(scraped_at)
            """

            db_result = db_tools.execute_query(insert_query, data_to_store)

            if db_result["success"]:
                print("✅ Data stored successfully in database!")

                # Step 5: Verify the data
                print("\n🔍 Step 5: Verifying stored data...")
                verify_query = "SELECT id, url, title, CHAR_LENGTH(content) as content_length, scraped_at FROM scraped_content ORDER BY id DESC LIMIT 1"
                verify_result = db_tools.execute_query(verify_query)

                if verify_result["success"] and verify_result["rows"]:
                    stored_data = verify_result["rows"][0]
                    print("✅ Data verification successful:")
                    print(f"   ID: {stored_data['id']}")
                    print(f"   URL: {stored_data['url']}")
                    print(f"   Title: {stored_data['title']}")
                    print(f"   Content Length: {stored_data['content_length']} characters")
                    print(f"   Scraped At: {stored_data['scraped_at']}")
                else:
                    print("❌ Data verification failed")
            else:
                print(f"❌ Failed to store data: {db_result['error']}")
        else:
            print("❌ Scraping failed - no results")
    else:
        print(f"❌ Site analysis failed: {analysis['error']}")

    print("\n🎉 Containerized demo completed!")
    print("\nTo explore further:")
    print(
        "1. docker-compose exec scraper python3 -c \"from scraperbot import DatabaseTools; db = DatabaseTools('mysql://scraper_user:scraper_pass@mysql:3306/scraper_db'); print(db.get_database_schema())\""
    )
    print("2. docker-compose exec mysql mysql -u scraper_user -p scraper_db")
    print("3. Edit docker-compose.yml to modify database settings")


def show_database_contents():
    """Show current database contents"""
    print("\n📋 Current Database Contents:")
    print("-" * 30)

    db_tools = wait_for_database()

    # Show scraped content
    content_query = "SELECT id, url, title, CHAR_LENGTH(content) as content_length, scraped_at FROM scraped_content ORDER BY id DESC LIMIT 5"
    result = db_tools.execute_query(content_query)

    if result["success"]:
        print(f"Scraped Content ({len(result['rows'])} recent entries):")
        for row in result["rows"]:
            print(
                f"  ID {row['id']}: {row['title']} ({row['content_length']} chars) - {row['scraped_at']}"
            )

    # Show configurations
    config_query = "SELECT id, site_name, base_url, title_selector FROM scraper_configs ORDER BY id"
    result = db_tools.execute_query(config_query)

    if result["success"]:
        print(f"\nScraper Configurations ({len(result['rows'])} total):")
        for row in result["rows"]:
            print(f"  {row['site_name']}: {row['base_url']} (title: {row['title_selector']})")


if __name__ == "__main__":
    try:
        demonstrate_containerized_scraping()
        show_database_contents()

    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure containers are running: docker-compose ps")
        print("2. Check database health: docker-compose logs mysql")
        print("3. Verify network connectivity: docker-compose exec scraper ping mysql")
