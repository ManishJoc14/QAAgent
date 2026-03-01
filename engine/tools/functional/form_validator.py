from __future__ import annotations

import json
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


class _FormParser(HTMLParser):
    """
    Parse forms and input controls needed for static validation checks.
    """

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self.labels_for_ids: set[str] = set()
        self._current_form: dict[str, Any] | None = None
        self._id_counter = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        attr = _attrs_to_dict(attrs)

        if tag_name == "label":
            target = attr.get("for", "").strip()
            if target:
                self.labels_for_ids.add(target)
            return

        if tag_name == "form":
            self._id_counter += 1
            self._current_form = {
                "id": attr.get("id", "").strip(),
                "form_index": self._id_counter,
                "action": attr.get("action", "").strip(),
                "method": (attr.get("method", "get") or "get").lower(),
                "controls": [],
                "has_submit": False,
            }
            self.forms.append(self._current_form)
            return

        if self._current_form is None:
            return

        if tag_name in {"input", "textarea", "select"}:
            input_type = (attr.get("type", "text") or "text").lower()
            is_hidden = input_type == "hidden"
            if not is_hidden:
                self._current_form["controls"].append(
                    {
                        "tag": tag_name,
                        "type": input_type,
                        "name": attr.get("name", "").strip(),
                        "id": attr.get("id", "").strip(),
                        "required": "required" in attr,
                        "has_aria_label": bool(attr.get("aria-label", "").strip()),
                        "has_aria_labelledby": bool(attr.get("aria-labelledby", "").strip()),
                    }
                )
            if tag_name == "input" and input_type == "submit":
                self._current_form["has_submit"] = True
            return

        if tag_name == "button":
            button_type = (attr.get("type", "submit") or "submit").lower()
            if button_type == "submit":
                self._current_form["has_submit"] = True
            return

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form":
            self._current_form = None


class FormValidatorTool(BaseTool):
    """
    Validate basic form structure and required-field metadata.

    It wants to answer these questions:
    Does the page have forms?
    Do forms have submit buttons?
    Do required fields exist?
    Are form fields properly labeled?
    Are accessibility basics followed?
    """

    name = "form_validator"
    description = "Validate forms for required fields, labels, and submit controls."
    timeout_seconds = 45
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_forms": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "required": [],
    }

    def __init__(self, fallback_url: str | None = None):
        self._fallback_url = fallback_url

    def _form_locator(self, form: dict[str, Any]) -> str:
        form_id = str(form.get("id", "")).strip()
        if form_id:
            return f"form:{form_id}"
        return f"form_index:{form.get('form_index')}"

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        url = str(arguments.get("url") or self._fallback_url or "").strip()
        if not url:
            return ToolExecutionResult(success=False, error="No URL provided")
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        max_forms = int(arguments.get("max_forms", 30))
        max_forms = max(1, min(max_forms, 100))

        try:
            html = self._download_html(url)
        except Exception as exc:
            return ToolExecutionResult(success=False, error=f"Failed to fetch page HTML: {exc}")

        parser = _FormParser()
        parser.feed(html)
        forms = parser.forms[:max_forms]
        labels_for_ids = parser.labels_for_ids

        finding_details: list[dict[str, Any]] = []
        form_results: list[dict[str, Any]] = []
        required_fields = 0
        unlabeled_controls = 0
        forms_without_submit = 0

        for form in forms:
            controls = form["controls"]
            form_required = 0
            form_unlabeled = 0
            unlabeled_controls_in_form: list[dict[str, Any]] = []

            for control in controls:
                if control["required"]:
                    form_required += 1
                    required_fields += 1

                has_label = (
                    bool(control["id"] and control["id"] in labels_for_ids)
                    or bool(control["has_aria_label"])
                    or bool(control["has_aria_labelledby"])
                )
                if not has_label:
                    form_unlabeled += 1
                    unlabeled_controls += 1
                    control_location = f"{url}#{self._form_locator(form)}"
                    control_hint = (
                        control["id"] or control["name"] or f"{control['tag']}[{control['type']}]"
                    )
                    unlabeled_controls_in_form.append(
                        {
                            "id": control["id"],
                            "name": control["name"],
                            "tag": control["tag"],
                            "type": control["type"],
                        }
                    )
                    finding_details.append(
                        {
                            "code": "unlabeled_form_control",
                            "severity": "medium",
                            "location": control_location,
                            "message": (
                                f"Control '{control_hint}' is missing label association "
                                "(label/aria-label/aria-labelledby)."
                            ),
                            "evidence": {
                                "form_id": form["id"],
                                "form_index": form["form_index"],
                                "control": {
                                    "id": control["id"],
                                    "name": control["name"],
                                    "tag": control["tag"],
                                    "type": control["type"],
                                },
                            },
                        }
                    )

            if not form["has_submit"]:
                forms_without_submit += 1
                finding_details.append(
                    {
                        "code": "form_missing_submit_control",
                        "severity": "high",
                        "location": f"{url}#{self._form_locator(form)}",
                        "message": "Form has no submit button/input.",
                        "evidence": {
                            "form_id": form["id"],
                            "form_index": form["form_index"],
                        },
                    }
                )

            form_results.append(
                {
                    "id": form["id"],
                    "form_index": form["form_index"],
                    "control_count": len(controls),
                    "required_field_count": form_required,
                    "unlabeled_control_count": form_unlabeled,
                    "unlabeled_controls": unlabeled_controls_in_form,
                    "has_submit_control": form["has_submit"],
                }
            )

        if not forms:
            finding_details.append(
                {
                    "code": "no_forms_detected",
                    "severity": "info",
                    "location": url,
                    "message": "No forms detected on the page.",
                    "evidence": {},
                }
            )
        if required_fields == 0 and forms:
            finding_details.append(
                {
                    "code": "no_required_fields_detected",
                    "severity": "low",
                    "location": url,
                    "message": "No required fields detected; verify validation requirements.",
                    "evidence": {"form_count": len(forms)},
                }
            )

        if not finding_details:
            finding_details.append(
                {
                    "code": "form_validation_passed",
                    "severity": "info",
                    "location": url,
                    "message": "No obvious form-structure issues detected.",
                    "evidence": {"form_count": len(forms)},
                }
            )
        findings = [_format_finding_line(item) for item in finding_details]

        payload = {
            "url": url,
            "form_count": len(forms),
            "required_field_count": required_fields,
            "unlabeled_control_count": unlabeled_controls,
            "forms_without_submit_count": forms_without_submit,
            "forms": form_results,
            "finding_details": finding_details,
            "findings": findings,
        }

        return ToolExecutionResult(
            success=True,
            output=json.dumps(payload),
            metadata={
                "url": url,
                "form_count": len(forms),
                "unlabeled_control_count": unlabeled_controls,
            },
        )

    def _download_html(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "QABot-FormValidator/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(
            req, timeout=20, context=ssl.create_default_context()
        ) as response:
            return response.read().decode("utf-8", errors="replace")
