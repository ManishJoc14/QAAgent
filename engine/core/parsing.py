from __future__ import annotations

import json
import re
from typing import Any


def extract_first_json_block(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or first >= last:
        return None

    try:
        return json.loads(text[first : last + 1])
    except json.JSONDecodeError:
        return None


def extract_issues(text: str | None) -> list[dict[str, Any]]:
    payload = extract_first_json_block(text)
    if not payload:
        return []
    issues = payload.get("issues")
    if isinstance(issues, list):
        return [i for i in issues if isinstance(i, dict)]
    return []
