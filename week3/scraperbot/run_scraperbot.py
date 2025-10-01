#!/usr/bin/env python3
"""
Wrapper script to run scraperbot from the host system.
This handles environment setup and database connection properly.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the scraperbot directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Load environment variables from the repository root .env file
try:
    from dotenv import load_dotenv
    env_file = script_dir / ".." / ".." / ".env"
    load_dotenv(env_file)
    print(f"Loaded environment from: {env_file}")
except ImportError:
    print("python-dotenv not installed. Install with: pip install python-dotenv")
    print("Or ensure OPENAI_API_KEY is set in your environment")

# Set DB_HOST to localhost for host execution
os.environ["DB_HOST"] = "localhost"

def check_mysql_running():
    """Check if MySQL container is running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=scraper_mysql", "--filter", "status=running", "--quiet"],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False

def ensure_mysql_running():
    """Ensure MySQL container is running"""
    if not check_mysql_running():
        print("MySQL container not running. Starting it...")
        try:
            subprocess.run(
                ["docker-compose", "up", "-d", "mysql"],
                cwd=script_dir,
                check=True
            )
            print("Waiting for MySQL to be ready...")
            import time
            time.sleep(15)
        except subprocess.CalledProcessError as e:
            print(f"Failed to start MySQL container: {e}")
            sys.exit(1)
    else:
        print("MySQL container is already running")

if __name__ == "__main__":
    # Ensure MySQL is running
    ensure_mysql_running()
    
    # Import and run the main scraperbot
    try:
        from scraperbot import main
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error running scraperbot: {e}")
        sys.exit(1)