import { Network } from "lucide-react";
import Link from "next/link";

import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const showDesign = process.env.NODE_ENV !== "production";

  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col items-center justify-center gap-8 px-4 py-16 text-center">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-fg">
        <Network aria-hidden className="size-7" />
      </span>
      <div className="space-y-3">
        <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">Cognexa</h1>
        <p className="text-lg text-balance text-muted">
          A knowledge-graph-grounded AI tutor for Data Structures &amp; Algorithms.
        </p>
      </div>
      <ThemeSwitcher />
      {showDesign && (
        <Link href="/design" className={cn(buttonVariants({ variant: "outline" }))}>
          Open design reference
        </Link>
      )}
    </main>
  );
}
