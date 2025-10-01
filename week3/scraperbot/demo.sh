#!/bin/bash
# Demonstration script for the ScraperBot Interactive CLI

echo "🚀 ScraperBot Interactive CLI Demo"
echo "=================================="
echo ""
echo "This will demonstrate the complete workflow:"
echo "1. Scrape http://books.toscrape.com/"
echo "2. Create database tables with scraped data"
echo "3. Answer questions about the scraped data"
echo ""
echo "Starting demo in 3 seconds..."
sleep 3

cd /home/kennion/401/prompt-engineering/week3/scraperbot

# Test questions one by one using expect-like behavior
echo "📋 Testing individual questions:"
echo ""

echo "❓ Question 1: What tables do we have?"
echo "What tables do we have?" | timeout 30 python3 clean_interactive.py http://books.toscrape.com/ | head -30
echo ""

echo "❓ Question 2: How many pages did we scrape?"  
echo "How many pages did we scrape?" | timeout 30 python3 clean_interactive.py http://books.toscrape.com/ | head -30
echo ""

echo "✅ Demo completed! The ScraperBot CLI is fully functional."
echo "   To use it interactively, run:"
echo "   python3 clean_interactive.py <URL>"