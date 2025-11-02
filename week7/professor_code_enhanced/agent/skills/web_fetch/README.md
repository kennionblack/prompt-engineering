# web_fetch skill

Simple skill to perform HTTP GET requests using the requests library.

Features:
- Performs GET with configurable timeout, headers, params, SSL verification and redirects
- Returns a JSON-serializable dict with response metadata and both text and base64-encoded content
- Truncates content over a configurable max (default 5_000_000 bytes) and marks truncated=True
- Handles binary content by providing a text decode with replacement and a base64 content field
- Catches requests exceptions and returns an error field instead of raising

Dependencies:
- requests

Usage example
--------------

from web_fetch.main import fetch_url

res = fetch_url("https://example.com")
print(res["status_code"])  # 200
print(res["text"][:200])
print(res["content_base64"][:200])

Advanced options:
- timeout: integer seconds
- headers: dict of headers
- params: dict of query parameters
- verify_ssl: bool to enable/disable SSL verification (use with caution)
- allow_redirects: bool
- max_content_bytes: int override of the default 5_000_000 bytes limit

Tests
-----

A basic pytest file is included in tests/test_web_fetch.py demonstrating simple calls and error handling.

Security
--------
- Disabling SSL verification (verify_ssl=False) is allowed for flexibility but is insecure and should only be used for debugging/trusted environments.
- The skill reads the full response into memory; large responses may consume significant memory until truncated.

License
-------
MIT-style, minimal.
