from typing import Any

from pydantic import BaseModel, Field


class QARequest(BaseModel):
    url: str = Field(..., description="Website URL to test")
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context for QA flow (credentials, test notes, etc.)",
    )
    device_profile: str = Field(default="iphone_14")
    network_profile: str = Field(default="wifi")


class QAResponse(BaseModel):
    url: str
    issues: list[dict[str, Any]]
    tool_outputs: list[dict[str, Any]]
    screenshots: list[str]
    raw_model_output: str | None
    trace: list[dict[str, Any]]
