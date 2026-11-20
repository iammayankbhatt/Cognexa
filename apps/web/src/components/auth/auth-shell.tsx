import { Network } from "lucide-react";
import Link from "next/link";

import { ThemeSwitcher } from "@/components/theme/theme-switcher";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-6 px-4 py-10">
      <Link href="/" className="flex items-center gap-2 text-text">
        <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-fg">
          <Network aria-hidden className="size-5" />
        </span>
        <span className="text-xl font-semibold tracking-tight">Cognexa</span>
      </Link>
      <section className="w-full max-w-sm space-y-5 rounded-2xl border border-border bg-surface p-6 shadow-sm">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-text">{title}</h1>
          {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
        </header>
        {children}
        {footer && (
          <div className="border-t border-border pt-4 text-center text-sm text-muted">{footer}</div>
        )}
      </section>
      <ThemeSwitcher />
    </main>
  );
}

export function FormMessage({
  tone,
  children,
}: {
  tone: "error" | "success" | "info";
  children: React.ReactNode;
}) {
  const styles = {
    error: "border-danger/40 bg-danger/5 text-text",
    success: "border-success/40 bg-success/5 text-text",
    info: "border-border bg-surface-2 text-text",
  }[tone];
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={`rounded-lg border px-3 py-2 text-sm ${styles}`}
    >
      {children}
    </p>
  );
}

// Always underlined: links inside a sentence must not rely on colour alone (WCAG 1.4.1).
export const linkClass = "text-accent underline underline-offset-4 hover:decoration-2";
