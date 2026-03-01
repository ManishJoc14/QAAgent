from __future__ import annotations

from typing import Any


def build_user_prompt(
    target_url: str,
    task: str,
    context: dict[str, Any] | None = None,
) -> str:
    context_blob = ""
    if context:
        lines = [f"- {k}: {v}" for k, v in context.items()]
        context_blob = "\nAdditional context:\n" + "\n".join(lines)

    return (
        f"Target URL: {target_url}\n"
        f"Testing objective: {task}"
        f"{context_blob}\n"
        "Start by opening the target URL in the browser tool, then test systematically."
    )
