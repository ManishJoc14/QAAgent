export type RunStatus = "Idle" | "Scanning" | "Analyzing" | "Completed" | "Failed";

export type Severity = "P1" | "P2" | "P3" | "Unknown";

export const DeviceProfile = {
  IPHONE_SE: "iphone_se",
  IPHONE_14: "iphone_14",
  PIXEL_7: "pixel_7",
  GALAXY_S23: "galaxy_s23",
  DESKTOP: "desktop",
  DESKTOP_1440: "desktop_1440"
} as const;

export type DeviceProfile = typeof DeviceProfile[keyof typeof DeviceProfile];

export const NetworkProfile = {
  WIFI: "wifi",
  FOUR_G: "4g",
  FAST_3G: "fast_3g",
  SLOW_3G: "slow_3g",
  HIGH_LATENCY: "high_latency",
  OFFLINE: "offline"
} as const;

export type NetworkProfile = typeof NetworkProfile[keyof typeof NetworkProfile];

export const QAToolName = {
  DEAD_LINK_CHECKER: "dead_link_checker",
  FORM_VALIDATOR: "form_validator",
  BUTTON_CLICK_CHECKER: "button_click_checker",
  LOGIN_FLOW_CHECKER: "login_flow_checker",
  SESSION_PERSISTENCE_CHECKER: "session_persistence_checker",
  ACCESSIBILITY_AUDIT: "accessibility_audit",
  RESPONSIVE_LAYOUT_CHECKER: "responsive_layout_checker",
  TOUCH_TARGET_CHECKER: "touch_target_checker",
  NETWORK_MONITOR: "network_monitor",
  CONSOLE_WATCHER: "console_watcher",
  SEO_METADATA_CHECKER: "seo_metadata_checker",
  PERFORMANCE_AUDIT: "performance_audit",
  SSL_AUDIT: "ssl_audit",
  SECURITY_HEADERS_AUDIT: "security_headers_audit",
  SECURITY_CONTENT_AUDIT: "security_content_audit"
} as const;

export type QAToolName = typeof QAToolName[keyof typeof QAToolName];

export interface ScanIssue {
  id: string;
  severity: Severity;
  title: string;
  category: string;
  description: string;
  stepsToReproduce: string[];
  severityJustification: string;
}

export interface PerfMetric {
  key: "FCP" | "DOM" | "TTFB" | "Resources";
  value: number;
  unit: "ms" | "count";
  target: number;
}

export interface SecurityFinding {
  header: string;
  missing: boolean;
  severity: Severity;
}

export interface CookieFinding {
  name: string;
  issue: string;
  severity: Severity;
}

export interface ScreenshotItem {
  id: string;
  label: string;
  url: string;
  failed?: boolean;
}

export interface TraceStep {
  id: string;
  step: number;
  status: "success" | "failed";
  assistantContent: string;
  toolCalls: BackendTraceToolCall[];
  toolResults: TraceToolResult[];
  output: string | null;
  outputJson: Record<string, unknown> | null;
  error: string | null;
  metadata: Record<string, unknown>;
  screenshotUrl?: string;
}

export interface TraceToolResult {
  toolCallId: string;
  toolName: string;
  success: boolean;
  output: string | null;
  outputJson: Record<string, unknown> | null;
  error: string | null;
  metadata: Record<string, unknown>;
  screenshotUrl?: string;
}

export interface ScanReport {
  id: string;
  targetUrl: string;
  httpStatus: number | null;
  riskScore: number;
  performanceScore: number;
  runStatus: RunStatus;
  startedAt?: string;
  completedAt?: string;
  severity: { p1: number; p2: number; p3: number; unknown: number };
  issues: ScanIssue[];
  performance: PerfMetric[];
  security: SecurityFinding[];
  cookies: CookieFinding[];
  screenshots: ScreenshotItem[];
  trace: TraceStep[];
  toolOutputs: BackendToolOutput[];
  rawModelOutput: string;
  rawJson: Record<string, unknown>;
  logs: string[];
}

export interface ScanPayload {
  targetUrl: string;
  deviceProfile: DeviceProfile;
  networkProfile: NetworkProfile;
  selectedTools?: QAToolName[];
  contextJson?: string;
}

export interface BackendToolOutput {
  success: boolean;
  output: string | null;
  error: string | null;
  screenshot_base64: string | null;
  metadata: Record<string, unknown>;
}

export interface BackendTraceToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface BackendTraceStep {
  step: number;
  assistant_content: string;
  tool_calls: BackendTraceToolCall[];
}

export interface BackendScanResponse {
  url: string;
  issues: Array<Record<string, unknown>>;
  tool_outputs: BackendToolOutput[];
  screenshots: string[];
  raw_model_output: string;
  trace: BackendTraceStep[];
}
