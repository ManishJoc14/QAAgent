from __future__ import annotations

import json
import ssl
import urllib.request
from html.parser import HTMLParser
from typing import Any

from engine.tools.base import BaseTool, ToolExecutionResult

VALID_ARIA_ROLES = {
    "button",
    "link",
    "checkbox",
    "radio",
    "textbox",
    "combobox",
    "listbox",
    "menuitem",
    "tab",
    "tabpanel",
    "dialog",
    "navigation",
    "main",
    "banner",
    "contentinfo",
    "search",
    "status",
    "alert",
    "progressbar",
    "slider",
    "switch",
}


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


class _AccessibilityParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.labels_for_ids: set[str] = set()
        self.img_missing_alt: list[dict[str, Any]] = []
        self.unlabeled_controls: list[dict[str, Any]] = []
        self.invalid_roles: list[dict[str, Any]] = []
        self._control_index = 0
        self._img_index = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        attr = _attrs_to_dict(attrs)

        if tag_name == "label":
            control_id = attr.get("for", "").strip()
            if control_id:
                self.labels_for_ids.add(control_id)
            return

        role = attr.get("role", "").strip().lower()
        if role and role not in VALID_ARIA_ROLES:
            self.invalid_roles.append(
                {
                    "tag": tag_name,
                    "role": role,
                    "id": attr.get("id", "").strip(),
                }
            )

        if tag_name == "img":
            self._img_index += 1
            if "alt" not in attr or not attr.get("alt", "").strip():
                self.img_missing_alt.append(
                    {
                        "image_index": self._img_index,
                        "id": attr.get("id", "").strip(),
                        "src": attr.get("src", "").strip(),
                    }
                )
            return

        if tag_name not in {"input", "textarea", "select"}:
            return
        input_type = attr.get("type", "text").strip().lower()
        if input_type == "hidden":
            return

        self._control_index += 1
        control_id = attr.get("id", "").strip()
        has_label = bool(control_id and control_id in self.labels_for_ids)
        has_aria = bool(attr.get("aria-label", "").strip() or attr.get("aria-labelledby", "").strip())
        if not has_label and not has_aria:
            self.unlabeled_controls.append(
                {
                    "control_index": self._control_index,
                    "tag": tag_name,
                    "type": input_type,
                    "id": control_id,
                    "name": attr.get("name", "").strip(),
                }
            )


class AccessibilityAuditTool(BaseTool):
    name = "accessibility_audit"
    description = "Audit alt text, input labeling, and ARIA role validity from page HTML."
    timeout_seconds = 45
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
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

        try:
            html = self._download_html(url)
        except Exception as exc:
            return ToolExecutionResult(success=False, error=f"Failed to fetch page HTML: {exc}")
        parser = _AccessibilityParser()
        parser.feed(html)

        finding_details: list[dict[str, Any]] = []
        missing_alt = parser.img_missing_alt
        unlabeled_controls = parser.unlabeled_controls
        invalid_roles = parser.invalid_roles

        for item in missing_alt:
            finding_details.append(
                {
                    "code": "image_missing_alt_text",
                    "severity": "medium",
                    "location": f"{url}#img:{item['image_index']}",
                    "message": "Image is missing non-empty alt text.",
                    "evidence": item,
                }
            )
        for item in unlabeled_controls:
            hint = item["id"] or item["name"] or f"{item['tag']}[{item['type']}]"
            finding_details.append(
                {
                    "code": "form_control_missing_accessible_label",
                    "severity": "high",
                    "location": f"{url}#control:{item['control_index']}",
                    "message": f"Form control '{hint}' has no label/aria-label/aria-labelledby.",
                    "evidence": item,
                }
            )
        for item in invalid_roles:
            role = item["role"]
            finding_details.append(
                {
                    "code": "invalid_aria_role",
                    "severity": "medium",
                    "location": f"{url}#{item['tag']}",
                    "message": f"Invalid ARIA role '{role}' detected.",
                    "evidence": item,
                }
            )
        if not finding_details:
            finding_details.append(
                {
                    "code": "accessibility_markup_checks_passed",
                    "severity": "info",
                    "location": url,
                    "message": "No obvious accessibility markup issues detected by this audit.",
                    "evidence": {},
                }
            )

        findings = [_format_finding_line(item) for item in finding_details]
        payload = {
            "url": url,
            "mode": "static_html",
            "missing_alt_count": len(missing_alt),
            "unlabeled_control_count": len(unlabeled_controls),
            "invalid_aria_role_count": len(invalid_roles),
            "finding_details": finding_details,
            "findings": findings,
        }
        return ToolExecutionResult(
            success=True,
            output=json.dumps(payload),
            metadata={
                "url": url,
                "mode": payload["mode"],
                "missing_alt_count": len(missing_alt),
                "unlabeled_control_count": len(unlabeled_controls),
            },
        )

    def _download_html(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "QABot-AccessibilityAudit/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
            return response.read().decode("utf-8", errors="replace")
