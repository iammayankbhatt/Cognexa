import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  /** Small label above the title (e.g. a section name). */
  eyebrow?: string;
  /** Right-aligned actions (buttons). */
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, description, eyebrow, actions, className }: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0 space-y-1.5">
        {eyebrow && (
          <p className="text-xs font-semibold tracking-widest text-accent uppercase">{eyebrow}</p>
        )}
        <h1 className="text-3xl font-semibold tracking-tight text-balance text-text">{title}</h1>
        {description && <p className="max-w-2xl text-base text-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
