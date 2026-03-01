from __future__ import annotations

import json
import socket
import ssl
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from ..base import BaseTool, ToolExecutionResult


class SSLAuditTool(BaseTool):
    name = "ssl_audit"
    description = (
        "Checks HTTPS availability, certificate validity, TLS version, and HSTS policy for a URL."
    )
    timeout_seconds = 20

    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
        },
        "required": ["url"],
    }

    def __init__(self, fallback_url: Optional[str] = None):
        self.fallback_url = fallback_url

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        url = arguments.get("url") or self.fallback_url

        if not url:
            return ToolExecutionResult(success=False, error="No URL provided")

        if not str(url).startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 443

        if not host:
            return ToolExecutionResult(success=False, error="Invalid URL")

        findings: list[str] = []
        metadata: dict[str, Any] = {"url": url}

        # SSL / TLS CHECK
        # ----------------------------
        try:
            context = ssl.create_default_context()

            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()

                    # TLS Version
                    tls_version = ssock.version()
                    metadata["tls_version"] = tls_version
                    findings.append(f"TLS version: {tls_version}")

                    # Certificate issuer
                    issued_by = "Unknown"
                    for attribute in cert.get("issuer", ()):
                        for key, value in attribute:
                            if key == "organizationName":
                                issued_by = value
                                break

                    findings.append(f"Issued by: {issued_by}")

                    # Certificate validity
                    try:
                        not_before = datetime.strptime(
                            cert["notBefore"], "%b %d %H:%M:%S %Y %Z"
                        ).replace(tzinfo=timezone.utc)

                        not_after = datetime.strptime(
                            cert["notAfter"], "%b %d %H:%M:%S %Y %Z"
                        ).replace(tzinfo=timezone.utc)

                        now = datetime.now(timezone.utc)

                        if now < not_before:
                            findings.append(
                                f"Certificate not yet valid (starts {not_before.isoformat()})"
                            )

                        if now > not_after:
                            findings.append(f"Certificate expired ({not_after.isoformat()})")

                        metadata["certificate_expiry"] = not_after.isoformat()

                    except Exception:
                        findings.append("Could not parse certificate validity dates.")

        except ssl.SSLError as e:
            return ToolExecutionResult(success=False, error=f"SSL error: {str(e)}")
        except socket.gaierror:
            return ToolExecutionResult(success=False, error="DNS resolution failed")
        except Exception as e:
            return ToolExecutionResult(success=False, error=f"SSL connection failed: {str(e)}")

        # HSTS CHECK
        # ----------------------------
        try:
            req = urllib.request.Request(
                url,
                method="GET",
                headers={"User-Agent": "SecurityAuditBot/1.0"},
            )

            with urllib.request.urlopen(
                req,
                timeout=10,
                context=ssl.create_default_context(),
            ) as response:
                hsts_header = response.headers.get("Strict-Transport-Security")

                if hsts_header:
                    findings.append(f"HSTS header present: {hsts_header}")
                else:
                    findings.append("HSTS header missing")

        except Exception as e:
            findings.append(f"HSTS check failed: {str(e)}")

        if not findings:
            findings = ["No issues detected"]

        return ToolExecutionResult(
            success=True,
            output=json.dumps(
                {
                    "url": url,
                    "findings": findings,
                }
            ),
            metadata=metadata,
        )
