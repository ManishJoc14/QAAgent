from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from engine.tools.base import BaseTool, ToolExecutionResult

if TYPE_CHECKING:
    from engine.tools.playwright import PlaywrightComputerTool


def _format_finding_line(detail: dict[str, Any]) -> str:
    return (
        f"{str(detail['severity']).upper()} | {detail['code']} | "
        f"{detail['location']} | {detail['message']}"
    )


def _looks_like_session_cookie(name: str) -> bool:
    key = (name or "").lower()
    markers = ("session", "sess", "sid", "auth", "token", "jwt")
    return any(marker in key for marker in markers)


class SessionPersistenceCheckerTool(BaseTool):
    """Check whether likely session cookies persist across page reload."""

    name = "session_persistence_checker"
    description = "Check session-like cookie persistence before and after a page reload."
    timeout_seconds = 60
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
        },
        "required": [],
    }

    def __init__(self, computer_tool: PlaywrightComputerTool, fallback_url: str | None = None):
        self._computer = computer_tool
        self._fallback_url = fallback_url

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        await self._computer.ensure_ready()

        target_url = str(
            arguments.get("url") or self._computer.current_url or self._fallback_url or ""
        ).strip()
        if not target_url:
            return ToolExecutionResult(
                success=False, error="No URL available for session persistence check"
            )
        if not target_url.startswith(("http://", "https://")):
            target_url = f"https://{target_url}"

        try:
            if self._computer.current_url != target_url:
                await self._computer.navigate(target_url)

            before = await self._computer.get_cookies()
            await self._computer.reload()
            after = await self._computer.get_cookies()
        except Exception as exc:
            return ToolExecutionResult(
                success=False, error=f"Failed to check session persistence: {exc}"
            )

        before_map = {str(item.get("name", "")): item for item in before}
        after_map = {str(item.get("name", "")): item for item in after}
        session_names = sorted(
            name for name in before_map.keys() if _looks_like_session_cookie(name)
        )
        persisted = [name for name in session_names if name in after_map]
        dropped = [name for name in session_names if name not in after_map]

        finding_details: list[dict[str, Any]] = []
        if not before_map:
            finding_details.append(
                {
                    "code": "no_cookies_detected_before_reload",
                    "severity": "low",
                    "location": target_url,
                    "message": "No cookies detected before reload.",
                    "evidence": {},
                }
            )
        if before_map and not session_names:
            finding_details.append(
                {
                    "code": "no_session_like_cookies_detected",
                    "severity": "low",
                    "location": target_url,
                    "message": "No obvious session-like cookies detected.",
                    "evidence": {"cookie_count_before": len(before_map)},
                }
            )
        if dropped:
            for name in dropped:
                finding_details.append(
                    {
                        "code": "session_cookie_dropped_after_reload",
                        "severity": "high",
                        "location": f"{target_url}#cookie:{name}",
                        "message": f"Session-like cookie '{name}' was dropped after reload.",
                        "evidence": {"cookie_name": name},
                    }
                )
        if session_names and not dropped:
            finding_details.append(
                {
                    "code": "session_cookies_persisted",
                    "severity": "info",
                    "location": target_url,
                    "message": "Session-like cookies persisted after reload.",
                    "evidence": {"session_cookie_names": session_names},
                }
            )
        if not finding_details:
            finding_details.append(
                {
                    "code": "session_check_completed",
                    "severity": "info",
                    "location": target_url,
                    "message": "Session persistence check completed with no notable issues.",
                    "evidence": {},
                }
            )
        findings = [_format_finding_line(item) for item in finding_details]

        payload = {
            "url": target_url,
            "host": urlparse(target_url).hostname or "",
            "cookie_count_before": len(before_map),
            "cookie_count_after": len(after_map),
            "session_cookie_names": session_names,
            "persisted_session_cookie_names": persisted,
            "dropped_session_cookie_names": dropped,
            "finding_details": finding_details,
            "findings": findings,
        }

        return ToolExecutionResult(
            success=True,
            output=json.dumps(payload),
            metadata={
                "url": target_url,
                "cookie_count_before": len(before_map),
                "cookie_count_after": len(after_map),
                "dropped_session_cookie_count": len(dropped),
            },
        )
