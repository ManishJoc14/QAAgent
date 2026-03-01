from __future__ import annotations

import json
import re
import ssl
import urllib.request
from html.parser import HTMLParser
from typing import Any

from engine.tools.base import BaseTool, ToolExecutionResult


def _format_finding_line(detail: dict[str, Any]) -> str:
    return (
        f"{str(detail['severity']).upper()} | {detail['code']} | "
        f"{detail['location']} | {detail['message']}"
    )


def _attrs_to_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in attrs:
        out[(key or "").lower()] = value or ""
    return out


def _parse_max_fixed_width(style: str) -> int | None:
    values = re.findall(r"width\s*:\s*(\d+)px", style, flags=re.IGNORECASE)
    if not values:
        return None
    return max(int(value) for value in values)


class _ResponsiveParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.viewport_meta_found = False
        self.fixed_width_elements: list[dict[str, Any]] = []
        self._index = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        attr = _attrs_to_dict(attrs)
        self._index += 1

        if tag_name == "meta" and attr.get("name", "").strip().lower() == "viewport":
            content = attr.get("content", "").lower()
            if "width=device-width" in content:
                self.viewport_meta_found = True
            return

        style = attr.get("style", "")
        fixed_style_width = _parse_max_fixed_width(style)
        fixed_attr_width = int(attr["width"]) if attr.get("width", "").isdigit() else None
        fixed_width = None
        if fixed_style_width is not None and fixed_attr_width is not None:
            fixed_width = max(fixed_style_width, fixed_attr_width)
        else:
            fixed_width = fixed_style_width if fixed_style_width is not None else fixed_attr_width

        if fixed_width is None:
            return
        if fixed_width >= 768:
            self.fixed_width_elements.append(
                {
                    "element_index": self._index,
                    "tag": tag_name,
                    "id": attr.get("id", "").strip(),
                    "fixed_width_px": fixed_width,
                }
            )


class ResponsiveLayoutCheckerTool(BaseTool):
    name = "responsive_layout_checker"
    description = "Check responsive layout risk signals such as missing viewport meta and large fixed widths."
    timeout_seconds = 45
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "overflow_risk_width_px": {"type": "integer", "minimum": 480, "maximum": 2000},
        },
        "required": [],
    }

    def __init__(self, fallback_url: str | None = None):
        self._fallback_url = fallback_url

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        url = str(arguments.get("url") or self._fallback_url or "").strip()
        if not url:
            return ToolExecutionResult(success=False, error="No URL provided")
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        overflow_threshold = int(arguments.get("overflow_risk_width_px", 768))
        overflow_threshold = max(480, min(overflow_threshold, 2000))

        try:
            html = self._download_html(url)
        except Exception as exc:
            return ToolExecutionResult(success=False, error=f"Failed to fetch page HTML: {exc}")

        parser = _ResponsiveParser()
        parser.feed(html)
        viewport_meta_found = parser.viewport_meta_found
        filtered = [item for item in parser.fixed_width_elements if item["fixed_width_px"] >= overflow_threshold]
        finding_details: list[dict[str, Any]] = []

        if not viewport_meta_found:
            finding_details.append(
                {
                    "code": "viewport_meta_missing_or_incorrect",
                    "severity": "high",
                    "location": url,
                    "message": "Responsive viewport meta (`width=device-width`) not found.",
                    "evidence": {},
                }
            )
        for item in filtered:
            finding_details.append(
                {
                    "code": "large_fixed_width_element",
                    "severity": "medium",
                    "location": f"{url}#element:{item['element_index']}",
                    "message": (
                        f"Element has fixed width {item['fixed_width_px']}px, which may overflow on smaller screens."
                    ),
                    "evidence": item,
                }
            )
        if not finding_details:
            finding_details.append(
                {
                    "code": "responsive_layout_risk_not_detected",
                    "severity": "info",
                    "location": url,
                    "message": "No obvious responsive layout risks detected by static checks.",
                    "evidence": {},
                }
            )

        findings = [_format_finding_line(item) for item in finding_details]
        payload = {
            "url": url,
            "mode": "static_html",
            "viewport_meta_found": viewport_meta_found,
            "overflow_risk_width_px": overflow_threshold,
            "large_fixed_width_count": len(filtered),
            "large_fixed_width_elements": filtered,
            "finding_details": finding_details,
            "findings": findings,
        }
        return ToolExecutionResult(
            success=True,
            output=json.dumps(payload),
            metadata={
                "url": url,
                "mode": payload["mode"],
                "viewport_meta_found": viewport_meta_found,
                "large_fixed_width_count": len(filtered),
            },
        )

    def _download_html(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "QABot-ResponsiveLayoutChecker/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
            return response.read().decode("utf-8", errors="replace")
