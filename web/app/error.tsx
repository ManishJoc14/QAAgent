"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type ErrorWithDigest = Error & { digest?: string };

export default function Error({ error, reset }: { error: ErrorWithDigest; reset: () => void }) {
  return (
    <main className="min-h-screen bg-[var(--surface-bg)] px-6 py-16 text-[var(--surface-fg)]">
      <div className="mx-auto w-full max-w-2xl">
        <Card className="space-y-6 border border-[var(--surface-border)] bg-[var(--surface-card)] p-8 shadow-none backdrop-blur-0">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-rose-600">System Error</p>
            <h1 className="text-2xl font-semibold tracking-tight">QA Agent Error</h1>
            <p className="text-sm text-[var(--surface-muted)]">
              The dashboard hit an unexpected state while rendering this page. You can safely retry, start a new scan,
              or return to home.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <Button onClick={reset} className="w-full">
              Retry
            </Button>
            <Link href="/qa" className="w-full">
              <Button variant="ghost" className="w-full border border-[var(--surface-border)] bg-transparent text-[var(--surface-fg)] hover:bg-slate-50">
                New Scan
              </Button>
            </Link>
            <Link href="/" className="w-full">
              <Button variant="ghost" className="w-full border border-[var(--surface-border)] bg-transparent text-[var(--surface-fg)] hover:bg-slate-50">
                Go Home
              </Button>
            </Link>
          </div>

          <details className="rounded-xl border border-[var(--surface-border)] p-4">
            <summary className="cursor-pointer text-sm font-medium text-[var(--surface-muted)]">Technical details</summary>
            <div className="mt-3 space-y-2 text-xs">
              <p className="font-semibold uppercase tracking-wide text-[var(--surface-muted)]">Message</p>
              <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-lg border border-[var(--surface-border)] bg-slate-50 p-3 text-slate-700">
                {error?.message || "Unknown error"}
              </pre>
              {error?.digest && (
                <>
                  <p className="font-semibold uppercase tracking-wide text-[var(--surface-muted)]">Digest</p>
                  <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-lg border border-[var(--surface-border)] bg-slate-50 p-3 text-slate-700">
                    {error.digest}
                  </pre>
                </>
              )}
            </div>
          </details>
        </Card>
      </div>
    </main>
  );
}
