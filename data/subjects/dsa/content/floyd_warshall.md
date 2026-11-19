---
id: floyd_warshall
name: "Floyd-Warshall"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 25.2 (The Floyd-Warshall algorithm)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.4 (All-pairs shortest paths, exercises)"
---

## Overview
The Floyd-Warshall algorithm computes the shortest path distance between every pair of vertices in a weighted graph in one run. It works on a V by V distance matrix and allows negative edge weights, as long as there is no negative cycle, which it can also detect. The algorithm is three nested loops over the vertices, so it runs in O(V cubed) time and O(V squared) space. It is the simplest way to get all-pairs distances for small or dense graphs, and it is a classic example of dynamic programming: each step reuses the answers of the previous step, adding one more allowed intermediate vertex at a time.

## Intuition
Imagine a table of flight prices between every pair of cities, where at first only direct flights are listed. Now ask: "would any trip be cheaper if it were allowed to change planes in city 1?" Update every entry that improves. Then allow changes in city 1 or city 2, then in cities 1 to 3, and so on. After every city has been allowed as a stopover, each table entry holds the cheapest possible route. The key insight is that when city k becomes allowed, the best route through k is just the best route to k followed by the best route from k, both of which are already in the table.

## How It Works
Matrix setup. Create dist[i][j] equal to the weight of the edge i -> j, 0 when i = j, and infinity when there is no edge. If there are parallel edges keep the lightest.

DP definition. Let d_k[i][j] be the shortest path from i to j that uses only vertices 0 to k - 1 as intermediate stops. Then d_0 is the initial matrix, and the recurrence is d_(k+1)[i][j] = min(d_k[i][j], d_k[i][k] + d_k[k][j]): either the best path does not use k, or it goes from i to k and then from k to j, each part using only earlier vertices. The answer is d_V.

In-place loops. For k from 0 to V - 1, for every i, for every j: if dist[i][k] + dist[k][j] < dist[i][j], update dist[i][j]. The outer loop must be over k, the intermediate vertex. Updating a single matrix in place is safe because row k and column k do not change during iteration k (dist[k][k] is 0 when there is no negative cycle).

Path reconstruction. Keep next[i][j], the first vertex after i on the best path from i to j. Initialise next[i][j] = j for every edge, and when dist[i][j] improves through k, set next[i][j] = next[i][k]. Following next from i reaches j along the shortest path.

Negative cycles. After the algorithm, if any dist[i][i] is negative, vertex i lies on a negative cycle, and distances involving such vertices are not meaningful.

Transitive closure. Replacing min and + with logical or and and gives Warshall's algorithm, which answers "can i reach j?" for all pairs.

When to use it. For a dense graph or a small V (up to a few hundred vertices), the short code and cache-friendly loops make it practical. For large sparse graphs, running Dijkstra from every vertex costs O(V (V + E) log V), which is much less.

## Worked Example
Three vertices with edges 0 -> 1 (3), 1 -> 2 (1), 0 -> 2 (7), 2 -> 0 (2). Initial matrix (rows are sources, inf means no edge): row 0 = [0, 3, 7], row 1 = [inf, 0, 1], row 2 = [2, inf, 0].

k = 0 (allow stopping at 0): dist[2][1] = min(inf, dist[2][0] + dist[0][1]) = 2 + 3 = 5. Nothing else improves. k = 1: dist[0][2] = min(7, dist[0][1] + dist[1][2]) = 3 + 1 = 4. k = 2: dist[1][0] = min(inf, dist[1][2] + dist[2][0]) = 1 + 2 = 3.

```
Final:      to 0  to 1  to 2
  from 0      0     3     4
  from 1      3     0     1
  from 2      2     5     0
```

The direct flight 0 -> 2 of cost 7 was replaced by 0 -> 1 -> 2 of cost 4, and vertex 1 can now reach 0 through 2. The diagonal stays 0, so there is no negative cycle.

## Code
```python
INF = float("inf")


def floyd_warshall(n, edges):
    dist = [[0 if i == j else INF for j in range(n)] for i in range(n)]
    nxt = [[j if i == j else None for j in range(n)] for i in range(n)]
    for u, v, w in edges:
        if w < dist[u][v]:
            dist[u][v] = w
            nxt[u][v] = v
    for k in range(n):                                  # intermediate vertex: outermost loop
        for i in range(n):
            if dist[i][k] == INF:
                continue
            for j in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
                    nxt[i][j] = nxt[i][k]
    return dist, nxt


def path(nxt, i, j):
    if nxt[i][j] is None:
        return []
    p = [i]
    while i != j:
        i = nxt[i][j]
        p.append(i)
    return p


def has_negative_cycle(dist):
    return any(dist[i][i] < 0 for i in range(len(dist)))


edges = [(0, 1, 3), (1, 2, 1), (0, 2, 7), (2, 0, 2)]
dist, nxt = floyd_warshall(3, edges)
assert dist == [[0, 3, 4], [3, 0, 1], [2, 5, 0]]
assert path(nxt, 0, 2) == [0, 1, 2] and path(nxt, 1, 0) == [1, 2, 0]
assert not has_negative_cycle(dist)
neg, _ = floyd_warshall(3, [(0, 1, 1), (1, 2, -2), (2, 0, -1)])
assert has_negative_cycle(neg)
d2, n2 = floyd_warshall(3, [(0, 1, 5)])
assert d2[1][0] == INF and path(n2, 1, 0) == []
neg_edge, _ = floyd_warshall(3, [(0, 1, 4), (0, 2, 5), (2, 1, -3)])
assert neg_edge[0][1] == 2                             # negative edge, no negative cycle
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <limits>
#include <tuple>
#include <vector>

const long long INF = std::numeric_limits<long long>::max() / 4;   // headroom so INF + INF does not overflow

std::vector<std::vector<long long>> floydWarshall(int n, const std::vector<std::tuple<int, int, int>>& edges) {
    std::vector<std::vector<long long>> d(n, std::vector<long long>(n, INF));
    for (int i = 0; i < n; ++i) d[i][i] = 0;
    for (const auto& e : edges) {
        int u, v, w;
        std::tie(u, v, w) = e;
        d[u][v] = std::min<long long>(d[u][v], w);
    }
    for (int k = 0; k < n; ++k)
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                if (d[i][k] < INF && d[k][j] < INF) d[i][j] = std::min(d[i][j], d[i][k] + d[k][j]);
    return d;
}

int main() {
    std::vector<std::tuple<int, int, int>> edges = {
        std::make_tuple(0, 1, 3), std::make_tuple(1, 2, 1), std::make_tuple(0, 2, 7),
        std::make_tuple(2, 0, 2)};
    auto d = floydWarshall(3, edges);
    assert(d[0][2] == 4 && d[1][0] == 3 && d[2][1] == 5);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Three nested loops over V vertices give Theta(V cubed) time regardless of the number of edges, and the distance matrix (plus the next matrix for paths) needs Theta(V squared) space. For V = 400 that is 64 million simple steps, which is fast; for V = 100000 it is hopeless. Running Dijkstra from every source costs O(V (V + E) log V), which is better for sparse graphs with non-negative weights; Johnson's algorithm extends that to negative weights by first reweighting with Bellman-Ford. Floyd-Warshall's advantages are tiny code, no priority queue, support for negative edges and good cache behaviour on dense inputs.

## Common Mistakes & Misconceptions
The classic bug is putting the k loop inside the i and j loops, which looks harmless but computes wrong distances because intermediate results are used before they are final; k must be the outermost loop. Initialising the diagonal to infinity instead of 0 makes every path look unreachable through itself. In C++, using INT_MAX for infinity and adding two of them overflows to a negative number, which then looks like a very short path; use a smaller sentinel or check for infinity first. Treating 0 as "no edge" in the input matrix breaks graphs with zero-weight edges. Students forget to check the diagonal for negative values and report distances in a graph with a negative cycle. Another misconception is that it is always better than repeated Dijkstra; it is only better for small or dense graphs.

## Builds On
This concept builds on Graph Basics & Representations, because the algorithm works directly on the adjacency matrix form of a weighted graph, using infinity for missing edges and O(1) access to dist[i][j]. It builds on Dynamic Programming (memoization & tabulation): the state d_k[i][j] (shortest path using only the first k vertices as stops), the recurrence that chooses between skipping or using vertex k, and the bottom-up order in which k grows, are a textbook tabulation, with the extra trick of reusing one table in place.

## Leads To
Floyd-Warshall leads to transitive closure (Warshall's algorithm) for reachability, to the computation of graph diameter and centrality measures, and to minimax and maximin path problems by swapping the operators. It is also a stepping stone to algebraic path problems and matrix-multiplication views of shortest paths, and it is compared with Johnson's algorithm for all-pairs shortest paths in sparse graphs.

## Check Yourself
**Q1.** What is the time complexity of Floyd-Warshall?
**A1.** O(V cubed).
**Q2.** Which loop must be outermost?
**A2.** The loop over the intermediate vertex k.
**Q3.** How do you detect a negative cycle after running it?
**A3.** Check whether any diagonal entry dist[i][i] is negative.
