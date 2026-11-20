import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NextStep, PathChain } from "@/components/recommend/next-step-card";
import { pathConcepts, type RecommendationItem } from "@/lib/recommend";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const r1: RecommendationItem = {
  id: "log-1",
  concept_id: "call_stack",
  name: "Function Calls & the Call Stack",
  rule: "R1",
  reason:
    "You've struggled with Tree Traversals; it builds on Recursion, which builds on Call Stack — start there.",
  action: "learn",
  path: [
    { source: "call_stack", target: "recursion" },
    { source: "recursion", target: "dfs_tree_traversals" },
  ],
  names: { recursion: "Recursion", dfs_tree_traversals: "Tree Traversals" },
};

function wrap(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

describe("recommendation display", () => {
  it("orders path concepts from the gap to the struggling concept", () => {
    expect(pathConcepts(r1.path)).toEqual(["call_stack", "recursion", "dfs_tree_traversals"]);
    expect(pathConcepts([])).toEqual([]);
  });

  it("renders the path chain with names, gap first", () => {
    render(<PathChain item={r1} />);
    const items = screen.getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toEqual(["Function Calls & the Call Stack", "Recursion", "Tree Traversals"]);
  });

  it("shows the rule, reason and a learn link", () => {
    wrap(<NextStep item={r1} />);
    expect(screen.getByText("Fix the root cause")).toBeInTheDocument();
    expect(screen.getByText(/start there/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Learn Function Calls/ })).toHaveAttribute(
      "href",
      "/app/learn/call_stack",
    );
  });

  it("uses review and practice actions", () => {
    const { rerender } = wrap(
      <NextStep item={{ ...r1, rule: "R3", action: "review", path: [] }} />,
    );
    expect(screen.getByRole("link", { name: /Start review/ })).toHaveAttribute(
      "href",
      "/app/review",
    );
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <NextStep item={{ ...r1, rule: "R2", action: "practice", path: [] }} />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("button", { name: /Practise Function Calls/ })).toBeInTheDocument();
    expect(screen.getByText("Focused review")).toBeInTheDocument();
  });
});
