from __future__ import annotations

import json
import re
import ssl
import urllib.request
from html.parser import HTMLParser
from typing import Any

from engine.tools.base import BaseTool, ToolExecutionResult

MIN_TOUCH_TARGET = 44


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


def _parse_px(style: str, prop: str) -> int | None:
    pattern = rf"{prop}\s*:\s*(\d+)px"
    match = re.search(pattern, style, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


class _TouchTargetParser(HTMLParser):
    def __init__(self, min_size: int) -> None:
        super().__init__()
        self.min_size = min_size
        self.small_targets: list[dict[str, Any]] = []
        self.clickable_count = 0
        self._index = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        attr = _attrs_to_dict(attrs)

        is_clickable = (
            tag_name in {"a", "button"}
            or attr.get("role", "").strip().lower() == "button"
            or (tag_name == "input" and attr.get("type", "").strip().lower() in {"button", "submit", "reset"})
        )
        if not is_clickable:
            return

        self.clickable_count += 1
        self._index += 1
        style = attr.get("style", "")
        width = _parse_px(style, "width")
        height = _parse_px(style, "height")
        if width is None and attr.get("width", "").isdigit():
            width = int(attr["width"])
        if height is None and attr.get("height", "").isdigit():
            height = int(attr["height"])

        if width is None or height is None:
            return
        if width < self.min_size or height < self.min_size:
            self.small_targets.append(
                {
                    "target_index": self._index,
                    "tag": tag_name,
                    "id": attr.get("id", "").strip(),
                    "width_px": width,
                    "height_px": height,
                }
            )


class TouchTargetCheckerTool(BaseTool):
    name = "touch_target_checker"
    description = "Check whether clickable targets satisfy the 44x44px mobile touch guideline."
    timeout_seconds = 45
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "min_size_px": {"type": "integer", "minimum": 24, "maximum": 100},
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

        min_size = int(arguments.get("min_size_px", MIN_TOUCH_TARGET))
        min_size = max(24, min(min_size, 100))

        try:
            html = self._download_html(url)
        except Exception as exc:
            return ToolExecutionResult(success=False, error=f"Failed to fetch page HTML: {exc}")
        parser = _TouchTargetParser(min_size=min_size)
        parser.feed(html)
        small_targets = parser.small_targets
        clickable_count = parser.clickable_count

        finding_details: list[dict[str, Any]] = []
        for item in small_targets:
            finding_details.append(
                {
                    "code": "touch_target_below_minimum",
                    "severity": "medium",
                    "location": f"{url}#target:{item['target_index']}",
                    "message": (
                        f"Clickable target size {item['width_px']}x{item['height_px']}px is below "
                        f"{min_size}x{min_size}px guideline."
                    ),
                    "evidence": item,
                }
            )
        if not finding_details:
            finding_details.append(
                {
                    "code": "touch_target_check_passed",
                    "severity": "info",
                    "location": url,
                    "message": "No measurable undersized touch targets detected.",
                    "evidence": {"clickable_count": clickable_count},
                }
            )

        findings = [_format_finding_line(item) for item in finding_details]
        payload = {
            "url": url,
            "mode": "static_html",
            "min_size_px": min_size,
            "clickable_count": clickable_count,
            "small_target_count": len(small_targets),
            "small_targets": small_targets,
            "finding_details": finding_details,
            "findings": findings,
        }
        return ToolExecutionResult(
            success=True,
            output=json.dumps(payload),
            metadata={
                "url": url,
                "mode": payload["mode"],
                "small_target_count": len(small_targets),
                "clickable_count": clickable_count,
            },
        )

    def _download_html(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "QABot-TouchTargetChecker/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
            return response.read().decode("utf-8", errors="replace")
