import Link from "next/link";
import { Cormorant_Garamond } from "next/font/google";
import { ArrowRight } from "lucide-react";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600", "700"]
});

export function HomePage() {
  return (
    <>
      {/* Magenta Orb Grid Background */}
      <div
        className="absolute inset-0 z-0"
        style={{
          background: "white",
          backgroundImage: `
            linear-gradient(to right, rgba(71,85,105,0.15) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(71,85,105,0.15) 1px, transparent 1px),
            radial-gradient(circle at 50% 60%, rgba(236,72,153,0.15) 0%, rgba(168,85,247,0.05) 40%, transparent 70%)
          `,
          backgroundSize: "40px 40px, 40px 40px, 100% 100%",
        }}
      />

      {/* Content Layer */}
      <div className="relative z-10 flex flex-col items-center justify-center py-12">
        <main className="mx-auto flex w-full max-w-[1280px] flex-col items-center px-6 py-8 text-center lg:px-10">
          <div className="relative w-full max-w-5xl">
            <h1 className={`${cormorant.className} mx-auto max-w-5xl text-balance text-[54px] leading-[0.95] tracking-tight sm:text-[72px] lg:text-[88px]`}>
              Your QA Agent that actually works
            </h1>
          </div>

          <p
            id="about"
            className="mt-8 max-w-3xl text-balance text-xl leading-tight text-surface-fg/90 sm:text-[30px]"
          >
            Autonomous QA scans across devices, networks, and key user flows.
            <br />
            Prioritized issues with reproducible evidence.
          </p>

          <Link
            href="/qa"
            className="mt-10 inline-flex min-h-11 items-center gap-2 rounded-xl bg-black px-7 py-3 text-lg font-medium text-white transition hover:-translate-y-0.5 dark:bg-white dark:text-black"
          >
            Try now <ArrowRight className="h-5 w-5 -rotate-10" />
          </Link>
        </main>
      </div>
    </>
  );
}
