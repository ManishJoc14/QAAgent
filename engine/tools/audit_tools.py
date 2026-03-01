from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

from .base import BaseTool, ToolExecutionResult
from .playwright import PlaywrightComputerTool


class PageAuditTool(BaseTool):
    name = "page_audit"
    description = "Run a heuristic UX/accessibility/security content audit on the current page."
    timeout_seconds = 45
    input_schema = {
        "type": "object",
        "properties": {
            "include_screenshot": {"type": "boolean"},
        },
        "required": [],
    }

    def __init__(self, computer_tool: PlaywrightComputerTool):
        self._computer = computer_tool

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        include_screenshot = bool(arguments.get("include_screenshot", False))

        await self._computer.ensure_ready()
        snapshot = await self._computer.collect_page_snapshot()

        findings: list[str] = []
        if snapshot.get("missing_alt_images", 0) > 0:
            findings.append("Images missing alt text detected.")
        if snapshot.get("small_touch_targets", 0) > 0:
            findings.append("Touch targets below 44x44 detected.")
        if snapshot.get("unlabeled_form_controls", 0) > 0:
            findings.append("Form fields without accessible labels detected.")
        if snapshot.get("insecure_form_actions", 0) > 0:
            findings.append("Form action posting over HTTP detected.")
        if snapshot.get("mixed_content_references", 0) > 0:
            findings.append("HTTP mixed-content references found in page resources.")
        if snapshot.get("inline_script_blocks", 0) > 10:
            findings.append("High number of inline scripts; check CSP/XSS hardening.")

        result = ToolExecutionResult(
            success=True,
            output=json.dumps(
                {
                    "url": self._computer.current_url,
                    "snapshot": snapshot,
                    "findings": findings,
                }
            ),
            metadata={"url": self._computer.current_url},
        )

        if include_screenshot:
            shot = await self._computer.execute({"action": "screenshot"})
            result.screenshot_base64 = shot.screenshot_base64

        return result


class ConsoleNetworkAuditTool(BaseTool):
    name = "console_network_audit"
    description = "Return recent browser console errors/warnings and failed network requests."
    timeout_seconds = 20
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "minimum": 1, "maximum": 200},
        },
        "required": [],
    }

    def __init__(self, computer_tool: PlaywrightComputerTool):
        self._computer = computer_tool

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        limit = int(arguments.get("limit", 50))
        limit = max(1, min(limit, 200))

        console_events = await self._computer.get_console_events(limit=limit)
        request_failures = await self._computer.get_request_failures(limit=limit)

        return ToolExecutionResult(
            success=True,
            output=json.dumps(
                {
                    "url": self._computer.current_url,
                    "console_events": console_events,
                    "request_failures": request_failures,
                    "console_event_count": len(console_events),
                    "request_failure_count": len(request_failures),
                }
            ),
            metadata={"url": self._computer.current_url},
        )


class SecurityHeadersAuditTool(BaseTool):
    name = "security_headers_audit"
    description = "Inspect security-critical HTTP headers and cookie flags for a URL."
    timeout_seconds = 20
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
        },
        "required": [],
    }

    _expected_headers = [
        "strict-transport-security",
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "permissions-policy",
    ]

    def __init__(self, fallback_url: str | None = None):
        self._fallback_url = fallback_url

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        url = arguments.get("url") or self._fallback_url
        if not url:
            return ToolExecutionResult(success=False, error="No URL provided")
        if not str(url).startswith(("http://", "https://")):
            url = f"https://{url}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "QABot-SecurityAudit/1.0",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(
                req, timeout=15, context=ssl.create_default_context()
            ) as response:
                raw_headers = {k.lower(): v for k, v in response.headers.items()}
                set_cookie = response.headers.get_all("Set-Cookie") or []
                status = response.status
                final_url = response.geturl()
        except urllib.error.URLError as exc:
            return ToolExecutionResult(success=False, error=f"Failed to fetch URL headers: {exc}")

        missing_headers = [h for h in self._expected_headers if h not in raw_headers]

        weak_cookies = []
        for cookie in set_cookie:
            cookie_lower = cookie.lower()
            issues = []
            if "secure" not in cookie_lower:
                issues.append("missing Secure")
            if "httponly" not in cookie_lower:
                issues.append("missing HttpOnly")
            if "samesite" not in cookie_lower:
                issues.append("missing SameSite")
            if issues:
                weak_cookies.append({"cookie": cookie.split(";", 1)[0], "issues": issues})

        findings = []
        if missing_headers:
            findings.append("Missing recommended security headers")
        if weak_cookies:
            findings.append("Cookie hardening flags are incomplete")

        return ToolExecutionResult(
            success=True,
            output=json.dumps(
                {
                    "url": final_url,
                    "status": status,
                    "missing_headers": missing_headers,
                    "weak_cookies": weak_cookies,
                    "findings": findings,
                    "headers": {
                        k: raw_headers[k]
                        for k in sorted(raw_headers)
                        if k in self._expected_headers
                    },
                }
            ),
            metadata={"url": final_url, "status": status},
        )


class PerformanceAuditTool(BaseTool):
    name = "performance_audit"
    description = "Collect Core Web Vitals and page timing metrics from browser performance APIs."
    timeout_seconds = 30
    input_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, computer_tool: PlaywrightComputerTool):
        self._computer = computer_tool

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        await self._computer.ensure_ready()
        metrics = await self._computer.collect_perf_metrics()

        findings: list[str] = []
        lcp = metrics.get("lcp_ms")
        cls = metrics.get("cls")
        fcp = metrics.get("fcp_ms")
        if isinstance(lcp, int | float) and lcp > 2500:
            findings.append("LCP above 2.5s threshold.")
        if isinstance(fcp, (int, float)) and fcp > 1800:
            findings.append("FCP above 1.8s threshold.")
        if isinstance(cls, (int, float)) and cls > 0.1:
            findings.append("CLS above 0.1 threshold.")

        return ToolExecutionResult(
            success=True,
            output=json.dumps(
                {
                    "url": self._computer.current_url,
                    "metrics": metrics,
                    "findings": findings,
                }
            ),
            metadata={"url": self._computer.current_url},
        )
