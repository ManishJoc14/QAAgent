from __future__ import annotations

import json
import ssl
import urllib.request
from typing import Any, Optional

from ..base import BaseTool, ToolExecutionResult


class SecurityHeadersAuditTool(BaseTool):
    name = "security_headers_audit"
    description = "Inspect security-critical HTTP headers and cookie flags for a URL."
    timeout_seconds = 20
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
        },
        "required": ["url"],
    }

    _expected_headers = [
        "strict-transport-security",
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "permissions-policy",
    ]

    def __init__(self, fallback_url: Optional[str] = None):
        self.fallback_url = fallback_url

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        url = arguments.get("url") or self.fallback_url

        if not url:
            return ToolExecutionResult(success=False, error="No URL provided")

        if not str(url).startswith(("http://", "https://")):
            url = f"https://{url}"

        req = urllib.request.Request(
            url, headers={"User-Agent": "QABot-SecurityAudit/1.0"}, method="GET"
        )
        try:
            with urllib.request.urlopen(
                req, timeout=15, context=ssl.create_default_context()
            ) as resp:
                raw_headers = {k.lower(): v for k, v in resp.headers.items()}
                set_cookies = resp.headers.get_all("Set-Cookie") or []
                status = resp.status
                final_url = resp.geturl()
        except Exception as e:
            return ToolExecutionResult(success=False, error=str(e))

        # Analyze headers
        missing_headers = [h for h in self._expected_headers if h not in raw_headers]

        # Analyze cookies
        weak_cookies = []
        for cookie in set_cookies:
            issues = []
            c_lower = cookie.lower()
            if "secure" not in c_lower:
                issues.append("missing Secure")
            if "httponly" not in c_lower:
                issues.append("missing HttpOnly")
            if "samesite" not in c_lower:
                issues.append("missing SameSite")
            if issues:
                weak_cookies.append({"cookie": cookie.split(";", 1)[0], "issues": issues})

        findings = missing_headers + [f"Cookie issues: {c['cookie']}" for c in weak_cookies]
        if not findings:
            findings = ["No issues detected"]

        return ToolExecutionResult(
            success=True,
            output=json.dumps(
                {
                    "url": final_url,
                    "status": status,
                    "missing_headers": missing_headers,
                    "weak_cookies": weak_cookies,
                    "findings": findings,
                }
            ),
            metadata={"url": final_url, "status": status},
        )
