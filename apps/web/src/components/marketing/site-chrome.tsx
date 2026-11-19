import { Network } from "lucide-react";
import Link from "next/link";

import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 text-text">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-fg">
            <Network aria-hidden className="size-4" />
          </span>
          <span className="text-lg font-semibold tracking-tight">Cognexa</span>
        </Link>
        <nav aria-label="Site" className="ml-4 hidden items-center gap-1 sm:flex">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="rounded-lg px-3 py-1.5 text-sm text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-text"
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {/* No prefetch: the auth pages pull in supabase-js + zod (~110 KB gzipped),
              which visitors who only read the public pages should not pay for. */}
          <Link
            prefetch={false}
            href="/login"
            className={cn(buttonVariants({ variant: "ghost" }), "h-9")}
          >
            Sign in
          </Link>
          <Link prefetch={false} href="/signup" className={cn(buttonVariants(), "h-9")}>
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="space-y-1">
          <p className="font-semibold text-text">Cognexa</p>
          <p className="text-sm text-muted">
            A knowledge-graph-grounded tutor for Data Structures &amp; Algorithms.
          </p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {[...NAV, { href: "/privacy", label: "Privacy" }, { href: "/terms", label: "Terms" }].map(
            (n) => (
              <Link key={n.href} href={n.href} className="text-muted hover:text-text">
                {n.label}
              </Link>
            ),
          )}
        </nav>
        <ThemeSwitcher />
      </div>
    </footer>
  );
}
