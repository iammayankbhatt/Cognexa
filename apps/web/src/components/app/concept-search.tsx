"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useMemo, useState } from "react";

import { api } from "@/lib/api";

interface ConceptLite {
  id: string;
  name: string;
  cluster: string;
}

/** Type-ahead search over the concept list (loaded once, filtered in the browser). */
export function ConceptSearch() {
  const router = useRouter();
  const listId = useId();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const { data } = useQuery({
    queryKey: ["concepts"],
    queryFn: () => api<ConceptLite[]>("/concepts"),
    staleTime: 10 * 60_000,
  });

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term || !data) return [];
    return data
      .filter((c) => c.name.toLowerCase().includes(term) || c.id.replace(/_/g, " ").includes(term))
      .slice(0, 8);
  }, [q, data]);

  function go(c: ConceptLite) {
    setQ("");
    setOpen(false);
    router.push(`/app/learn?concept=${encodeURIComponent(c.id)}`);
  }

  return (
    <div className="relative w-full max-w-md">
      <Search
        aria-hidden
        className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-muted"
      />
      <input
        type="search"
        role="combobox"
        aria-expanded={open && results.length > 0}
        aria-controls={listId}
        aria-label="Search concepts"
        placeholder="Search concepts…"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((i) => Math.min(i + 1, results.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((i) => Math.max(i - 1, 0));
          } else if (e.key === "Enter" && results[active]) {
            e.preventDefault();
            go(results[active]);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
        className="h-9 w-full rounded-lg border border-border bg-surface pr-3 pl-9 text-sm text-text outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring"
      />
      {open && q.trim() !== "" && (
        <ul
          id={listId}
          role="listbox"
          className="absolute top-11 z-30 w-full overflow-hidden rounded-lg border border-border bg-surface shadow-lg"
        >
          {results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-muted">No matching concepts</li>
          ) : (
            results.map((c, i) => (
              <li
                key={c.id}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => {
                  e.preventDefault();
                  go(c);
                }}
                className={`flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm text-text ${
                  i === active ? "bg-surface-2" : ""
                }`}
              >
                <span>{c.name}</span>
                <span className="text-xs text-muted">{c.cluster.replace(/_/g, " ")}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
