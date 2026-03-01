import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-[var(--surface-border)] py-4">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-6 text-sm text-[var(--surface-muted)] md:flex-row md:items-center md:justify-between">
        <p>QA Agent</p>
        <div className="flex items-center gap-4">
          <Link className="transition hover:text-[var(--surface-fg)]" href="/about">
            About
          </Link>
          <Link className="transition hover:text-[var(--surface-fg)]" href="/qa">
            Try Now
          </Link>
        </div>
      </div>
    </footer>
  );
}
