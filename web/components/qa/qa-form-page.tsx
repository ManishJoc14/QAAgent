"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { useRunScan } from "@/hooks/use-run-scan";
import { DeviceProfile, NetworkProfile, QAToolName, ScanPayload, ScanReport } from "@/types/scan";

const deviceOptions = [
  { value: DeviceProfile.IPHONE_SE, label: "iPhone SE" },
  { value: DeviceProfile.IPHONE_14, label: "iPhone 14" },
  { value: DeviceProfile.PIXEL_7, label: "Pixel 7" },
  { value: DeviceProfile.GALAXY_S23, label: "Galaxy S23" },
  { value: DeviceProfile.DESKTOP, label: "Desktop 1280x800" },
  { value: DeviceProfile.DESKTOP_1440, label: "Desktop 1440x900" }
] as const;

const networkOptions = [
  { value: NetworkProfile.WIFI, label: "Wi-Fi" },
  { value: NetworkProfile.FOUR_G, label: "4G" },
  { value: NetworkProfile.FAST_3G, label: "Fast 3G" },
  { value: NetworkProfile.SLOW_3G, label: "Slow 3G" },
  { value: NetworkProfile.HIGH_LATENCY, label: "High Latency" },
  { value: NetworkProfile.OFFLINE, label: "Offline" }
] as const;

const tools = Object.values(QAToolName);

const toolLabelMap: Record<string, string> = {
  dead_link_checker: "Dead Link Checker",
  form_validator: "Form Validator",
  button_click_checker: "Button Click Checker",
  login_flow_checker: "Login Flow Checker",
  session_persistence_checker: "Session Persistence Checker",
  accessibility_audit: "Accessibility Audit",
  responsive_layout_checker: "Responsive Layout Checker",
  touch_target_checker: "Touch Target Checker",
  network_monitor: "Network Monitor",
  console_watcher: "Console Watcher",
  seo_metadata_checker: "SEO Metadata Checker",
  performance_audit: "Performance Audit",
  ssl_audit: "SSL Audit",
  security_headers_audit: "Security Headers Audit",
  security_content_audit: "Security Content Audit"
};

export function QAFormPage() {
  const router = useRouter();
  const [history, setHistory] = useLocalStorage<ScanReport[]>("qa-agent-history", []);
  const [targetUrl, setTargetUrl] = useState("https://example.com");
  const [deviceProfile, setDeviceProfile] = useState<ScanPayload["deviceProfile"]>(DeviceProfile.DESKTOP);
  const [networkProfile, setNetworkProfile] = useState<ScanPayload["networkProfile"]>(NetworkProfile.WIFI);
  const [selectedTools, setSelectedTools] = useState<ScanPayload["selectedTools"]>(tools);
  const [contextJson, setContextJson] = useState('{"mission":"autonomous_scan"}');

  const mutation = useRunScan((report) => {
    const updated = [report, ...history].slice(0, 25);
    setHistory(updated);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("qa-agent-latest-report-id", report.id);
    }
    toast.success("Scan completed");
    router.push(`/qa/results?scanId=${encodeURIComponent(report.id)}`);
  });

  const selectedCount = useMemo(() => selectedTools?.length ?? 0, [selectedTools]);

  const toggleTool = (name: (typeof tools)[number]) => {
    setSelectedTools((prev) => {
      const current = prev ?? [];
      if (current.includes(name)) return current.filter((item) => item !== name);
      return [...current, name];
    });
  };

  const executeScan = () => {
    const payload: ScanPayload = {
      targetUrl,
      deviceProfile,
      networkProfile,
      selectedTools,
      contextJson
    };
    mutation.mutate(payload, {
      onError: (error) => {
        toast.error("Scan failed", { description: error.message });
      }
    });
  };

  return (
    <>
      <main className="mx-auto w-full max-w-6xl px-6 pb-20 pt-6 md:pt-10">
        <section className="mx-auto max-w-4xl rounded-2xl border border-surface-border bg-surface-card p-6 shadow-sm sm:p-8">
          <h1 className="text-3xl font-semibold tracking-tight">Autonomous Scan</h1>
          <p className="mt-2 text-sm text-surface-muted">Run an end-to-end QA mission and generate a full report.</p>

          <div className="mt-8 space-y-6">
            <div>
              <label htmlFor="targetUrl" className="mb-2 block text-sm font-medium">
                Target URL
              </label>
              <input
                id="targetUrl"
                value={targetUrl}
                onChange={(event) => setTargetUrl(event.target.value)}
                className="h-12 w-full rounded-xl border border-surface-border bg-transparent px-4 text-base outline-none ring-0 transition focus:border-slate-900 dark:focus:border-slate-200"
              />
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label htmlFor="deviceProfile" className="mb-2 block text-sm font-medium">
                  Device Profile
                </label>
                <select
                  id="deviceProfile"
                  value={deviceProfile}
                  onChange={(event) => setDeviceProfile(event.target.value as ScanPayload["deviceProfile"])}
                  className="h-12 w-full rounded-xl border border-surface-border bg-transparent px-4 text-sm outline-none transition focus:border-slate-900 dark:focus:border-slate-200"
                >
                  {deviceOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="networkProfile" className="mb-2 block text-sm font-medium">
                  Network Profile
                </label>
                <select
                  id="networkProfile"
                  value={networkProfile}
                  onChange={(event) => setNetworkProfile(event.target.value as ScanPayload["networkProfile"])}
                  className="h-12 w-full rounded-xl border border-surface-border bg-transparent px-4 text-sm outline-none transition focus:border-slate-900 dark:focus:border-slate-200"
                >
                  {networkOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-medium">Tools</label>
                <span className="text-xs text-surface-muted">{selectedCount} selected</span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
                {tools.map((tool) => {
                  const checked = (selectedTools ?? []).includes(tool);
                  return (
                    <label
                      key={tool}
                      className="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl border border-surface-border px-3 py-2 text-sm capitalize transition hover:border-slate-400 dark:hover:border-slate-500"
                    >
                      <input type="checkbox" checked={checked} onChange={() => toggleTool(tool)} className="h-4 w-4" />
                      <span>{toolLabelMap[tool] ?? tool.replaceAll("_", " ")}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div>
              <label htmlFor="contextJson" className="mb-2 block text-sm font-medium">
                Context
              </label>
              <textarea
                id="contextJson"
                value={contextJson}
                onChange={(event) => setContextJson(event.target.value)}
                className="h-36 w-full rounded-xl border border-surface-border bg-transparent p-4 font-mono text-xs outline-none transition focus:border-slate-900 dark:focus:border-slate-200"
              />
            </div>

            <button
              type="button"
              disabled={mutation.isPending}
              onClick={executeScan}
              className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-surface-accent px-6 py-3 text-sm font-medium text-surface-accent-fg transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-65"
            >
              {mutation.isPending ? "Running autonomous scan..." : "Try now"}
              {!mutation.isPending && <ArrowRight className="h-4 w-4" />}
            </button>
          </div>
        </section>
      </main>
    </>
  );
}
