import Link from "next/link";
import { Cormorant_Garamond } from "next/font/google";
import { ArrowRight, Wrench, Smartphone, FileText } from "lucide-react";
import { SiteFooter } from "@/components/public/site-footer";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600", "700"]
});

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-[var(--surface-bg)] text-[var(--surface-fg)]">
      <header className="mx-auto flex w-full max-w-[1280px] items-center justify-between px-6 py-7 lg:px-10">
        <Link href="/" className="text-2xl font-bold tracking-tight text-blue-700 dark:text-blue-400">
          QA<span className="text-[var(--surface-fg)]"> agent</span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-[var(--surface-fg)] md:flex">
          <Link href="/about" className="font-bold text-blue-700 dark:text-blue-400">
            About
          </Link>
          <Link
            href="/qa"
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border-2 border-current px-7 py-2 text-base font-medium transition hover:-translate-y-0.5"
          >
            Try now <ArrowRight className="h-5 w-5" />
          </Link>
        </nav>
      </header>

      <main className="mx-auto flex w-full max-w-[1280px] flex-col items-center px-6 pb-10 pt-8 text-center lg:px-10">
        <section className="w-full max-w-5xl text-center">
          <h2 className={`${cormorant.className} text-4xl font-bold tracking-tight sm:text-5xl`}>How It Works</h2>
          <p className="mt-4 text-lg text-[var(--surface-fg)]/80">A simple, three-step process to automate your QA.</p>
          <div className="mt-16 grid gap-12 md:grid-cols-3">
            <div className="flex flex-col items-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-blue-700 bg-blue-50 text-2xl font-bold text-blue-700 dark:border-blue-400 dark:bg-transparent dark:text-blue-400">
                1
              </div>
              <h3 className="mt-6 text-xl font-semibold">Configure Scan</h3>
              <p className="mt-2 text-[var(--surface-muted)]">Start by providing the target URL and selecting device and network profiles.</p>
            </div>
            <div className="flex flex-col items-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-blue-700 bg-blue-50 text-2xl font-bold text-blue-700 dark:border-blue-400 dark:bg-transparent dark:text-blue-400">
                2
              </div>
              <h3 className="mt-6 text-xl font-semibold">Build Your Mission</h3>
              <p className="mt-2 text-[var(--surface-muted)]">Choose from a comprehensive list of QA tools to tailor the scan to your needs.</p>
            </div>
            <div className="flex flex-col items-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-blue-700 bg-blue-50 text-2xl font-bold text-blue-700 dark:border-blue-400 dark:bg-transparent dark:text-blue-400">
                3
              </div>
              <h3 className="mt-6 text-xl font-semibold">Launch & Analyze</h3>
              <p className="mt-2 text-[var(--surface-muted)]">Execute the scan and receive a detailed report with actionable insights.</p>
            </div>
          </div>
        </section>

        <Link
          href="/qa"
          className="mt-16 inline-flex min-h-11 items-center gap-2 rounded-xl bg-black px-7 py-3 text-lg font-medium text-white transition hover:-translate-y-0.5 dark:bg-white dark:text-black"
        >
          Start a scan <ArrowRight className="h-5 w-5" />
        </Link>
      </main>

      <SiteFooter />
    </div>
  );
}
