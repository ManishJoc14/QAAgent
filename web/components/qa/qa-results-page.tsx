"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Download, ArrowRight, CheckCircle2, CircleX } from "lucide-react";
import { SiteFooter } from "@/components/public/site-footer";
import { IssueTable } from "@/components/issues/issue-table";
import MarkdownRenderer from "@/components/markdown/markdown-renderer";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { createMockReport } from "@/lib/mock-data";
import { ScanReport, TraceToolResult } from "@/types/scan";

function tone(score: number) {
  if (score >= 80) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 60) return "text-amber-600 dark:text-amber-400";
  return "text-rose-600 dark:text-rose-400";
}

function summarizeStep(step: ScanReport["trace"][number]) {
  if (step.toolCalls.length === 0) return "No tool used";
  const names = step.toolCalls.map((call) => call.name).join(", ");
  return names;
}

function getToolResults(step: ScanReport["trace"][number]): TraceToolResult[] {
  if (Array.isArray(step.toolResults)) return step.toolResults;
  const hasLegacyOutput = step.output || step.outputJson || step.error || Object.keys(step.metadata ?? {}).length > 0 || step.screenshotUrl;
  if (!hasLegacyOutput) return [];
  return [
    {
      toolCallId: `legacy-step-${step.step}-result-1`,
      toolName: step.toolCalls?.[0]?.name ?? "step_output",
      success: step.status !== "failed",
      output: step.output ?? null,
      outputJson: step.outputJson ?? null,
      error: step.error ?? null,
      metadata: step.metadata ?? {},
      screenshotUrl: step.screenshotUrl
    }
  ];
}

function toolLabel(name: string) {
  return name
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function compactArgs(args: Record<string, unknown>) {
  const preferred = ["url", "max_links", "max_forms", "overflow_risk_width_px", "min_size_px", "slow_threshold_ms", "limit", "level_filter"];
  return preferred
    .filter((key) => key in args)
    .map((key) => `${key}: ${String(args[key])}`)
    .slice(0, 4);
}

function buildToolSummary(toolName: string, result: TraceToolResult) {
  const json = result.outputJson ?? {};
  const lines: string[] = [];
  if (toolName === "dead_link_checker") {
    lines.push(
      `Checked ${Number(json.total_links_checked ?? 0)} links (${Number(json.internal_links_checked ?? 0)} internal, ${Number(json.external_links_checked ?? 0)} external).`,
      `Dead links found: ${Array.isArray(json.dead_links) ? json.dead_links.length : 0}.`
    );
  } else if (toolName === "form_validator") {
    lines.push(
      `Forms detected: ${Number(json.form_count ?? 0)}.`,
      `Unlabeled controls: ${Number(json.unlabeled_control_count ?? 0)}.`,
      `Forms without submit button: ${Number(json.forms_without_submit_count ?? 0)}.`
    );
  } else if (toolName === "button_click_checker") {
    lines.push(
      `Anchors: ${Number(json.anchor_count ?? 0)}, buttons: ${Number(json.button_count ?? 0)}.`,
      `Broken anchors: ${Array.isArray(json.broken_anchors) ? json.broken_anchors.length : 0}.`
    );
  } else if (toolName === "accessibility_audit") {
    lines.push(
      `Missing alt text: ${Number(json.missing_alt_count ?? 0)}.`,
      `Unlabeled controls: ${Number(json.unlabeled_control_count ?? 0)}.`,
      `Invalid ARIA roles: ${Number(json.invalid_aria_role_count ?? 0)}.`
    );
  } else if (toolName === "responsive_layout_checker") {
    lines.push(`Viewport meta tag: ${json.viewport_meta_found ? "present" : "missing"}.`, `Large fixed-width elements: ${Number(json.large_fixed_width_count ?? 0)}.`);
  } else if (toolName === "touch_target_checker") {
    lines.push(`Clickable elements measured: ${Number(json.clickable_count ?? 0)}.`, `Undersized targets: ${Number(json.small_target_count ?? 0)}.`);
  } else if (toolName === "network_monitor") {
    lines.push(`Resources scanned: ${Number(json.resource_count ?? 0)}.`, `Failed requests: ${Array.isArray(json.failed_requests) ? json.failed_requests.length : 0}.`);
  } else if (toolName === "console_watcher") {
    lines.push(`Console events: ${Number(json.total_console_events ?? 0)}.`, `Errors: ${Number(json.error_count ?? 0)}, warnings: ${Number(json.warning_count ?? 0)}.`);
  }
  const findings = Array.isArray(json.findings) ? json.findings.filter((item): item is string => typeof item === "string") : [];
  return { lines, findings };
}

function buildReadableReportContent(report: ScanReport) {
  const content = report.rawModelOutput?.trim();
  if (!content) return "No report narrative returned by the agent.";

  const jsonFence = content.match(/```json\s*([\s\S]*?)```/i);
  if (!jsonFence?.[1]) return content;

  try {
    const parsed = JSON.parse(jsonFence[1]) as {
      summary?: string;
      issues?: Array<{ severity?: string; title?: string; description?: string }>;
    };
    const summary = typeof parsed.summary === "string" ? parsed.summary.trim() : "";
    const issues = Array.isArray(parsed.issues) ? parsed.issues : [];
    const issueLines = issues
      .map((issue, index) => {
        const severity = typeof issue.severity === "string" ? issue.severity : "Unknown";
        const title = typeof issue.title === "string" ? issue.title : "Untitled issue";
        const description = typeof issue.description === "string" ? issue.description : "";
        return `${index + 1}. **${severity}** - **${title}**${description ? `: ${description}` : ""}`;
      })
      .join("\n");

    const parts = ["### Final Report"];
    if (summary) parts.push(`\n${summary}`);
    if (issueLines) parts.push(`\n### Key Issues\n${issueLines}`);
    return parts.join("\n");
  } catch {
    return content;
  }
}

export function QAResultsPage() {
  const searchParams = useSearchParams();
  const [history] = useLocalStorage<ScanReport[]>("qa-agent-history", []);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  const report = useMemo(() => {
    if (!isHydrated) return null;

    const scanIdFromQuery = searchParams.get("scanId");
    const latestFromStorage = typeof window !== "undefined" ? window.localStorage.getItem("qa-agent-latest-report-id") : null;
    const preferredId = scanIdFromQuery ?? latestFromStorage;

    if (history.length === 0) {
      return createMockReport({
        targetUrl: "https://example.com",
        deviceProfile: "desktop",
        networkProfile: "wifi"
      });
    }

    if (!preferredId) return history[0];
    return history.find((item) => item.id === preferredId) ?? history[0];
  }, [history, searchParams, isHydrated]);

  const readableReportContent = useMemo(() => (report ? buildReadableReportContent(report) : ""), [report]);

  const downloadJson = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${report.id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (!report) {
    return (
      <div className="min-h-screen bg-[var(--surface-bg)] text-[var(--surface-fg)]">
        <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-8">
          <Link href="/" className="text-xl font-semibold tracking-tight">
            QA agent
          </Link>
        </header>
        <main className="mx-auto w-full max-w-6xl px-6 pb-20">
          <section className="rounded-2xl border border-[var(--surface-border)] bg-[var(--surface-card)] p-6">
            <p className="text-sm text-slate-700">Loading latest scan report...</p>
          </section>
        </main>
        <SiteFooter />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--surface-bg)] text-[var(--surface-fg)]">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-8">
        <Link href="/" className="text-xl font-semibold tracking-tight">
          QA agent
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/#about" className="text-[var(--surface-muted)] transition hover:text-[var(--surface-fg)]">
            about
          </Link>
          <Link href="/qa" className="font-medium text-[var(--surface-fg)]">
            try now
          </Link>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-6xl space-y-8 px-6 pb-20">
        <section className="rounded-2xl border border-[var(--surface-border)] bg-[var(--surface-card)] p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--surface-muted)]">Overview</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">{report.targetUrl}</h1>
              <p className="mt-1 text-xs text-[var(--surface-muted)]">{report.id}</p>
            </div>
            <button
              type="button"
              onClick={downloadJson}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[var(--surface-border)] px-4 py-2 text-sm font-medium transition hover:bg-slate-50 dark:hover:bg-slate-900"
            >
              <Download className="h-4 w-4" />
              Download JSON
            </button>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-[var(--surface-border)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--surface-muted)]">Risk Score</p>
              <p className={`mt-2 text-3xl font-semibold ${tone(report.riskScore)}`}>{report.riskScore}</p>
            </div>
            <div className="rounded-xl border border-[var(--surface-border)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--surface-muted)]">Performance Score</p>
              <p className={`mt-2 text-3xl font-semibold ${tone(report.performanceScore)}`}>{report.performanceScore}</p>
            </div>
            <div className="rounded-xl border border-[var(--surface-border)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--surface-muted)]">Total Findings</p>
              <p className="mt-2 text-3xl font-semibold">{report.issues.length}</p>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-[var(--surface-border)] bg-[var(--surface-card)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Issues</h2>
          <div className="mt-4">
            <IssueTable issues={report.issues} />
          </div>
        </section>

        <section className="rounded-2xl border border-[var(--surface-border)] bg-[var(--surface-card)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Report</h2>
          <p className="mt-1 text-sm text-[var(--surface-muted)]">Human-readable summary from the agent output.</p>
          <div className="mt-4 rounded-xl border border-[var(--surface-border)] bg-slate-50/40 dark:bg-slate-900/40 py-2">
            <MarkdownRenderer content={readableReportContent} className="max-w-none px-4" />
          </div>
        </section>

        <section className="rounded-2xl border border-[var(--surface-border)] bg-[var(--surface-card)] p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">How The Scan Ran</h2>
            <Link href="/qa" className="inline-flex items-center gap-1 text-sm font-medium text-[var(--surface-muted)] hover:text-[var(--surface-fg)]">
              Run another scan <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <p className="mt-1 text-base text-slate-700">Step-by-step execution with tool usage and outcomes.</p>

          <div className="mt-6 space-y-3">
            {report.trace.map((step) => (
              <article key={step.id} className="rounded-xl border border-[var(--surface-border)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold">Step {step.step}</p>
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                      step.status === "failed"
                        ? "bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
                        : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                    }`}
                  >
                    {step.status}
                  </span>
                </div>

                <div className="mt-3">
                  <p className="text-sm font-semibold uppercase tracking-wide text-slate-700">Tools</p>
                  <p className="mt-1 text-base text-slate-800">{summarizeStep(step)}</p>
                </div>

                <div className="mt-3">
                  <p className="text-sm font-semibold uppercase tracking-wide text-slate-700">Tool Calls</p>
                  {step.toolCalls.length === 0 && (
                    <p className="mt-1 text-base text-slate-700">No tool calls were made in this step.</p>
                  )}
                  {step.toolCalls.length > 0 && (
                    <div className="mt-2 space-y-3">
                      {step.toolCalls.map((call, callIdx) => {
                        const result = getToolResults(step)[callIdx];
                        const args = compactArgs(call.arguments ?? {});
                        const summary = result ? buildToolSummary(call.name, result) : { lines: [], findings: [] as string[] };
                        return (
                          <details key={call.id} className="rounded-xl border border-[var(--surface-border)] p-3">
                            <summary className="cursor-pointer list-none">
                              <div className="flex items-center justify-between gap-3">
                                <div className="flex items-center gap-2">
                                  {result?.success ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <CircleX className="h-4 w-4 text-rose-600" />}
                                  <p className="text-base font-semibold text-slate-900">{toolLabel(call.name)}</p>
                                </div>
                                <span className={`rounded-full px-2 py-0.5 text-xs ${result?.success ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                                  {result?.success ? "Success" : "Failed"}
                                </span>
                              </div>
                            </summary>

                            <div className="mt-3">
                              {args.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                  {args.map((arg) => (
                                    <span key={`${call.id}-${arg}`} className="rounded-full bg-slate-100 px-2 py-0.5 text-sm text-slate-700">
                                      {arg}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {!result && <p className="mt-2 text-base text-slate-700">No tool output mapped for this call.</p>}
                              {result && (
                                <div className="mt-2 space-y-2">
                                  {summary.lines.length > 0 && (
                                    <ul className="list-disc space-y-1 pl-5 text-base text-slate-800">
                                      {summary.lines.map((line, idx) => (
                                        <li key={`${call.id}-line-${idx}`}>{line}</li>
                                      ))}
                                    </ul>
                                  )}

                                  {summary.findings.length > 0 && (
                                    <div>
                                      <p className="text-sm font-semibold uppercase tracking-wide text-slate-700">Findings</p>
                                      <ul className="mt-1 list-disc space-y-1 pl-5 text-base text-slate-800">
                                        {summary.findings.map((finding, idx) => (
                                          <li key={`${call.id}-finding-${idx}`}>{finding}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}

                                  {result.error && <div className="rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-sm text-rose-700">{result.error}</div>}

                                  {!result.outputJson && result.output && (
                                    <details className="rounded-md border border-[var(--surface-border)] p-2">
                                      <summary className="cursor-pointer text-sm font-medium text-slate-700">Raw Output</summary>
                                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-all text-sm text-slate-700">{result.output}</pre>
                                    </details>
                                  )}

                                  {result.screenshotUrl && (
                                    <div>
                                      <p className="text-sm font-medium text-slate-700">Screenshot</p>
                                      <Image
                                        src={result.screenshotUrl}
                                        alt={`${call.name} screenshot`}
                                        width={1200}
                                        height={700}
                                        className="mt-1 h-auto w-full rounded-md border border-[var(--surface-border)]"
                                      />
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </details>
                        )})}
                    </div>
                  )}
                </div>

                <div className="mt-3">
                  <p className="text-sm font-semibold uppercase tracking-wide text-slate-700">Agent Notes</p>
                  <div className="mt-1 rounded-lg border border-[var(--surface-border)] bg-slate-50/40 dark:bg-slate-900/40 py-1">
                    <MarkdownRenderer
                      content={step.assistantContent || "No assistant commentary returned for this step."}
                      className="max-w-none px-3"
                    />
                  </div>
                </div>

                {step.toolCalls.length === 0 && getToolResults(step).length > 0 && (
                  <details className="mt-3 rounded-lg border border-[var(--surface-border)] p-3">
                    <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-[var(--surface-muted)]">
                      Step Outputs
                    </summary>
                    <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-all text-xs text-slate-700 dark:text-slate-300">
                      {JSON.stringify(getToolResults(step), null, 2)}
                    </pre>
                  </details>
                )}
              </article>
            ))}
          </div>

          <details className="mt-5 rounded-xl border border-[var(--surface-border)] p-4">
            <summary className="cursor-pointer text-sm font-medium text-[var(--surface-muted)]">Show raw technical trace</summary>
            <div className="mt-4 rounded-xl border border-[var(--surface-border)] p-3 font-mono text-xs break-all whitespace-pre-wrap">
              {JSON.stringify(report.trace, null, 2)}
            </div>
          </details>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
