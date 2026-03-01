import json

import pytest

from engine.tools.functional import FormValidatorTool


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
async def test_form_validator_reports_required_labels_and_submit(monkeypatch):
    html = """
    <html>
      <body>
        <form id="signup" action="/signup" method="post">
          <label for="email">Email</label>
          <input id="email" name="email" type="email" required />
          <input id="password" name="password" type="password" required />
          <button type="submit">Create account</button>
        </form>
        <form id="search" action="/search" method="get">
          <input name="q" type="text" />
        </form>
      </body>
    </html>
    """

    def fake_urlopen(req, timeout=0, context=None):
        assert req.full_url == "https://example.com"
        assert req.get_method() == "GET"
        return _FakeResponse(status=200, body=html)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    tool = FormValidatorTool(fallback_url="https://example.com")
    result = await tool.execute({})

    assert result.success is True
    payload = json.loads(result.output or "{}")
    assert payload["form_count"] == 2
    assert payload["required_field_count"] == 2
    assert payload["unlabeled_control_count"] == 2
    assert payload["forms_without_submit_count"] == 1
    codes = {item["code"] for item in payload["finding_details"]}
    assert "form_missing_submit_control" in codes
    assert "unlabeled_form_control" in codes
