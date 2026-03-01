import json

import pytest

from engine.tools.functional import SessionPersistenceCheckerTool


class _FakeComputer:
    def __init__(self):
        self.current_url = "https://example.com"
        self._reload_count = 0

    async def ensure_ready(self):
        return None

    async def navigate(self, url: str):
        self.current_url = url

    async def reload(self):
        self._reload_count += 1

    async def get_cookies(self):
        if self._reload_count == 0:
            return [
                {"name": "sessionid", "value": "abc"},
                {"name": "pref", "value": "dark"},
                {"name": "auth_token", "value": "xyz"},
            ]
        return [
            {"name": "sessionid", "value": "abc"},
            {"name": "pref", "value": "dark"},
        ]


@pytest.mark.asyncio
async def test_session_persistence_checker_detects_dropped_session_cookie():
    tool = SessionPersistenceCheckerTool(
        computer_tool=_FakeComputer(), fallback_url="https://example.com"
    )
    result = await tool.execute({})

    assert result.success is True
    payload = json.loads(result.output or "{}")
    assert payload["cookie_count_before"] == 3
    assert payload["cookie_count_after"] == 2
    assert payload["session_cookie_names"] == ["auth_token", "sessionid"]
    assert payload["persisted_session_cookie_names"] == ["sessionid"]
    assert payload["dropped_session_cookie_names"] == ["auth_token"]
    codes = {item["code"] for item in payload["finding_details"]}
    assert "session_cookie_dropped_after_reload" in codes
