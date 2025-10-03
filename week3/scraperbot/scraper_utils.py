"""
Web Scraping Utility Functions
==============================

Simple utility functions for web scraping operations.
Used by the AI-powered scraperbot system.
"""

import requests
from bs4 import BeautifulSoup
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
from datetime import datetime


def fetch_page(url: str, delay: float = 1.0) -> Optional[BeautifulSoup]:
    """
    Fetch and parse a webpage, returning BeautifulSoup object.
    
    Args:
        url: The URL to fetch
        delay: Delay in seconds after request
        
    Returns:
        BeautifulSoup object or None if failed
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        time.sleep(delay)
        return BeautifulSoup(response.content, "html.parser")
    except requests.RequestException:
        return None


def analyze_site(url: str) -> Dict[str, Any]:
    """
    Analyze website structure to understand content patterns.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Dictionary containing site analysis results
    """
    soup = fetch_page(url)
    if not soup:
        return {"error": "Could not fetch page"}
    
    analysis = {
        "url": url,
        "title_options": [],
        "content_options": [],
        "metadata_patterns": {},
        "structure_info": {},
    }
    
    # Find potential title selectors
    title_candidates = []
    for selector in ["h1", "h2", "h3", ".title", ".headline", ".article-title", "title"]:
        elements = soup.select(selector)
        for elem in elements[:3]:  # Max 3 per selector type
            text = elem.get_text(strip=True)[:100]
            if text:
                title_candidates.append({
                    "selector": selector, 
                    "text": text, 
                    "length": len(text)
                })
    analysis["title_options"] = title_candidates
    
    # Find content containers (sorted by text amount)
    content_candidates = []
    for selector in ["article", ".content", ".article-body", ".post-content", "main", "div", "p"]:
        elements = soup.select(selector)
        if elements:
            total_text = 0
            sample_text = ""
            for elem in elements:
                elem_text = elem.get_text(strip=True)
                total_text += len(elem_text)
                if not sample_text and len(elem_text) > 50:
                    sample_text = elem_text[:200] + "..." if len(elem_text) > 200 else elem_text
            
            if total_text > 50:  # Only meaningful content
                content_candidates.append({
                    "selector": selector,
                    "total_text_length": total_text,
                    "element_count": len(elements),
                    "sample_text": sample_text,
                })
    
    # Sort by text content (descending)
    content_candidates.sort(key=lambda x: x["total_text_length"], reverse=True)
    analysis["content_options"] = content_candidates
    
    # Look for common metadata patterns
    metadata_selectors = {}
    for selector in [".author", ".date", ".price", ".rating", ".category", ".tags"]:
        elements = soup.select(selector)
        if elements:
            sample_text = elements[0].get_text(strip=True)[:50]
            if sample_text:
                metadata_selectors[selector] = sample_text
    analysis["metadata_patterns"] = metadata_selectors
    
    # Basic structure info
    analysis["structure_info"] = {
        "total_links": len(soup.find_all("a")),
        "total_images": len(soup.find_all("img")),
        "has_forms": len(soup.find_all("form")) > 0,
        "domain": urlparse(url).netloc,
    }
    
    return analysis


def suggest_config(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-suggest scraping configuration based on site analysis.
    
    Args:
        analysis: Output from analyze_site()
        
    Returns:
        Suggested configuration dictionary
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


def extract_basic_data(soup: BeautifulSoup, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract basic data from a page using the provided configuration.
    
    Args:
        soup: BeautifulSoup object of the page
        url: The original URL
        config: Configuration dictionary with selectors
        
    Returns:
        Dictionary containing extracted data
    """
    def extract_text(selector: str) -> Optional[str]:
        try:
            element = soup.select_one(selector)
            return element.get_text(strip=True) if element else None
        except Exception:
            return None
    
    title = extract_text(config.get("title_selector", "title"))
    content = extract_text(config.get("content_selector", "body"))
    
    metadata = {}
    for key, selector in config.get("metadata_selectors", {}).items():
        metadata[key] = extract_text(selector)
    
    # Add basic structural metadata
    metadata.update({
        "word_count": len(content.split()) if content else 0,
        "links_count": len(soup.find_all("a")),
        "images_count": len(soup.find_all("img")),
        "domain": urlparse(url).netloc,
    })
    
    return {
        "url": url,
        "title": title if title else "No Title",
        "content": content if content else "",
        "metadata": metadata,
        "scraped_at": datetime.now().isoformat(),
    }


# Wrapper class to maintain compatibility with existing code
class WebScraper:
    """
    Simple wrapper class for backward compatibility.
    Maintains the same interface as the original WebScraper.
    """
    
    def __init__(self, delay: float = 1.0, headers: Optional[Dict[str, str]] = None):
        self.delay = delay
    
    def analyze_site(self, url: str) -> Dict[str, Any]:
        """Analyze website structure"""
        return analyze_site(url)
    
    def suggest_config(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest scraping configuration"""
        return suggest_config(analysis)
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse webpage"""
        return fetch_page(url, self.delay)
    
    def scrape_multiple(self, urls: List[str], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape multiple URLs using configuration"""
        results = []
        for url in urls:
            soup = fetch_page(url, self.delay)
            if soup:
                data = extract_basic_data(soup, url, config)
                results.append(data)
        return results