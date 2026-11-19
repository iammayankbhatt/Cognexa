"use client";

import { BookOpen, Brain, Flame, Inbox, Target } from "lucide-react";
import { toast } from "sonner";

import { ConceptChip } from "@/components/shared/concept-chip";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { MasteryBadge } from "@/components/shared/mastery-badge";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { THEMES } from "@/lib/themes";

const TOKENS = [
  { name: "bg", cls: "bg-bg", note: "Page background" },
  { name: "surface", cls: "bg-surface", note: "Cards, panels" },
  { name: "surface-2", cls: "bg-surface-2", note: "Raised / hover" },
  { name: "border", cls: "bg-border", note: "Dividers" },
  { name: "text", cls: "bg-text", note: "Body text" },
  { name: "muted", cls: "bg-muted", note: "Secondary text" },
  { name: "primary", cls: "bg-primary", note: "Buttons, surfaces" },
  { name: "primary-fg", cls: "bg-primary-fg", note: "Text on primary" },
  { name: "accent", cls: "bg-accent", note: "Highlights, focus" },
  { name: "success", cls: "bg-success", note: "Positive" },
  { name: "warning", cls: "bg-warning", note: "Caution" },
  { name: "danger", cls: "bg-danger", note: "Errors" },
] as const;

const TYPE_SCALE = [
  { cls: "text-5xl font-semibold tracking-tight", label: "Display · 48" },
  { cls: "text-3xl font-semibold tracking-tight", label: "Heading 1 · 30" },
  { cls: "text-2xl font-semibold", label: "Heading 2 · 24" },
  { cls: "text-xl font-semibold", label: "Heading 3 · 20" },
  { cls: "text-base", label: "Body · 16" },
  { cls: "text-sm", label: "Small · 14" },
  { cls: "text-xs", label: "Caption · 12" },
] as const;

function Section({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="space-y-4">
      <div>
        <h2 id={`${id}-title`} className="text-xl font-semibold">
          {title}
        </h2>
        {description && <p className="text-sm text-muted">{description}</p>}
      </div>
      {children}
    </section>
  );
}

/** A small slice of UI rendered inside a scoped data-theme so all three themes show at once. */
function ThemeSample({ id, label }: { id: (typeof THEMES)[number]["id"]; label: string }) {
  return (
    <div
      data-theme={id}
      className="space-y-4 rounded-xl border border-border bg-bg p-5 text-text"
      aria-label={`${label} sample`}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{label}</h3>
        <MasteryBadge value={0.82} />
      </div>
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm">Why does my recursive function crash?</p>
        <p className="mt-1 text-xs text-muted">Retrieved: Recursion → Call Stack</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button>Primary</Button>
        <Button variant="outline">Outline</Button>
        <ConceptChip name="Call Stack" relation="prerequisite" mastery={0.3} />
      </div>
      <div className="flex gap-2">
        <MasteryBadge value={0.2} />
        <MasteryBadge value={0.55} />
      </div>
    </div>
  );
}

export function DesignShowcase() {
  return (
    <main className="mx-auto max-w-6xl space-y-12 px-4 py-10 sm:px-6">
      <PageHeader
        eyebrow="Design system"
        title="Cognexa design reference"
        description="Every token and shared component in the active theme. Dev-only: this route returns 404 in production."
        actions={<ThemeSwitcher />}
      />

      <Section
        id="themes"
        title="All three themes at once"
        description="Each card is scoped to its own theme, independent of the active one."
      >
        <div className="grid gap-4 lg:grid-cols-3">
          {THEMES.map((t) => (
            <ThemeSample key={t.id} id={t.id} label={t.label} />
          ))}
        </div>
      </Section>

      <Section id="colors" title="Colour tokens" description="Defined as CSS variables per theme.">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {TOKENS.map((t) => (
            <div
              key={t.name}
              className="overflow-hidden rounded-xl border border-border bg-surface"
            >
              <div className={`${t.cls} h-16 border-b border-border`} />
              <div className="p-3">
                <p className="font-mono text-sm">--{t.name}</p>
                <p className="text-xs text-muted">{t.note}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section id="type" title="Typography" description="Geist for UI, JetBrains Mono for code.">
        <Card>
          <CardContent className="space-y-3">
            {TYPE_SCALE.map((t) => (
              <div key={t.label} className="flex flex-wrap items-baseline gap-x-4">
                <span className="w-32 shrink-0 font-mono text-xs text-muted">{t.label}</span>
                <span className={t.cls}>Prerequisites before pointers</span>
              </div>
            ))}
            <div className="flex flex-wrap items-baseline gap-x-4">
              <span className="w-32 shrink-0 font-mono text-xs text-muted">Mono · 14</span>
              <code className="rounded-md bg-surface-2 px-2 py-1 font-mono text-sm">
                def fib(n): return n if n &lt; 2 else fib(n - 1) + fib(n - 2)
              </code>
            </div>
          </CardContent>
        </Card>
      </Section>

      <Section id="buttons" title="Buttons & badges">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Default</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="link">Link</Button>
          <Button disabled>Disabled</Button>
          <Button size="sm">Small</Button>
          <Button size="lg">Large</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge>Default</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <Badge variant="outline">Outline</Badge>
          <Badge variant="destructive">Destructive</Badge>
        </div>
      </Section>

      <Section id="inputs" title="Inputs">
        <div className="grid max-w-xl gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="demo-name">Concept</Label>
            <Input id="demo-name" placeholder="e.g. Call Stack" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="demo-invalid">Invalid</Label>
            <Input id="demo-invalid" aria-invalid defaultValue="???" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="demo-disabled">Disabled</Label>
            <Input id="demo-disabled" disabled defaultValue="Read only" />
          </div>
        </div>
      </Section>

      <Section id="cards" title="Stat cards & cards">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Concepts mastered" value="23" hint="of 69 in DSA" icon={<Brain />} />
          <StatCard label="Day streak" value="7" hint="Best: 12" icon={<Flame />} />
          <StatCard label="Quizzes taken" value="18" hint="+3 this week" icon={<Target />} />
          <StatCard label="Notes" value="42" hint="Across 11 concepts" icon={<BookOpen />} />
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Recommended next: Call Stack</CardTitle>
            <CardDescription>
              Your weak area is Recursion, and its prerequisite is shaky.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <ConceptChip name="Functions" relation="prerequisite" mastery={0.85} />
            <ConceptChip name="Call Stack" relation="prerequisite" mastery={0.5} />
            <ConceptChip name="Recursion" mastery={0.2} href="#cards" />
            <ConceptChip name="DFS" relation="leads-to" />
          </CardContent>
        </Card>
      </Section>

      <Section id="mastery" title="Mastery badges" description="Low < 40%, mid 40–75%, high ≥ 75%.">
        <div className="flex flex-wrap items-center gap-3">
          <MasteryBadge value={0.15} />
          <MasteryBadge value={0.55} />
          <MasteryBadge value={0.9} />
          <MasteryBadge value={0.55} showValue={false} />
        </div>
      </Section>

      <Section id="tabs" title="Tabs">
        <Tabs defaultValue="python" className="max-w-xl">
          <TabsList>
            <TabsTrigger value="python">Python</TabsTrigger>
            <TabsTrigger value="cpp">C++</TabsTrigger>
            <TabsTrigger value="notes">Notes</TabsTrigger>
          </TabsList>
          <TabsContent value="python">
            <pre className="overflow-x-auto rounded-lg border border-border bg-surface-2 p-4 font-mono text-sm">
              {`def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)`}
            </pre>
          </TabsContent>
          <TabsContent value="cpp">
            <pre className="overflow-x-auto rounded-lg border border-border bg-surface-2 p-4 font-mono text-sm">
              {`int factorial(int n) {\n  return n <= 1 ? 1 : n * factorial(n - 1);\n}`}
            </pre>
          </TabsContent>
          <TabsContent value="notes">
            <p className="text-sm text-muted">
              Each recursive call adds a frame to the call stack.
            </p>
          </TabsContent>
        </Tabs>
      </Section>

      <Section id="overlays" title="Dialog & toasts">
        <div className="flex flex-wrap items-center gap-3">
          <Dialog>
            <DialogTrigger render={<Button variant="outline" />}>Open dialog</DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Report this answer</DialogTitle>
                <DialogDescription>
                  Tell us what was wrong. A reviewer will look at it.
                </DialogDescription>
              </DialogHeader>
              <Input aria-label="What went wrong" placeholder="It missed the prerequisite…" />
              <DialogFooter>
                <Button>Send report</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button variant="secondary" onClick={() => toast.success("Quiz saved")}>
            Success toast
          </Button>
          <Button variant="secondary" onClick={() => toast.info("Warming up the server…")}>
            Info toast
          </Button>
          <Button variant="secondary" onClick={() => toast.warning("Daily AI quota almost used")}>
            Warning toast
          </Button>
          <Button variant="secondary" onClick={() => toast.error("Could not reach the API")}>
            Error toast
          </Button>
        </div>
      </Section>

      <Section id="states" title="Loading, empty and error states">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <LoadingSkeleton variant="stat" count={2} label="Loading stats" />
            <LoadingSkeleton variant="card" label="Loading card" />
            <LoadingSkeleton variant="list" count={2} label="Loading list" />
          </div>
          <div className="space-y-4">
            <EmptyState
              icon={<Inbox />}
              title="No quizzes yet"
              description="Take your first quiz and your mastery map will start filling in."
              action={<Button>Start a quiz</Button>}
            />
            <ErrorState
              message="The tutor service didn't respond. It may be waking up (free tier)."
              requestId="3f9c2a1b7d4e4a0c"
              onRetry={() => toast.info("Retrying…")}
            />
          </div>
        </div>
      </Section>
    </main>
  );
}
