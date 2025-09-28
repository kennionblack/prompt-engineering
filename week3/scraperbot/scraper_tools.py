from tools import ToolBox

scraper_tool_box = ToolBox()


class ScraperTools:
    @scraper_tool_box.tool
    def fetch_url(url: str) -> str:
        """Fetches the content of the specified URL and returns it as a string."""
        import requests

        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            return f"Error fetching URL {url}: {e}"
