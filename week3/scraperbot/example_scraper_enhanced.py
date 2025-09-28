"""
Enhanced Web Scraper with Site Analysis
=======================================

This EXAMPLE demonstrates the RECOMMENDED approach for scraping arbitrary websites:

1. ANALYZE FIRST: Use analyze_site() to understand the HTML structure
2. CONFIGURE: Create selectors based on the analysis results
3. SCRAPE: Extract data using the optimized configuration
4. STORE: Save structured data to MySQL database

This approach is much more reliable than guessing selectors!
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from datetime import datetime
import re

try:
    import mysql.connector
    from mysql.connector import Error

    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


@dataclass
class ScrapedData:
    """EXAMPLE: Data structure for scraped content"""

    url: str
    title: str
    content: str
    metadata: Dict[str, Any]
    scraped_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_mysql_values(self) -> tuple:
        return (
            self.url,
            self.title,
            self.content,
            json.dumps(self.metadata, ensure_ascii=False),
            datetime.fromisoformat(self.scraped_at.replace("Z", "+00:00")).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )


class WebScraper:
    """
    EXAMPLE: Enhanced scraper with site analysis capabilities

    RECOMMENDED WORKFLOW:
    1. scraper.analyze_site(sample_url) - Understand the structure
    2. Create configuration based on analysis results
    3. scraper.scrape_multiple(urls, config) - Extract data
    """

    def __init__(self, delay: float = 1.0, headers: Optional[Dict[str, str]] = None):
        self.delay = delay
        self.session = requests.Session()

        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if headers:
            default_headers.update(headers)
        self.session.headers.update(default_headers)

    def analyze_site(self, url: str) -> Dict[str, Any]:
        """
        EXAMPLE: Analyze website structure to determine optimal selectors

        This is the KEY METHOD that makes scraping arbitrary sites reliable!

        Usage:
        1. Run this on a sample page from your target site
        2. Review the returned analysis
        3. Choose the best selectors from the options provided
        4. Create your configuration using those selectors

        Returns structured analysis of:
        - Title element options (h1, h2, .title, etc.)
        - Content container options (sorted by text length)
        - Potential metadata selectors
        - Overall page structure info
        """
        soup = self.fetch_page(url)
        if not soup:
            return {"error": "Could not fetch page"}

        analysis = {
            "url": url,
            "title_options": [],
            "content_options": [],
            "metadata_patterns": {},
            "structure_info": {},
        }

        # STEP 1: Find potential title selectors
        title_candidates = []
        for selector in ["h1", "h2", "h3", ".title", ".headline", ".article-title", "title"]:
            elements = soup.select(selector)
            for elem in elements[:3]:  # Max 3 per selector type
                text = elem.get_text(strip=True)[:100]
                if text:
                    title_candidates.append(
                        {"selector": selector, "text": text, "length": len(text)}
                    )
        analysis["title_options"] = title_candidates

        # STEP 2: Find content containers (sorted by text amount)
        content_candidates = []
        for selector in [
            "article",
            ".content",
            ".article-body",
            ".post-content",
            "main",
            "div",
            "p",
        ]:
            elements = soup.select(selector)
            if elements:
                # Calculate total text in these elements
                total_text = 0
                sample_text = ""
                for elem in elements:
                    elem_text = elem.get_text(strip=True)
                    total_text += len(elem_text)
                    if not sample_text and len(elem_text) > 50:
                        sample_text = elem_text[:200] + "..." if len(elem_text) > 200 else elem_text

                if total_text > 50:  # Only meaningful content
                    content_candidates.append(
                        {
                            "selector": selector,
                            "total_text_length": total_text,
                            "element_count": len(elements),
                            "sample_text": sample_text,
                        }
                    )

        # Sort by text length (most content first)
        analysis["content_options"] = sorted(
            content_candidates, key=lambda x: x["total_text_length"], reverse=True
        )

        # STEP 3: Find potential metadata selectors
        metadata_patterns = {}
        for elem in soup.find_all(attrs={"class": True}):
            class_names = elem.get("class", [])
            if isinstance(class_names, str):
                class_names = [class_names]

            for class_name in class_names:
                # Look for common metadata patterns
                if any(
                    keyword in class_name.lower()
                    for keyword in [
                        "author",
                        "date",
                        "time",
                        "price",
                        "rating",
                        "category",
                        "tag",
                        "meta",
                    ]
                ):
                    text = elem.get_text(strip=True)[:100]
                    if text:
                        metadata_patterns[f".{class_name}"] = text

        analysis["metadata_patterns"] = metadata_patterns

        # STEP 4: Overall structure analysis
        analysis["structure_info"] = {
            "total_text_length": len(soup.get_text(strip=True)),
            "paragraph_count": len(soup.find_all("p")),
            "div_count": len(soup.find_all("div")),
            "heading_counts": {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)},
            "link_count": len(soup.find_all("a")),
            "image_count": len(soup.find_all("img")),
            "form_count": len(soup.find_all("form")),
        }

        return analysis

    def suggest_config(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        EXAMPLE: Auto-suggest configuration based on site analysis

        Takes the output from analyze_site() and suggests the best
        configuration options. You can use this as-is or modify based
        on your specific needs.
        """
        if "error" in analysis:
            return {"error": "Cannot suggest config - analysis failed"}

        config = {
            "title_selector": "title",  # fallback
            "content_selector": "body",  # fallback
            "metadata_selectors": {},
        }

        # Choose best title selector
        if analysis["title_options"]:
            # Prefer h1, then other headings, then specialized classes
            for option in analysis["title_options"]:
                if option["selector"] == "h1":
                    config["title_selector"] = "h1"
                    break
                elif option["selector"].startswith("h") and config["title_selector"] == "title":
                    config["title_selector"] = option["selector"]
                elif "title" in option["selector"] and config["title_selector"] == "title":
                    config["title_selector"] = option["selector"]

        # Choose best content selector
        if analysis["content_options"]:
            best_content = analysis["content_options"][0]  # Highest text content
            config["content_selector"] = best_content["selector"]

        # Add metadata selectors if found
        for selector, text in analysis["metadata_patterns"].items():
            key = selector.replace(".", "").replace("#", "")
            if any(keyword in key.lower() for keyword in ["author", "date", "price", "rating"]):
                config["metadata_selectors"][key] = selector

        return config

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse webpage"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)
            return BeautifulSoup(response.content, "html.parser")
        except requests.RequestException:
            return None

    def extract_data(self, soup: BeautifulSoup, url: str, config: Dict[str, Any]) -> ScrapedData:
        """Extract data using configuration"""
        title = self._extract_text(soup, config.get("title_selector", "title"))
        content = self._extract_text(soup, config.get("content_selector", "body"))

        metadata = {}
        for key, selector in config.get("metadata_selectors", {}).items():
            metadata[key] = self._extract_text(soup, selector)

        # Add structural metadata
        metadata.update(
            {
                "word_count": len(content.split()) if content else 0,
                "links_count": len(soup.find_all("a")),
                "images_count": len(soup.find_all("img")),
                "domain": urlparse(url).netloc,
                "has_forms": len(soup.find_all("form")) > 0,
                "heading_structure": {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)},
            }
        )

        return ScrapedData(
            url=url,
            title=self._clean_text(title) if title else "No Title",
            content=self._clean_text(content) if content else "",
            metadata=metadata,
            scraped_at=datetime.now().isoformat(),
        )

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extract text using CSS selector"""
        try:
            element = soup.select_one(selector)
            return element.get_text(strip=True) if element else None
        except Exception:
            return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        text = text.encode("utf-8", errors="ignore").decode("utf-8")
        return text.strip()

    def scrape_multiple(self, urls: List[str], config: Dict[str, Any]) -> List[ScrapedData]:
        """Scrape multiple URLs using configuration"""
        results = []
        for url in urls:
            soup = self.fetch_page(url)
            if soup:
                data = self.extract_data(soup, url, config)
                results.append(data)
        return results


class MySQLExporter:
    """MySQL database export functionality"""

    @staticmethod
    def export_to_mysql(
        data: List[ScrapedData],
        host: str,
        database: str,
        username: str,
        password: str,
        table_name: str = "scraped_data",
        port: int = 3306,
    ) -> bool:
        """Export scraped data to MySQL database"""
        if not MYSQL_AVAILABLE:
            return False

        if not data:
            return True

        try:
            connection = mysql.connector.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
            )

            cursor = connection.cursor()

            # Create table
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                url VARCHAR(2048) UNIQUE NOT NULL,
                title TEXT,
                content LONGTEXT,
                metadata JSON,
                scraped_at DATETIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_url (url(255)),
                INDEX idx_scraped_at (scraped_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_table_query)

            # Insert data
            insert_query = f"""
            INSERT INTO {table_name} (url, title, content, metadata, scraped_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                content = VALUES(content), 
                metadata = VALUES(metadata),
                scraped_at = VALUES(scraped_at)
            """

            for item in data:
                try:
                    cursor.execute(insert_query, item.to_mysql_values())
                except Error:
                    pass

            connection.commit()
            return True

        except Error:
            return False
        finally:
            if "connection" in locals() and connection.is_connected():
                cursor.close()
                connection.close()


if __name__ == "__main__":
    """
    EXAMPLE: Enhanced workflow with site analysis

    This demonstrates the RECOMMENDED approach for scraping any arbitrary website:
    1. Analyze the site structure first
    2. Use analysis to create optimal configuration
    3. Scrape with confidence
    """

    # STEP 1: Analyze the target site
    scraper = WebScraper(delay=1.0)
    test_url = "https://httpbin.org/html"

    print("STEP 1: Analyzing site structure...")
    analysis = scraper.analyze_site(test_url)

    if "error" not in analysis:
        print("\n=== SITE ANALYSIS RESULTS ===")
        print(f"URL: {analysis['url']}")

        print(f"\nTITLE OPTIONS (found {len(analysis['title_options'])}):")
        for option in analysis["title_options"][:3]:
            print(f"  {option['selector']}: '{option['text'][:50]}...'")

        print(f"\nCONTENT OPTIONS (found {len(analysis['content_options'])}):")
        for option in analysis["content_options"][:3]:
            print(
                f"  {option['selector']}: {option['total_text_length']} chars, {option['element_count']} elements"
            )
            if option["sample_text"]:
                print(f"    Sample: '{option['sample_text'][:100]}...'")

        print(f"\nMETADATA PATTERNS:")
        for selector, text in list(analysis["metadata_patterns"].items())[:5]:
            print(f"  {selector}: '{text[:50]}...'")

        # STEP 2: Auto-suggest optimal configuration
        print("\nSTEP 2: Generating optimal configuration...")
        suggested_config = scraper.suggest_config(analysis)
        print(f"Suggested config: {json.dumps(suggested_config, indent=2)}")

        # STEP 3: Test the configuration
        print("\nSTEP 3: Testing the configuration...")
        results = scraper.scrape_multiple([test_url], suggested_config)

        if results:
            print("\n=== SCRAPING RESULTS ===")
            result = results[0]
            print(f"URL: {result.url}")
            print(f"Title: {result.title}")
            print(f"Content length: {len(result.content)} characters")
            print(f"Content preview: '{result.content[:200]}...'")
            print(f"Metadata: {json.dumps(result.metadata, indent=2)}")

            # Show if we successfully captured the Moby Dick content
            if len(result.content) > 100:
                print("\n✅ SUCCESS: Content extraction working!")
            else:
                print("\n❌ ISSUE: Content extraction needs improvement")
                print("Try a different content selector from the analysis above.")

    else:
        print(f"Analysis failed: {analysis['error']}")
