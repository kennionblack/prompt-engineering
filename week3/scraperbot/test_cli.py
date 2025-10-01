#!/usr/bin/env python3
"""
Simple test script to verify the interactive CLI functionality
"""
import subprocess
import sys
import time

def test_cli():
    """Test the interactive CLI with a few questions"""
    
    print("🧪 Testing ScraperBot Interactive CLI")
    print("=" * 50)
    
    # Questions to test
    questions = [
        "What tables do we have?",
        "How many pages did we scrape?", 
        "What is the title of the scraped page?",
        "What metadata do we have?",
        "exit"
    ]
    
    # Prepare input for the CLI
    input_text = "\n".join(questions)
    
    try:
        # Run the CLI with input
        process = subprocess.Popen(
            ["python3", "clean_interactive.py", "http://books.toscrape.com/"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/home/kennion/401/prompt-engineering/week3/scraperbot"
        )
        
        stdout, stderr = process.communicate(input=input_text, timeout=60)
        
        print("STDOUT:")
        print(stdout)
        
        if stderr:
            print("\nSTDERR:")
            print(stderr)
            
        return process.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ CLI test timed out")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_cli()
    print(f"\n{'✅ CLI test passed!' if success else '❌ CLI test failed!'}")
    sys.exit(0 if success else 1)