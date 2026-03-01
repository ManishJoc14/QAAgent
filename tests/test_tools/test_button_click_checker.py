import json

import pytest

from engine.tools.functional import ButtonClickCheckerTool


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
async def test_button_click_checker_reports_broken_click_patterns(monkeypatch):
    html = """
    <html>
      <body>
        <a href="/ok">ok</a>
        <a href="#">hash only</a>
        <a href="javascript:void(0)">js only</a>
        <button type="button">Active</button>
        <button type="button" disabled>Disabled</button>
        <div role="button">No click hint</div>
        <span role="button" tabindex="0">Focusable pseudo button</span>
      </body>
    </html>
    """

    def fake_urlopen(req, timeout=0, context=None):
        assert req.full_url == "https://example.com"
        assert req.get_method() == "GET"
        return _FakeResponse(status=200, body=html)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    tool = ButtonClickCheckerTool(fallback_url="https://example.com")
    result = await tool.execute({})

    assert result.success is True
    payload = json.loads(result.output or "{}")
    assert payload["anchor_count"] == 3
    assert payload["button_count"] == 2
    assert payload["role_button_count"] == 2
    assert len(payload["broken_anchors"]) == 2
    assert payload["disabled_button_count"] == 1
    assert len(payload["weak_role_buttons"]) == 1
    codes = {item["code"] for item in payload["finding_details"]}
    assert "broken_anchor_target" in codes
    assert "disabled_button_controls_detected" in codes
    assert "weak_role_button_pattern" in codes
