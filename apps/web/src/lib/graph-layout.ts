export interface GNode {
  id: string;
  name: string;
  cluster: string;
  difficulty: number;
}
export interface GEdge {
  source: string;
  target: string;
  type: string;
}
export interface Placed extends GNode {
  x: number;
  y: number;
  layer: number;
}

/**
 * Layered layout for a prerequisite DAG: a node's column is the length of the longest chain of
 * prerequisites before it, and nodes in a column are ordered by cluster then name so related
 * concepts sit together. Only PREREQUISITE_OF edges define layers. Cycles (which the backend
 * forbids) would be ignored rather than looping forever.
 */
export function layerLayout(
  nodes: GNode[],
  edges: GEdge[],
  width: number,
  height: number,
  pad = 24,
): Placed[] {
  const prereq = edges.filter((e) => e.type === "PREREQUISITE_OF");
  const incoming = new Map<string, string[]>();
  for (const n of nodes) incoming.set(n.id, []);
  for (const e of prereq) incoming.get(e.target)?.push(e.source);

  const layer = new Map<string, number>();
  const visiting = new Set<string>();
  const depth = (id: string): number => {
    const known = layer.get(id);
    if (known !== undefined) return known;
    if (visiting.has(id)) return 0; // defensive: cycle
    visiting.add(id);
    const d = Math.max(-1, ...(incoming.get(id) ?? []).map(depth)) + 1;
    visiting.delete(id);
    layer.set(id, d);
    return d;
  };
  nodes.forEach((n) => depth(n.id));

  const columns = new Map<number, GNode[]>();
  for (const n of nodes) {
    const l = layer.get(n.id) ?? 0;
    columns.set(l, [...(columns.get(l) ?? []), n]);
  }
  const maxLayer = Math.max(0, ...columns.keys());
  const placed: Placed[] = [];
  for (const [l, col] of columns) {
    col.sort((a, b) => a.cluster.localeCompare(b.cluster) || a.name.localeCompare(b.name));
    col.forEach((n, i) => {
      placed.push({
        ...n,
        layer: l,
        x: maxLayer === 0 ? width / 2 : pad + (l / maxLayer) * (width - 2 * pad),
        y: col.length === 1 ? height / 2 : pad + (i / (col.length - 1)) * (height - 2 * pad),
      });
    });
  }
  return placed;
}
