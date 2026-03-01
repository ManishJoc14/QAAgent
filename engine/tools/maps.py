from engine.tools.console import ConsoleWatcherTool, NetworkMonitorTool

# Import all your tools
from engine.tools.functional import (
    ButtonClickCheckerTool,
    DeadLinkCheckerTool,
    FormValidatorTool,
    LoginFlowCheckerTool,
    SessionPersistenceCheckerTool,
)
from engine.tools.metadata import SEOMetadataCheckerTool
from engine.tools.performance import PerformanceAuditTool
from engine.tools.security import (
    SecurityContentAuditTool,
    SecurityHeadersAuditTool,
    SSLAuditTool,
)
from engine.tools.uiux import (
    AccessibilityAuditTool,
    ResponsiveLayoutCheckerTool,
    TouchTargetCheckerTool,
)

# Map string keys to tool classes
AVAILABLE_QA_TOOLS: dict[str, type] = {
    "dead_link_checker": DeadLinkCheckerTool,
    "form_validator": FormValidatorTool,
    "button_click_checker": ButtonClickCheckerTool,
    "login_flow_checker": LoginFlowCheckerTool,
    "session_persistence_checker": SessionPersistenceCheckerTool,
    "accessibility_audit": AccessibilityAuditTool,
    "responsive_layout_checker": ResponsiveLayoutCheckerTool,
    "touch_target_checker": TouchTargetCheckerTool,
    "network_monitor": NetworkMonitorTool,
    "console_watcher": ConsoleWatcherTool,
    "seo_metadata_checker": SEOMetadataCheckerTool,
    "performance_audit": PerformanceAuditTool,
    "ssl_audit": SSLAuditTool,
    "security_headers_audit": SecurityHeadersAuditTool,
    "security_content_audit": SecurityContentAuditTool,
}
