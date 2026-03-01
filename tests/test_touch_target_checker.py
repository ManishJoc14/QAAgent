import json

import pytest

from engine.tools.uiux import TouchTargetCheckerTool


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
async def test_touch_target_checker_reports_small_clickables(monkeypatch):
    html = """
    <html>
      <body>
        <a id="small-link" href="/x" style="width: 30px; height: 30px;">X</a>
        <button id="ok" style="width: 48px; height: 48px;">OK</button>
        <div role="button" id="small-div" style="width: 40px; height: 20px;"></div>
      </body>
    </html>
    """

    def fake_urlopen(req, timeout=0, context=None):
        assert req.full_url == "https://example.com"
        assert req.get_method() == "GET"
        return _FakeResponse(status=200, body=html)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    tool = TouchTargetCheckerTool(fallback_url="https://example.com")
    result = await tool.execute({})
    assert result.success is True
    payload = json.loads(result.output or "{}")
    assert payload["small_target_count"] == 2
    codes = {item["code"] for item in payload["finding_details"]}
    assert "touch_target_below_minimum" in codes

