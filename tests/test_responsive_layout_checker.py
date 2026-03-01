import json

import pytest

from engine.tools.uiux import ResponsiveLayoutCheckerTool


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
async def test_responsive_layout_checker_reports_viewport_and_fixed_width(monkeypatch):
    html = """
    <html>
      <head></head>
      <body>
        <div id="hero" style="width: 1200px;">Hero</div>
        <img id="big-image" width="1024" src="/big.png" />
      </body>
    </html>
    """

    def fake_urlopen(req, timeout=0, context=None):
        assert req.full_url == "https://example.com"
        assert req.get_method() == "GET"
        return _FakeResponse(status=200, body=html)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    tool = ResponsiveLayoutCheckerTool(fallback_url="https://example.com")
    result = await tool.execute({})
    assert result.success is True
    payload = json.loads(result.output or "{}")
    assert payload["viewport_meta_found"] is False
    assert payload["large_fixed_width_count"] == 2
    codes = {item["code"] for item in payload["finding_details"]}
    assert "viewport_meta_missing_or_incorrect" in codes
    assert "large_fixed_width_element" in codes

