/**
 * The project's central claim as a picture: a student describes a symptom ("my recursive
 * function crashes") without naming the real cause. Plain similarity search lands on Recursion
 * and stops; Cognexa then follows the PREREQUISITE_OF edge to Call Stack. Animated in steps;
 * with reduced motion the final (highlighted) state is shown immediately.
 */
export function FailureCase() {
  const step = (n: number) => ({ animation: `reveal 0.5s ease ${n}s both` });
  return (
    <figure className="rounded-2xl border border-border bg-surface p-4 sm:p-6">
      <svg
        viewBox="0 0 640 260"
        role="img"
        aria-label="A question about a recursive function crashing matches the Recursion concept; Cognexa then follows the prerequisite edge to Call Stack, which explains the crash."
        className="h-auto w-full"
      >
        {/* student question */}
        <g style={step(0)}>
          <rect
            x="8"
            y="96"
            width="170"
            height="68"
            rx="12"
            fill="var(--surface-2)"
            stroke="var(--border)"
          />
          <text x="93" y="124" textAnchor="middle" fontSize="12" fill="var(--text)">
            “Why does my recursive
          </text>
          <text x="93" y="142" textAnchor="middle" fontSize="12" fill="var(--text)">
            function crash at n = 5000?”
          </text>
        </g>

        {/* edge: question -> Recursion (both approaches get here) */}
        <line
          x1="178"
          y1="130"
          x2="262"
          y2="130"
          stroke="var(--muted)"
          strokeWidth="1.5"
          style={step(0.8)}
        />

        {/* Recursion */}
        <g style={step(1)}>
          <circle
            cx="300"
            cy="130"
            r="38"
            fill="var(--surface-2)"
            stroke="var(--primary)"
            strokeWidth="2"
          />
          <text
            x="300"
            y="134"
            textAnchor="middle"
            fontSize="12"
            fontWeight="600"
            fill="var(--text)"
          >
            Recursion
          </text>
          <text x="300" y="196" textAnchor="middle" fontSize="11" fill="var(--muted)">
            Plain RAG stops here
          </text>
        </g>

        {/* the prerequisite edge, drawn in */}
        <g style={step(2)}>
          <line
            x1="338"
            y1="130"
            x2="452"
            y2="130"
            stroke="var(--accent)"
            strokeWidth="2.5"
            strokeDasharray="120"
            style={{ "--len": 120, animation: "draw 0.9s ease 2s both" } as React.CSSProperties}
          />
          <polygon points="452,124 464,130 452,136" fill="var(--accent)" />
          <text x="395" y="118" textAnchor="middle" fontSize="11" fill="var(--accent)">
            needs
          </text>
        </g>

        {/* Call Stack */}
        <g style={step(2.8)}>
          <circle
            cx="500"
            cy="130"
            r="44"
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2"
            style={{ animation: "pulse-ring 2.4s ease-in-out 3s infinite" }}
          />
          <circle
            cx="500"
            cy="130"
            r="38"
            fill="var(--surface-2)"
            stroke="var(--accent)"
            strokeWidth="2"
          />
          <text
            x="500"
            y="134"
            textAnchor="middle"
            fontSize="12"
            fontWeight="600"
            fill="var(--text)"
          >
            Call Stack
          </text>
          <text x="500" y="196" textAnchor="middle" fontSize="11" fill="var(--accent)">
            Cognexa walks the graph here
          </text>
        </g>
      </svg>
      <figcaption className="mt-3 text-sm text-muted">
        The student never said “stack”. A similarity search matches the word “recursive”. The
        knowledge graph knows the cause lives one prerequisite edge away.
      </figcaption>
    </figure>
  );
}
