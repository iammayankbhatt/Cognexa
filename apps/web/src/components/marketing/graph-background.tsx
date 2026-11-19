/**
 * Decorative concept-graph backdrop for the hero. Pure SVG with deterministic positions (no
 * randomness, so server and client agree). Nodes drift slowly; the global reduced-motion rule
 * in globals.css flattens the animation. Colours come only from theme variables.
 */
const NODES: [number, number][] = [
  [8, 20],
  [18, 55],
  [14, 82],
  [28, 30],
  [34, 68],
  [42, 12],
  [48, 46],
  [55, 80],
  [62, 28],
  [70, 58],
  [76, 14],
  [84, 40],
  [90, 72],
  [95, 22],
  [38, 90],
  [66, 92],
  [24, 8],
  [58, 60],
];
const EDGES: [number, number][] = [
  [0, 3],
  [1, 3],
  [1, 4],
  [2, 4],
  [3, 5],
  [3, 6],
  [4, 6],
  [4, 7],
  [5, 8],
  [6, 8],
  [6, 9],
  [7, 9],
  [8, 10],
  [8, 11],
  [9, 11],
  [9, 12],
  [10, 13],
  [11, 13],
  [11, 12],
  [14, 7],
  [15, 12],
  [16, 5],
  [17, 9],
  [6, 17],
];

export function GraphBackground({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      focusable="false"
      viewBox="0 0 100 100"
      preserveAspectRatio="xMidYMid slice"
      className={className}
    >
      <g stroke="var(--border)" strokeWidth="0.18" opacity="0.9">
        {EDGES.map(([a, b]) => (
          <line
            key={`${a}-${b}`}
            x1={NODES[a][0]}
            y1={NODES[a][1]}
            x2={NODES[b][0]}
            y2={NODES[b][1]}
          />
        ))}
      </g>
      {NODES.map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i % 5 === 0 ? 1.1 : 0.7}
          fill={i % 3 === 0 ? "var(--accent)" : "var(--primary)"}
          opacity={i % 3 === 0 ? 0.85 : 0.7}
          style={
            {
              "--dx": `${(i % 4) - 1.5}px`,
              "--dy": `${(i % 3) - 1}px`,
              animation: `drift ${9 + (i % 5) * 2}s ease-in-out ${i * -0.7}s infinite`,
            } as React.CSSProperties
          }
        />
      ))}
    </svg>
  );
}
