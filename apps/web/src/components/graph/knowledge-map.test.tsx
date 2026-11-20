import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ClusterBars } from "@/components/dashboard/charts";
import { elementsFor, mapStyle } from "@/components/graph/knowledge-map";
import { timeAgo, type MasteryGraph } from "@/lib/dashboard";
import { sheetFileName } from "@/lib/notes";

const graph: MasteryGraph = {
  subject_id: "dsa",
  nodes: [
    {
      id: "a",
      name: "A",
      cluster: "foundations",
      difficulty: 1,
      order_index: 0,
      description: "",
      mastery: 0.9,
      band: "strong",
      attempts: 3,
      last_practiced_at: null,
      next_review_at: null,
    },
    {
      id: "b",
      name: "B",
      cluster: "trees",
      difficulty: 3,
      order_index: 1,
      description: "",
      mastery: null,
      band: "not_started",
      attempts: 0,
      last_practiced_at: null,
      next_review_at: null,
    },
  ],
  edges: [
    { source: "a", target: "b", type: "PREREQUISITE_OF" },
    { source: "a", target: "b", type: "RELATED_TO" },
  ],
};

describe("knowledge map helpers", () => {
  it("builds elements with size by difficulty and optional related edges", () => {
    const els = elementsFor(graph, false);
    expect(els.filter((e) => e.data.source)).toHaveLength(1);
    expect(els.find((e) => e.data.id === "b")?.data.size).toBe(36);
    expect(elementsFor(graph, true).filter((e) => e.data.source)).toHaveLength(2);
  });

  it("colours bands from theme variables only", () => {
    const read = (name: string) => `var${name}`;
    const style = JSON.stringify(mapStyle(read));
    expect(style).toContain("var--danger");
    expect(style).toContain("var--success");
    expect(style).not.toMatch(/#[0-9a-f]{6}/i);
  });
});

describe("dashboard helpers", () => {
  it("formats relative times", () => {
    const now = new Date("2026-11-20T12:00:00Z");
    expect(timeAgo("2026-11-20T11:59:30Z", now)).toBe("just now");
    expect(timeAgo("2026-11-20T11:00:00Z", now)).toBe("1 h ago");
    expect(timeAgo("2026-11-19T10:00:00Z", now)).toBe("yesterday");
    expect(timeAgo("2026-11-15T12:00:00Z", now)).toBe("5 days ago");
  });

  it("offers a table view of the cluster chart", async () => {
    render(
      <ClusterBars data={[{ cluster: "trees", concepts: 13, practised: 2, mastery: 0.31 }]} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Show table" }));
    expect(screen.getByRole("cell", { name: "Trees" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "31%" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "2/13" })).toBeInTheDocument();
  });

  it("names downloaded sheets from their title", () => {
    expect(
      sheetFileName({
        content: "# Revision: Recursion & Stacks!\n\nbody",
        created_at: "2026-11-20T10:00:00Z",
      }),
    ).toBe("revision-recursion-stacks-2026-11-20.md");
    expect(sheetFileName({ content: "", created_at: "2026-11-20T10:00:00Z" })).toBe(
      "revision-sheet-2026-11-20.md",
    );
  });
});
