from .base import BaseTool, ToolExecutionResult
from .bash import BashTool
from .collection import ToolCollection
from .functional import (
    ButtonClickCheckerTool,
    DeadLinkCheckerTool,
    FormValidatorTool,
    LoginFlowCheckerTool,
    SessionPersistenceCheckerTool,
)
from .console import NetworkTabAnalyzerTool
from .uiux import AccessibilityAuditTool, ResponsiveLayoutCheckerTool, TouchTargetCheckerTool

try:
    from .audit_tools import (
        ConsoleNetworkAuditTool,
        PageAuditTool,
        PerformanceAuditTool,
        SecurityHeadersAuditTool,
    )
    from .playwright import PlaywrightComputerTool
except ModuleNotFoundError:
    PlaywrightComputerTool = None  # type: ignore[assignment]
    PageAuditTool = None  # type: ignore[assignment]
    ConsoleNetworkAuditTool = None  # type: ignore[assignment]
    PerformanceAuditTool = None  # type: ignore[assignment]
    SecurityHeadersAuditTool = None  # type: ignore[assignment]

__all__ = [
    "BaseTool",
    "ToolExecutionResult",
    "ToolCollection",
    "DeadLinkCheckerTool",
    "FormValidatorTool",
    "ButtonClickCheckerTool",
    "LoginFlowCheckerTool",
    "SessionPersistenceCheckerTool",
    "NetworkTabAnalyzerTool",
    "AccessibilityAuditTool",
    "ResponsiveLayoutCheckerTool",
    "TouchTargetCheckerTool",
    "PlaywrightComputerTool",
    "BashTool",
    "PageAuditTool",
    "ConsoleNetworkAuditTool",
    "PerformanceAuditTool",
    "SecurityHeadersAuditTool",
]
