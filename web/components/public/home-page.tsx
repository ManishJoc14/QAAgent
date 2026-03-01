import Link from "next/link";
import { Cormorant_Garamond } from "next/font/google";
import { ArrowRight } from "lucide-react";
import { SiteFooter } from "@/components/public/site-footer";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600", "700"]
});

export function HomePage() {
  return (
    <div className="min-h-screen bg-[var(--surface-bg)] text-[var(--surface-fg)]">
      <header className="mx-auto flex w-full max-w-[1280px] items-center justify-between px-6 py-7 lg:px-10">
        <Link href="/" className="text-2xl font-bold tracking-tight text-blue-700 dark:text-blue-400">
          QA<span className="text-[var(--surface-fg)]"> agent</span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-[var(--surface-fg)] md:flex">
          <Link href="/about" className="transition hover:opacity-70">
            About
          </Link>
          <Link
            href="/qa"
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border-2 border-[var(--surface-fg)] px-7 py-2 text-base font-medium transition hover:-translate-y-0.5"
          >
            Try now <ArrowRight className="h-5 w-5" />
          </Link>
        </nav>
      </header>

      <main className="mx-auto flex w-full max-w-[1280px] flex-col items-center px-6 pb-24 pt-8 text-center lg:px-10">
        <div className="relative w-full max-w-5xl">
          <h1 className={`${cormorant.className} mx-auto max-w-5xl text-balance text-[54px] leading-[0.95] tracking-tight sm:text-[72px] lg:text-[88px]`}>
          Your QA Agent that actually works
          </h1>
        </div>

        <p
          id="about"
          className="mt-8 max-w-3xl text-balance text-xl leading-tight text-[var(--surface-fg)]/90 sm:text-[30px]"
        >
          Autonomous QA scans across devices, networks, and key user flows.
          <br />
          Prioritized issues with reproducible evidence.
        </p>
        <Link
          href="/qa"
          className="mt-10 inline-flex min-h-11 items-center gap-2 rounded-xl bg-black px-7 py-3 text-lg font-medium text-white transition hover:-translate-y-0.5 dark:bg-white dark:text-black"
        >
          Try now <ArrowRight className="h-5 w-5" />
        </Link>
      </main>

      <SiteFooter />
    </div>
  );
}
