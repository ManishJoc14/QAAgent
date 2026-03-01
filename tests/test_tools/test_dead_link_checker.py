import json
import urllib.error

import pytest

from engine.tools.functional import DeadLinkCheckerTool


class _FakeResponse:
    def __init__(self, status: int, body: str = ""):
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_dead_link_checker_detects_non_2xx_and_classifies_links(monkeypatch):
    html = """
    <html>
      <body>
        <a href="/ok">ok</a>
        <a href="/dead">dead</a>
        <a href="https://external.com/good">external good</a>
        <a href="https://external.com/bad">external bad</a>
        <a href="#skip">skip hash</a>
        <a href="mailto:test@example.com">skip mail</a>
      </body>
    </html>
    """

    def fake_urlopen(req, timeout=0, context=None):
        url = req.full_url
        method = req.get_method()

        if url == "https://example.com" and method == "GET":
            return _FakeResponse(status=200, body=html)
        if url == "https://example.com/ok" and method == "HEAD":
            return _FakeResponse(status=200)
        if url == "https://example.com/dead" and method == "HEAD":
            raise urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)
        if url == "https://external.com/good" and method == "HEAD":
            return _FakeResponse(status=200)
        if url == "https://external.com/bad" and method == "HEAD":
            raise urllib.error.URLError("DNS fail")
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    tool = DeadLinkCheckerTool(fallback_url="https://example.com")
    result = await tool.execute({})

    assert result.success is True
    payload = json.loads(result.output or "{}")
    assert payload["total_links_checked"] == 4
    assert payload["internal_links_checked"] == 2
    assert payload["external_links_checked"] == 2
    assert len(payload["dead_links"]) == 2
    dead_types = {item["type"] for item in payload["dead_links"]}
    assert dead_types == {"internal", "external"}
    assert len(payload["finding_details"]) >= 2
    assert all(
        {"code", "severity", "location", "message", "evidence"} <= set(item.keys())
        for item in payload["finding_details"]
    )
