from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolExecutionResult:
    """Standardized output format for all tools."""

    success: bool = True
    output: str | dict | None = None
    error: str | None = None
    screenshot_base64: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Base interface for tools callable by the model."""

    name: str
    description: str
    input_schema: dict[str, Any]
    timeout_seconds: int = 30

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        raise NotImplementedError

    def to_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    async def close(self) -> None:
        """Optional cleanup hook for stateful tools."""
        return None

    @classmethod
    def fail(cls, error: str, metadata: dict[str, Any] | None = None) -> ToolExecutionResult:
        return cls(success=False, error=error, metadata=metadata or {})
