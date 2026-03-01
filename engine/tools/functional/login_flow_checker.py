from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from engine.tools.base import BaseTool, ToolExecutionResult

if TYPE_CHECKING:
    from engine.tools.playwright import PlaywrightComputerTool


def _format_finding_line(detail: dict[str, Any]) -> str:
    return (
        f"{str(detail['severity']).upper()} | {detail['code']} | "
        f"{detail['location']} | {detail['message']}"
    )


class LoginFlowCheckerTool(BaseTool):
    """Check login surface and optionally attempt a credentialed login flow."""

    name = "login_flow_checker"
    description = "Inspect login surface and optionally attempt login using provided credentials."
    timeout_seconds = 90
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "auth_api_endpoint_contains": {"type": "string"},
            "success_selector": {"type": "string"},
            "auth_state_js": {"type": "string"},
            "token_storage_key": {"type": "string"},
            "include_screenshot": {"type": "boolean"},
        },
        "required": [],
    }

    def __init__(self, computer_tool: "PlaywrightComputerTool", fallback_url: str | None = None):
        self._computer = computer_tool
        self._fallback_url = fallback_url

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        await self._computer.ensure_ready()

        target_url = str(arguments.get("url") or self._computer.current_url or self._fallback_url or "").strip()
        if not target_url:
            return ToolExecutionResult(success=False, error="No URL available for login flow check")
        if not target_url.startswith(("http://", "https://")):
            target_url = f"https://{target_url}"

        username = str(arguments.get("username") or "").strip()
        password = str(arguments.get("password") or "").strip()
        include_screenshot = bool(arguments.get("include_screenshot", False))
        verification = {
            "auth_api_endpoint_contains": str(arguments.get("auth_api_endpoint_contains") or "").strip(),
            "success_selector": str(arguments.get("success_selector") or "").strip(),
            "auth_state_js": str(arguments.get("auth_state_js") or "").strip(),
            "token_storage_key": str(arguments.get("token_storage_key") or "").strip(),
        }
        verification = {k: v for k, v in verification.items() if v}

        try:
            if self._computer.current_url != target_url:
                await self._computer.navigate(target_url)
            surface = await self._computer.inspect_login_surface()
        except Exception as exc:
            return ToolExecutionResult(success=False, error=f"Failed to inspect login surface: {exc}")

        finding_details: list[dict[str, Any]] = []
        payload: dict[str, Any] = {
            "url": target_url,
            "login_surface": surface,
            "attempted_login": False,
            "login_result": None,
            "verification": {
                "mode": "deterministic" if verification else "heuristic",
                "requested_checks": verification,
            },
            "finding_details": finding_details,
            "findings": [],
        }

        has_login_surface = bool(surface.get("password_input_count", 0) > 0)
        if has_login_surface:
            finding_details.append(
                {
                    "code": "login_surface_detected",
                    "severity": "info",
                    "location": target_url,
                    "message": "Detected password field(s), login flow likely present.",
                    "evidence": surface,
                }
            )
        else:
            finding_details.append(
                {
                    "code": "no_login_surface_detected",
                    "severity": "medium",
                    "location": target_url,
                    "message": "No password fields detected on current page.",
                    "evidence": surface,
                }
            )

        if not username or not password:
            finding_details.append(
                {
                    "code": "login_attempt_skipped_missing_credentials",
                    "severity": "info",
                    "location": target_url,
                    "message": "No credentials provided; skipped login attempt.",
                    "evidence": {"username_provided": bool(username), "password_provided": bool(password)},
                }
            )
            payload["findings"] = [_format_finding_line(item) for item in finding_details]
            result = ToolExecutionResult(
                success=True,
                output=json.dumps(payload),
                metadata={
                    "url": target_url,
                    "attempted_login": False,
                    "login_surface_detected": has_login_surface,
                },
            )
            if include_screenshot:
                shot = await self._computer.execute({"action": "screenshot"})
                result.screenshot_base64 = shot.screenshot_base64
            return result

        try:
            try:
                login_result = await self._computer.attempt_login(
                    username=username,
                    password=password,
                    verification=verification,
                )
            except TypeError:
                # Backward compatibility for test doubles or older browser tool implementations.
                login_result = await self._computer.attempt_login(username=username, password=password)
        except Exception as exc:
            return ToolExecutionResult(success=False, error=f"Failed to execute login attempt: {exc}")

        payload["attempted_login"] = True
        payload["login_result"] = login_result

        mode = str(login_result.get("verification_mode") or ("deterministic" if verification else "heuristic"))
        if mode == "deterministic":
            if login_result.get("likely_success"):
                finding_details.append(
                    {
                        "code": "deterministic_verification_passed",
                        "severity": "info",
                        "location": str(login_result.get("after_url") or target_url),
                        "message": "Deterministic login checks passed.",
                        "evidence": {
                            "configured_checks": login_result.get("configured_checks", {}),
                            "deterministic_signals": login_result.get("deterministic_signals", {}),
                        },
                    }
                )
            else:
                finding_details.append(
                    {
                        "code": "deterministic_verification_failed",
                        "severity": "high",
                        "location": str(login_result.get("after_url") or target_url),
                        "message": "Deterministic login checks did not pass.",
                        "evidence": {
                            "configured_checks": login_result.get("configured_checks", {}),
                            "deterministic_signals": login_result.get("deterministic_signals", {}),
                        },
                    }
                )

        if login_result.get("likely_success"):
            finding_details.append(
                {
                    "code": "login_attempt_likely_successful",
                    "severity": "info",
                    "location": str(login_result.get("after_url") or target_url),
                    "message": "Login attempt appears successful.",
                    "evidence": login_result,
                }
            )
        else:
            finding_details.append(
                {
                    "code": "login_attempt_uncertain_or_failed",
                    "severity": "high",
                    "location": str(login_result.get("after_url") or target_url),
                    "message": "Login attempt did not show clear success signal.",
                    "evidence": login_result,
                }
            )
        if login_result.get("error_text_detected"):
            finding_details.append(
                {
                    "code": "auth_error_text_detected",
                    "severity": "high",
                    "location": str(login_result.get("after_url") or target_url),
                    "message": "Detected visible auth error text after submit.",
                    "evidence": login_result,
                }
            )
        payload["findings"] = [_format_finding_line(item) for item in finding_details]

        result = ToolExecutionResult(
            success=True,
            output=json.dumps(payload),
            metadata={
                "url": target_url,
                "attempted_login": True,
                "likely_success": bool(login_result.get("likely_success")),
            },
        )
        if include_screenshot:
            shot = await self._computer.execute({"action": "screenshot"})
            result.screenshot_base64 = shot.screenshot_base64
        return result
