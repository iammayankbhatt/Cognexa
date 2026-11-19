import Link from "next/link";

import { cn } from "@/lib/utils";

import { masteryLevel } from "./mastery";

type Relation = "prerequisite" | "related" | "leads-to";

const RELATION_LABEL: Record<Relation, string> = {
  prerequisite: "Prerequisite",
  related: "Related",
  "leads-to": "Leads to",
};

const DOT: Record<"low" | "mid" | "high", string> = {
  low: "bg-danger",
  mid: "bg-warning",
  high: "bg-success",
};

interface ConceptChipProps {
  name: string;
  /** If set, the chip is a link to the concept page. */
  href?: string;
  relation?: Relation;
  /** Optional mastery (0..1) shown as a coloured dot. */
  mastery?: number;
  className?: string;
}

export function ConceptChip({ name, href, relation, mastery, className }: ConceptChipProps) {
  const classes = cn(
    "inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-2.5 py-1 text-xs font-medium text-text",
    "transition-colors duration-150",
    href && "hover:border-accent focus-visible:ring-2 focus-visible:ring-ring outline-none",
    className,
  );

  const content = (
    <>
      {mastery !== undefined && (
        <span
          aria-hidden
          data-testid="mastery-dot"
          className={cn("size-2 rounded-full", DOT[masteryLevel(mastery)])}
        />
      )}
      <span>{name}</span>
      {relation && <span className="font-normal text-muted">· {RELATION_LABEL[relation]}</span>}
    </>
  );

  return href ? (
    <Link href={href} className={classes}>
      {content}
    </Link>
  ) : (
    <span className={classes}>{content}</span>
  );
}
