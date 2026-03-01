from typing import Any, Literal

from pydantic import BaseModel, Field

ToolKey = Literal[
    "dead_link_checker",
    "form_validator",
    "button_click_checker",
    "login_flow_checker",
    "session_persistence_checker",
    "accessibility_audit",
    "responsive_layout_checker",
    "touch_target_checker",
    "network_monitor",
    "console_watcher",
    "seo_metadata_checker",
    "performance_audit",
    "ssl_audit",
    "security_headers_audit",
    "security_content_audit",
]

# Allowed devices
DeviceProfile = Literal[
    "iphone_se",
    "iphone_14",
    "pixel_7",
    "galaxy_s23",
    "desktop",
    "desktop_1440",
]

# Allowed network profiles
NetworkProfile = Literal[
    "wifi",
    "4g",
    "fast_3g",
    "slow_3g",
    "high_latency",
    "offline",
]


class QARequest(BaseModel):
    url: str = Field(..., description="Website URL to test")
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context for QA flow (credentials, test notes, etc.)",
    )
    device_profile: DeviceProfile = Field(
        default="iphone_14",
        description="Select device profile for testing",
    )
    network_profile: NetworkProfile = Field(
        default="wifi",
        description="Select network speed / conditions for testing",
    )
    selected_tools: list[ToolKey] = Field(
        default_factory=list,
        description="List of tool keys to run, multiple-choice from available QA tools",
    )


class QAResponse(BaseModel):
    url: str
    issues: list[dict[str, Any]]
    tool_outputs: list[dict[str, Any]]
    screenshots: list[str]
    raw_model_output: str | None
    trace: list[dict[str, Any]]
