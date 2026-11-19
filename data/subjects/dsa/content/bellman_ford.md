---
id: bellman_ford
name: "Bellman-Ford"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 24.1 (The Bellman-Ford algorithm)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.4 (Negative weights, Bellman-Ford)"
---

## Overview
The Bellman-Ford algorithm computes single-source shortest paths in a weighted directed graph that may contain negative edge weights, and it also detects whether a negative-weight cycle is reachable from the source, in which case shortest paths are not defined. It works by relaxing every edge of the graph V - 1 times. It is slower than Dijkstra's algorithm, O(VE) instead of O((V + E) log V), but it is simpler, needs no priority queue, and handles cases Dijkstra cannot, such as currency exchange arbitrage, financial models with credits and debits, and distance-vector routing protocols like RIP.

## Intuition
Picture rumours of cheap travel routes spreading through a group of cities. In the first round, every city tells its neighbours the cheapest price it knows from the source plus the cost of one more leg. After the first round, cities one leg away know their best price; after the second round, cities reachable within two legs know theirs; and so on. A shortest path without cycles uses at most V - 1 legs, so after V - 1 rounds every city knows its true best price. If prices still drop in an extra round, somebody has found a loop that pays you to travel it, a negative cycle.

## How It Works
Relaxation. For an edge u -> v with weight w, relaxing it means: if dist[u] + w < dist[v], set dist[v] = dist[u] + w and parent[v] = u. Relaxation never makes a distance wrong; it only lowers an estimate to a value that is achievable.

Algorithm. Set dist[source] = 0 and every other distance to infinity. Repeat V - 1 times: relax every edge in the graph, in any order. Then do one more pass over all edges; if any edge can still be relaxed, a negative cycle is reachable from the source.

Why V - 1 rounds suffice. A shortest path in a graph without negative cycles is simple (it repeats no vertex), so it has at most V - 1 edges. By induction, after round i every vertex whose shortest path uses at most i edges has its correct distance, because the i-th edge of that path is relaxed during round i after its start vertex became correct in round i - 1.

Negative cycles. If a cycle has negative total weight and is reachable from the source, going around it again and again makes the path arbitrarily cheap, so "shortest path" has no answer. The extra pass catches this: any vertex whose distance still decreases is on or reachable from such a cycle. Following parent pointers V times from that vertex lands inside the cycle, from which the cycle can be printed.

Early stop. If a full round changes nothing, the distances are already final and the loop can stop early. This makes the algorithm fast on many practical inputs.

Comparison with Dijkstra. Dijkstra settles each vertex once using a greedy choice that negative edges break. Bellman-Ford makes no greedy commitment; it keeps relaxing every edge until no improvement is possible, which is why it tolerates negative weights at the cost of extra work.

## Worked Example
Edges in this order: 0 -> 1 (4), 0 -> 2 (5), 2 -> 1 (-3), 1 -> 3 (2). Source 0, four vertices, so at most 3 rounds.

```
       4
   0 -----> 1 ----> 3
   |        ^    2
  5|        | -3
   v        |
   2 -------+
```

Round 1: relax 0 -> 1, dist[1] = 4. Relax 0 -> 2, dist[2] = 5. Relax 2 -> 1: 5 - 3 = 2 < 4, so dist[1] = 2. Relax 1 -> 3: dist[3] = 4. Round 2: no edge improves anything, so stop early. Final distances: [0, 2, 5, 4]. Dijkstra would have settled vertex 1 at distance 4 before seeing the negative edge from 2, and its distance to 3 would be 6. Now add an edge 3 -> 2 with weight -4: the cycle 2 -> 1 -> 3 -> 2 has total -3 + 2 - 4 = -5, distances keep decreasing in every round, and the extra check pass reports a negative cycle.

## Code
```python
def bellman_ford(n, edges, source):
    INF = float("inf")
    dist, parent = [INF] * n, [-1] * n
    dist[source] = 0
    for _ in range(n - 1):
        changed = False
        for u, v, w in edges:
            if dist[u] != INF and dist[u] + w < dist[v]:     # relax
                dist[v] = dist[u] + w
                parent[v] = u
                changed = True
        if not changed:
            break                                           # early stop
    for u, v, w in edges:                                   # one extra pass
        if dist[u] != INF and dist[u] + w < dist[v]:
            return None, parent                             # negative cycle reachable
    return dist, parent


def negative_cycle(n, edges):
    """Return the vertices of some negative cycle, or None (checks the whole graph)."""
    dist, parent, last = [0] * n, [-1] * n, -1             # all zeros: a virtual source to every vertex
    for _ in range(n):
        last = -1
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                parent[v] = u
                last = v
    if last == -1:
        return None
    x = last
    for _ in range(n):                                      # step back into the cycle
        x = parent[x]
    cycle, y = [x], parent[x]
    while y != x:
        cycle.append(y)
        y = parent[y]
    return cycle[::-1]


edges = [(0, 1, 4), (0, 2, 5), (2, 1, -3), (1, 3, 2)]
dist, parent = bellman_ford(4, edges, 0)
assert dist == [0, 2, 5, 4]
bad = edges + [(3, 2, -4)]
assert bellman_ford(4, bad, 0)[0] is None
cyc = negative_cycle(4, bad)
assert sorted(cyc) == [1, 2, 3]
assert sum(w for u, v, w in bad if u in cyc and v in cyc) == -5
assert negative_cycle(4, edges) is None
assert bellman_ford(3, [(1, 2, -1)], 0)[0] == [0, float("inf"), float("inf")]   # unreachable stays inf
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <limits>
#include <tuple>
#include <vector>

// Returns false if a negative cycle is reachable from the source.
bool bellmanFord(int n, const std::vector<std::tuple<int, int, int>>& edges, int src,
                 std::vector<long long>& dist) {
    const long long INF = std::numeric_limits<long long>::max();
    dist.assign(n, INF);
    dist[src] = 0;
    for (int round = 0; round < n - 1; ++round) {
        bool changed = false;
        for (const auto& e : edges) {
            int u, v, w;
            std::tie(u, v, w) = e;
            if (dist[u] != INF && dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                changed = true;
            }
        }
        if (!changed) break;
    }
    for (const auto& e : edges) {
        int u, v, w;
        std::tie(u, v, w) = e;
        if (dist[u] != INF && dist[u] + w < dist[v]) return false;
    }
    return true;
}

int main() {
    std::vector<std::tuple<int, int, int>> edges = {
        std::make_tuple(0, 1, 4), std::make_tuple(0, 2, 5), std::make_tuple(2, 1, -3),
        std::make_tuple(1, 3, 2)};
    std::vector<long long> dist;
    assert(bellmanFord(4, edges, 0, dist));
    assert(dist[1] == 2 && dist[2] == 5 && dist[3] == 4);
    edges.push_back(std::make_tuple(3, 2, -4));
    assert(!bellmanFord(4, edges, 0, dist));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Each of the V - 1 rounds relaxes all E edges, so the worst case is O(VE) time, which is O(V cubed) for a dense graph. The extra detection pass adds O(E). Space is O(V) for the distance and parent arrays beyond the edge list. With the early-stop check, the best case is O(E) when distances settle after one round. The queue-based variant (often called SPFA) is faster on average but has the same worst case. For non-negative weights Dijkstra is much faster, so Bellman-Ford is chosen only when negative edges or cycle detection are needed.

## Common Mistakes & Misconceptions
A frequent bug is relaxing from vertices whose distance is still infinity: in Python inf - 3 is still inf so it is harmless, but in C++ adding a negative weight to INT_MAX or LLONG_MAX overflows and creates fake short paths, so always check dist[u] != INF. Running only V - 2 rounds, or stopping when one edge does not change, gives distances that are too large. Students forget the extra detection pass and print meaningless distances for graphs with a negative cycle. Another misconception is that any negative edge makes shortest paths undefined; only a negative cycle reachable from the source does. People confuse an undirected negative edge with a directed one: an undirected edge of negative weight is itself a negative cycle (going back and forth). Some believe the order of edges affects correctness; it affects only how quickly the distances converge.

## Builds On
This concept builds on Graph Basics & Representations, because the algorithm consumes the graph as a plain edge list of (u, v, w) triples and its O(VE) cost comes from scanning that list once per round. It builds on Dijkstra's Shortest Path, sharing the idea of relaxation, the distance and parent arrays and the path reconstruction, and it is best understood as the answer to the case Dijkstra cannot handle: when negative weights break Dijkstra's greedy settling, Bellman-Ford relaxes everything repeatedly instead.

## Leads To
Bellman-Ford is used inside Johnson's algorithm to reweight edges so Dijkstra can then compute all-pairs shortest paths on sparse graphs with negative weights. It detects arbitrage in currency exchange graphs (using negative logarithms of rates), solves systems of difference constraints in scheduling, and underlies distance-vector routing protocols. Floyd-Warshall solves the all-pairs version with a related relaxation idea.

## Check Yourself
**Q1.** How many rounds of relaxing all edges does Bellman-Ford need?
**A1.** V - 1, because a shortest simple path has at most V - 1 edges.
**Q2.** How does it detect a negative cycle?
**A2.** If any edge can still be relaxed after V - 1 rounds, a negative cycle is reachable from the source.
**Q3.** What is its time complexity?
**A3.** O(VE).
