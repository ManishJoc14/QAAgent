from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.tools.base import ToolExecutionResult


@dataclass
class QATask:
    """Input for a QA run."""

    target_url: str
    task: str = (
        "Explore the main user flow and report functional, UX, accessibility, "
        "performance, and security issues."
    )
    context: dict[str, Any] | None = None


@dataclass
class QAIssue:
    """Single issue reported by the agent."""

    title: str
    severity: str
    description: str
    category: str | None = None
    steps_to_reproduce: list[str] | None = None


@dataclass
class QAResult:
    """Structured result returned by the engine."""

    issues: list[dict[str, Any]] = field(default_factory=list)
    raw_model_output: str | None = None
    tool_outputs: list[ToolExecutionResult] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
