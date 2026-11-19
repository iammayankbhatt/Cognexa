import { describe, expect, it } from "vitest";

import { layerLayout, type GEdge, type GNode } from "@/lib/graph-layout";

const n = (id: string, cluster = "c"): GNode => ({ id, name: id, cluster, difficulty: 1 });
const pre = (source: string, target: string): GEdge => ({
  source,
  target,
  type: "PREREQUISITE_OF",
});

describe("layerLayout", () => {
  it("puts each node one column after its deepest prerequisite", () => {
    const placed = layerLayout(
      [n("a"), n("b"), n("c"), n("d")],
      [pre("a", "b"), pre("b", "c"), pre("a", "c"), pre("a", "d")],
      1000,
      600,
    );
    const layers = Object.fromEntries(placed.map((p) => [p.id, p.layer]));
    expect(layers).toEqual({ a: 0, b: 1, c: 2, d: 1 });
  });

  it("keeps every node inside the canvas and spreads columns left to right", () => {
    const placed = layerLayout([n("a"), n("b"), n("c")], [pre("a", "b"), pre("b", "c")], 900, 300);
    for (const p of placed) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(900);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeLessThanOrEqual(300);
    }
    const byId = Object.fromEntries(placed.map((p) => [p.id, p.x]));
    expect(byId.a).toBeLessThan(byId.b);
    expect(byId.b).toBeLessThan(byId.c);
  });

  it("ignores RELATED_TO edges when layering and survives a cycle", () => {
    const related: GEdge = { source: "a", target: "b", type: "RELATED_TO" };
    expect(layerLayout([n("a"), n("b")], [related], 100, 100).map((p) => p.layer)).toEqual([0, 0]);
    const cyc = layerLayout([n("a"), n("b")], [pre("a", "b"), pre("b", "a")], 100, 100);
    expect(cyc).toHaveLength(2);
  });

  it("handles an empty graph and a single node", () => {
    expect(layerLayout([], [], 100, 100)).toEqual([]);
    expect(layerLayout([n("a")], [], 100, 100)[0]).toMatchObject({ x: 50, y: 50 });
  });
});
