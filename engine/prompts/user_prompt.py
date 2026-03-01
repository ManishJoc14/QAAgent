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
        f"Testing objective: {task}\n"
        f"{context_blob}\n\n"
        "Instructions:\n"
        "1. Do not assume or guess any page state. Only report findings observed via the tools.\n"
        "2. Use the provided tools to systematically test the target URL.\n"
        "3. Collect evidence with screenshots, logs, or tool outputs whenever possible.\n"
        "4. If a tool fails or cannot collect evidence, report only the failure as a blocker.\n"
        "5. Always produce your final output strictly in the JSON schema defined by the system prompt.\n"
    )
