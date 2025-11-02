"""web_fetch skill

Provides a simple fetch_url function to perform HTTP GET requests.
"""

from typing import Optional, Dict, Any
import base64
import requests
import time

# Provide a noop decorator if skill system's decorator isn't available in this environment
try:
    from agent import skill_function  # type: ignore
except Exception:
    def skill_function(func):
        return func


@skill_function
def fetch_url(
    url: str,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    verify_ssl: bool = True,
    allow_redirects: bool = True,
    max_content_bytes: int = 5_000_000,
) -> Dict[str, Any]:
    """Perform an HTTP GET request and return a JSON-serializable summary.

    Returns dict with keys:
      - status_code (int | None)
      - headers (dict)
      - url (final URL or None)
      - elapsed_seconds (float | None)
      - ok (bool)
      - reason (str | None)
      - text (string)
      - content_base64 (string)
      - truncated (bool)
      - error (null or string)
    """
    result: Dict[str, Any] = {
        "status_code": None,
        "headers": {},
        "url": None,
        "elapsed_seconds": None,
        "ok": False,
        "reason": None,
        "text": "",
        "content_base64": "",
        "truncated": False,
        "error": None,
    }

    if headers is None:
        headers = {}
    if params is None:
        params = {}

    try:
        start = time.time()
        resp = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=timeout,
            verify=verify_ssl,
            allow_redirects=allow_redirects,
        )
        elapsed = time.time() - start

        content: bytes = resp.content or b""
        truncated = False
        if len(content) > max_content_bytes:
            truncated = True
            content_to_use = content[:max_content_bytes]
        else:
            content_to_use = content

        # Decode to text using response.encoding or utf-8 with replacement
        enc = resp.encoding if resp.encoding else "utf-8"
        try:
            text = content_to_use.decode(enc, errors="replace")
        except Exception:
            text = content_to_use.decode("utf-8", errors="replace")

        content_b64 = base64.b64encode(content_to_use).decode("ascii")

        result.update(
            {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "url": resp.url,
                "elapsed_seconds": float(elapsed),
                "ok": resp.ok,
                "reason": resp.reason if hasattr(resp, "reason") else None,
                "text": text,
                "content_base64": content_b64,
                "truncated": truncated,
                "error": None,
            }
        )

        return result

    except requests.RequestException as e:
        # Common requests errors: connection, timeout, invalid URL, SSL, etc.
        result.update({
            "error": str(e),
            "reason": None,
            "ok": False,
        })
        return result
    except Exception as e:  # pragma: no cover - defensive
        result.update({
            "error": str(e),
            "reason": None,
            "ok": False,
        })
        return result
