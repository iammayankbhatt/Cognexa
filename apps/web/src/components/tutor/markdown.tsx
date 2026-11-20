"use client";

import { Check, Copy } from "lucide-react";
import { memo, useEffect, useState, type ComponentPropsWithoutRef, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

// KaTeX (about 270 KB plus its stylesheet) is loaded the first time some text contains math,
// not with every page that renders Markdown (Phase 13 performance).
type KatexPlugin = typeof import("rehype-katex").default;
let katexPlugin: KatexPlugin | null = null;
let katexLoading: Promise<KatexPlugin> | null = null;

export function loadKatex(): Promise<KatexPlugin> {
  katexLoading ??= Promise.all([import("rehype-katex"), import("katex/dist/katex.min.css")]).then(
    ([m]) => (katexPlugin = m.default),
  );
  return katexLoading;
}

/** Inline $…$, display $$…$$ or \( … \) / \[ … \] math. */
export function hasMath(text: string): boolean {
  return /\$\$[\s\S]+?\$\$|\$[^$\n]+\$|\\\(|\\\[/.test(text);
}

function useKatex(needed: boolean): KatexPlugin | null {
  const [plugin, setPlugin] = useState<KatexPlugin | null>(katexPlugin);
  useEffect(() => {
    if (!needed || plugin) return;
    let live = true;
    void loadKatex().then((p) => {
      if (live) setPlugin(() => p);
    });
    return () => {
      live = false;
    };
  }, [needed, plugin]);
  return needed ? plugin : null;
}

import { ConceptChip } from "@/components/shared/concept-chip";
import { conceptIdFromHref, linkCitations } from "@/lib/tutor/text";
import { cn } from "@/lib/utils";

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (node && typeof node === "object" && "props" in node) {
    return textOf((node as { props: { children?: ReactNode } }).props.children);
  }
  return "";
}

function CodeBlock({ children, ...rest }: ComponentPropsWithoutRef<"pre">) {
  const [copied, setCopied] = useState(false);
  const code = textOf(children).replace(/\n$/, "");
  const lang = /language-(\w+)/.exec(
    (children as { props?: { className?: string } } | undefined)?.props?.className ?? "",
  )?.[1];
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard blocked: nothing to do
    }
  };
  return (
    <div className="group/code relative my-3 overflow-hidden rounded-lg border border-border bg-bg">
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5 text-xs text-muted">
        <span className="font-mono">{lang ?? "code"}</span>
        <button
          type="button"
          onClick={() => void copy()}
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors duration-150 outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={copied ? "Copied" : "Copy code"}
        >
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre {...rest} className="overflow-x-auto p-3 font-mono text-[13px] leading-relaxed">
        {children}
      </pre>
    </div>
  );
}

function makeComponents(names: Record<string, string>): Components {
  return {
    pre: CodeBlock,
    code: ({ className, children, ...rest }) => {
      const block = /language-|hljs/.test(className ?? "");
      return block ? (
        <code className={className} {...rest}>
          {children}
        </code>
      ) : (
        <code
          className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[0.85em] text-text"
          {...rest}
        >
          {children}
        </code>
      );
    },
    a: ({ href, children }) => {
      const id = conceptIdFromHref(href);
      if (id) {
        return (
          <ConceptChip
            name={names[id] ?? id.replace(/_/g, " ")}
            href={`/app/learn/${encodeURIComponent(id)}`}
            className="mx-0.5 align-baseline"
          />
        );
      }
      return (
        <a
          href={href}
          target="_blank"
          rel="noreferrer noopener"
          className="text-accent underline underline-offset-2"
        >
          {children}
        </a>
      );
    },
    p: ({ children }) => <p className="my-2 leading-relaxed">{children}</p>,
    ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-6">{children}</ul>,
    ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-6">{children}</ol>,
    h1: ({ children }) => <h3 className="mt-4 mb-2 text-lg font-semibold">{children}</h3>,
    h2: ({ children }) => <h3 className="mt-4 mb-2 text-base font-semibold">{children}</h3>,
    h3: ({ children }) => <h4 className="mt-3 mb-1.5 text-sm font-semibold">{children}</h4>,
    blockquote: ({ children }) => (
      <blockquote className="my-2 border-l-2 border-accent pl-3 text-muted">{children}</blockquote>
    ),
    table: ({ children }) => (
      <div className="my-3 overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">{children}</table>
      </div>
    ),
    th: ({ children }) => (
      <th className="border-b border-border bg-surface-2 px-3 py-1.5 text-left font-medium">
        {children}
      </th>
    ),
    td: ({ children }) => <td className="border-b border-border px-3 py-1.5">{children}</td>,
    hr: () => <hr className="my-4 border-border" />,
  };
}

interface MarkdownProps {
  text: string;
  /** concept id → display name, for citation chips. */
  conceptNames?: Record<string, string>;
  className?: string;
}

/**
 * Answer renderer: GFM, math (KaTeX), highlighted code with copy buttons and [[concept_id]]
 * citations as concept chips. Raw HTML in the text is never rendered (react-markdown default).
 */
export const Markdown = memo(function Markdown({
  text,
  conceptNames = {},
  className,
}: MarkdownProps) {
  const katex = useKatex(hasMath(text));
  return (
    <div className={cn("min-w-0 text-sm text-text [&>*:first-child]:mt-0", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[
          [rehypeHighlight, { detect: false, ignoreMissing: true }],
          ...(katex ? [katex] : []),
        ]}
        components={makeComponents(conceptNames)}
      >
        {linkCitations(text)}
      </ReactMarkdown>
    </div>
  );
});
