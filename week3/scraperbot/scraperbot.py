from pathlib import Path
import asyncio
import sys
import json
import os
import requests
from urllib.parse import urlparse
from datetime import datetime

from openai import AsyncOpenAI
from database_tools import DatabaseTools


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class PromptTextInsertion:
    def replace_keyword(original_text: str, keyword: str, replacement: str) -> str:
        """Replaces all occurrences of ${keyword} in original_text with replacement."""
        return original_text.replace(f"${{{keyword}}}", replacement)

    def replace_keywords(original_text: str, replacements: dict[str, str]) -> str:
        """Replaces all occurrences of ${keyword} in original_text with replacement for each key, value pair in replacements."""
        for key, value in replacements.items():
            original_text = PromptTextInsertion.replace_keyword(original_text, key, value)
        return original_text

    def populate_prompt(prompt_path: Path, replacements: dict[str, str]) -> str:
        """Reads the prompt file at prompt_path and replaces all occurrences of ${keyword} in the prompt with replacement for each key, value pair in replacements."""
        try:
            prompt_text = Path(prompt_path).read_text()
            return PromptTextInsertion.replace_keywords(prompt_text, replacements)
        except FileNotFoundError:
            print(f"File ${prompt_path} does not exist at the specified location")
            return ""


def validate_url(url: str) -> bool:
    """Validate URL by making a fetch request."""
    try:
        # Add http:// if no scheme is provided
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Parse URL to check if it's valid
        parsed = urlparse(url)
        if not parsed.netloc:
            return False

        # Make a request to check if URL is accessible
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        return response.status_code == 200
    except Exception as e:
        print(f"URL validation error: {e}")
        return False


def get_url_content(url: str) -> str:
    """Fetch content from URL."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        return response.text
    except Exception as e:
        print(f"Error fetching URL content: {e}")
        return ""


async def scraper_workflow(url: str, db_tools: DatabaseTools):
    """First AI workflow: analyze URL content and create database schema with data."""
    from scraper_utils import WebScraper

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Use the enhanced scraper to analyze and extract structured data
    scraper = WebScraper(delay=1.0)
    print("Analyzing website...")

    analysis = scraper.analyze_site(url)
    if "error" in analysis:
        print(f"Failed to analyze website: {analysis['error']}")
        return False

    config = scraper.suggest_config(analysis)

    print("Extracting content...")
    # Get raw HTML content instead of processed text for better AI analysis
    raw_soup = scraper.fetch_page(url)
    if not raw_soup:
        print("Failed to fetch raw HTML content")
        return False

    # Extract basic info but keep raw HTML for analysis
    scraped_data = scraper.scrape_multiple([url], config)
    if not scraped_data:
        print("Failed to extract basic data from website")
        return False

    data = scraped_data[0]

    # Get raw HTML content for AI to analyze
    raw_html_content = str(raw_soup)

    # Use the build_scraper_prompt.md file as the system prompt
    build_prompt_text = Path("prompts/build_scraper_prompt.md").read_text()
    build_prompt = PromptTextInsertion.replace_keywords(
        build_prompt_text,
        {
            "URL": url,
            "TITLE": data.title,
            "CONTENT": raw_html_content[:5000],  # Provide more HTML content for analysis
            "METADATA": json.dumps(data.metadata, indent=2),
            "SCRAPED_AT": data.scraped_at,
        },
    )

    print("Processing website data with AI...")

    # Create AI client with database tools
    history = [{"role": "system", "content": build_prompt}]

    from database_tools import db_tool_box

    response = await client.responses.create(
        input=history, model="gpt-4o-mini", tools=db_tool_box.tools
    )

    history += response.output

    # Handle function calls (schema creation and data insertion)
    for item in response.output:
        if item.type == "function_call":
            # Call the method on the db_tools instance instead of the unbound function
            if hasattr(db_tools, item.name):
                method = getattr(db_tools, item.name)
                result = method(**json.loads(item.arguments))
                history.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result, cls=DateTimeEncoder),
                    }
                )

    print("✅ Data extracted and stored!")
    return True


async def question_to_sql_workflow(question: str, db_tools: DatabaseTools) -> tuple[str, dict]:
    """Second AI workflow: convert natural language question to SQL."""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Get database schema
    schema_result = db_tools.get_database_schema()
    if not schema_result["success"]:
        print(f"Failed to get database schema: {schema_result['error']}")
        return "", {}

    schema = schema_result["schema"]

    # Format schema for prompt
    schema_text = json.dumps(schema, indent=2, cls=DateTimeEncoder)

    # Get sample data for tables
    tables_output = {"tables": []}
    for table in schema["tables"]:
        if table["sample_rows"]:
            tables_output["tables"].append({"name": table["name"], "rows": table["sample_rows"]})

    tables_output_text = json.dumps(tables_output, indent=2, cls=DateTimeEncoder)

    # Prepare the convert_question_to_sql prompt
    sql_prompt_text = Path("prompts/convert_question_to_sql.md").read_text()
    sql_prompt = PromptTextInsertion.replace_keywords(
        sql_prompt_text,
        {"SCHEMA": schema_text, "QUESTION": question, "TABLES_OUTPUT": tables_output_text},
    )

    # Try to get SQL query with retry logic
    max_retries = 2
    for attempt in range(max_retries + 1):

        history = [{"role": "system", "content": sql_prompt}]

        response = await client.responses.create(input=history, model="gpt-4o-mini")

        sql_query = response.output_text.strip()

        # Execute the query
        query_result = db_tools.execute_query(sql_query)

        if query_result["success"]:
            return sql_query, query_result
        else:
            print(f"SQL execution failed: {query_result['error']}")
            if attempt < max_retries:
                print("Retrying with error feedback...")
                # Add error feedback to the conversation
                history.append(
                    {
                        "role": "user",
                        "content": f"The previous query failed with error: {query_result['error']}. Please provide a corrected SQL query.",
                    }
                )
            else:
                print("Max retries reached. Query failed.")
                return sql_query, query_result

    return "", {}


async def translate_response_workflow(
    question: str, sql_query: str, query_result: dict, db_tools: DatabaseTools
) -> str:
    """Third AI workflow: translate SQL results to natural language."""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Get database schema
    schema_result = db_tools.get_database_schema()
    schema_text = (
        json.dumps(schema_result["schema"], indent=2, cls=DateTimeEncoder)
        if schema_result["success"]
        else "Schema unavailable"
    )

    # Format query result
    query_result_text = json.dumps(query_result, indent=2, cls=DateTimeEncoder)

    # Prepare the translate_sql_response prompt
    translate_prompt_text = Path("prompts/translate_sql_response.md").read_text()
    translate_prompt = PromptTextInsertion.replace_keywords(
        translate_prompt_text,
        {
            "SCHEMA": schema_text,
            "QUERY": sql_query,
            "QUERY_RESULT": query_result_text,
            "USER_QUESTION": question,
        },
    )

    history = [{"role": "system", "content": translate_prompt}]

    response = await client.responses.create(input=history, model="gpt-4o-mini")

    return response.output_text


async def main():
    """Main scraperbot workflow."""
    print("Welcome to ScraperBot!")
    print(
        "This tool will scrape a website, create a database, and answer questions about the data."
    )
    print()

    # Step 1: Get and validate URL
    while True:
        url = input("Please enter a website URL to scrape: ").strip()
        if not url:
            print("Please enter a valid URL.")
            continue

        print(f"Validating URL: {url}")
        if validate_url(url):
            print("URL is valid!")
            break
        else:
            print("Invalid URL or unable to fetch content. Please try again.")

    # Use service name 'mysql' when running in container, otherwise localhost
    db_host = os.environ.get("DB_HOST", "mysql")  # Default to docker service name
    db_connection = f"mysql://root:scraper_root_pass@{db_host}:3306/scraper_db"

    try:
        db_tools = DatabaseTools(db_connection)
        print("Database connection established!")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        print("Make sure the database is running (docker-compose up -d)")
        return

    # Step 2: Scrape and analyze website content
    success = await scraper_workflow(url, db_tools)
    if not success:
        print("Failed to scrape and analyze website content.")
        return

    # Step 3: Interactive Q&A loop
    print("\nDatabase created and populated! You can now ask questions about the scraped data.")
    print("Type 'quit' to exit.")
    print()

    while True:
        question = input("Ask a question about the data: ").strip()

        if question.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not question:
            continue

        # Convert question to SQL and execute
        sql_query, query_result = await question_to_sql_workflow(question, db_tools)

        if not query_result or not query_result.get("success"):
            print("Sorry, I couldn't process your question. Please try rephrasing it.")
            continue

        # Translate results to natural language
        answer = await translate_response_workflow(question, sql_query, query_result, db_tools)

        # Check for FOLLOW UP or DONE indicators
        if "FOLLOW UP" in answer:
            answer = answer.replace("FOLLOW UP", "").strip()
            print(f"Answer: {answer}")
            continue
        elif "DONE" in answer:
            answer = answer.replace("DONE", "").strip()
            print(f"Answer: {answer}")
            print("Conversation ended.")
            break
        else:
            print(f"Answer: {answer}")


if __name__ == "__main__":
    asyncio.run(main())
