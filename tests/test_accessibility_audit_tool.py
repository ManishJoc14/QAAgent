import json

import pytest

from engine.tools.uiux import AccessibilityAuditTool


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
async def test_accessibility_audit_reports_alt_label_and_role_issues(monkeypatch):
    html = """
    <html>
      <body>
        <img src="/logo.png" />
        <img src="/hero.png" alt="Hero" />
        <input id="email" name="email" type="email" />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" />
        <div role="badrole"></div>
      </body>
    </html>
    """

    def fake_urlopen(req, timeout=0, context=None):
        assert req.full_url == "https://example.com"
        assert req.get_method() == "GET"
        return _FakeResponse(status=200, body=html)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    tool = AccessibilityAuditTool(fallback_url="https://example.com")
    result = await tool.execute({})
    assert result.success is True
    payload = json.loads(result.output or "{}")
    assert payload["missing_alt_count"] == 1
    assert payload["unlabeled_control_count"] == 1
    assert payload["invalid_aria_role_count"] == 1
    codes = {item["code"] for item in payload["finding_details"]}
    assert "image_missing_alt_text" in codes
    assert "form_control_missing_accessible_label" in codes
    assert "invalid_aria_role" in codes

