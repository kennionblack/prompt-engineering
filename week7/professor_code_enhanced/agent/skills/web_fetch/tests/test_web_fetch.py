import base64
import pytest

from web_fetch.main import fetch_url


class DummyResponse:
    def __init__(self, content: bytes, status_code=200, url="http://example.com", headers=None, encoding=None, reason="OK", ok=True):
        self.content = content
        self.status_code = status_code
        self.url = url
        self.headers = headers or {"Content-Type": "text/plain"}
        self.encoding = encoding
        self.reason = reason
        self.ok = ok


def test_fetch_small_content(monkeypatch):
    content = b"hello world"

    def fake_get(*args, **kwargs):
        return DummyResponse(content)

    monkeypatch.setattr("requests.get", fake_get)

    res = fetch_url("http://example.com")
    assert res["status_code"] == 200
    assert res["text"].startswith("hello")
    assert base64.b64decode(res["content_base64"]) == content
    assert res["truncated"] is False
    assert res["error"] is None


def test_fetch_truncated(monkeypatch):
    content = b"A" * (5_000_010)

    def fake_get(*args, **kwargs):
        return DummyResponse(content)

    monkeypatch.setattr("requests.get", fake_get)

    res = fetch_url("http://example.com")
    assert res["truncated"] is True
    decoded = base64.b64decode(res["content_base64"])  # should be truncated
    assert len(decoded) == 5_000_000


def test_fetch_exception(monkeypatch):
    def fake_get(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr("requests.get", fake_get)

    res = fetch_url("http://bad-url")
    assert res["error"] is not None
    assert res["status_code"] is None
    assert res["ok"] is False
