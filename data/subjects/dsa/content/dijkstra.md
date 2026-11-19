---
id: dijkstra
name: "Dijkstra's Shortest Path"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 24.3 (Dijkstra's algorithm)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.4 (Shortest Paths, Dijkstra's algorithm)"
---

## Overview
Dijkstra's algorithm finds the shortest (least total weight) paths from one source vertex to every other vertex in a graph whose edge weights are all non-negative. It grows a set of vertices whose distance is final, always adding next the vertex with the smallest tentative distance, and then relaxes that vertex's outgoing edges to improve its neighbours' tentative distances. With a binary heap as the priority queue it runs in O((V + E) log V). It is the algorithm behind route planners, network routing protocols such as OSPF, and any problem that asks for a cheapest path with non-negative costs. It fails with negative edge weights, which is where Bellman-Ford takes over.

## Intuition
Imagine pouring water into a network of pipes at the source, where each pipe's length is its weight and water flows at a constant speed. The water reaches the nearest junction first, then the next nearest, and so on. The moment water first arrives at a junction, it has travelled the shortest route, because any other route would have to pass through junctions the water has not reached yet, which are farther away. Dijkstra's algorithm simulates this front of water by always settling the closest unsettled vertex next.

## How It Works
Setup. Set dist[source] = 0 and dist[v] = infinity for every other vertex. Put (0, source) into a min-priority queue keyed by distance.

Main loop. Pop the pair (d, u) with the smallest d. If d is larger than the current dist[u], this entry is stale (u was already reached more cheaply) and is skipped; this "lazy deletion" avoids needing a decrease-key operation. Otherwise u is settled, and its distance is final. For each edge u -> v with weight w, relax it: if dist[u] + w < dist[v], set dist[v] = dist[u] + w, record parent[v] = u, and push (dist[v], v).

Why it is correct. When u is popped with the smallest tentative distance, any other path to u would leave the settled set through some vertex x whose tentative distance is at least dist[u], and then add non-negative edge weights, so it cannot be shorter. This greedy argument needs every edge weight to be at least 0. A negative edge could make a later path cheaper after u has already been declared final.

Relation to BFS. If every edge weight is 1, the priority queue behaves like a FIFO queue and Dijkstra reduces to breadth-first search. Dijkstra generalises BFS by ordering the frontier by distance instead of by number of edges.

Paths. Following parent pointers from a target back to the source and reversing gives the actual shortest path. If only one target matters, the loop can stop as soon as that target is popped.

Priority queue choices. A binary heap gives O((V + E) log V). An unsorted array scanned each time gives O(V squared), which is better for very dense graphs. A Fibonacci heap gives O(E + V log V) in theory.

## Worked Example
Directed graph: 0 -> 1 (weight 4), 0 -> 2 (1), 2 -> 1 (2), 1 -> 3 (1), 2 -> 3 (5). Source 0.

```
      4
   0 ----> 1
   |      ^ |
  1|    2/  |1
   v    /   v
   2 -------> 3
        5
```

Start: dist = [0, inf, inf, inf], heap [(0, 0)]. Pop 0: relax 0 -> 1 gives dist[1] = 4 and 0 -> 2 gives dist[2] = 1; heap [(1, 2), (4, 1)]. Pop (1, 2): relax 2 -> 1, since 1 + 2 = 3 < 4, dist[1] = 3; relax 2 -> 3 gives dist[3] = 6; heap holds (3, 1), (4, 1), (6, 3). Pop (3, 1): relax 1 -> 3, since 3 + 1 = 4 < 6, dist[3] = 4. Pop (4, 1): stale because dist[1] is 3, so skip it. Pop (4, 3): settled. Pop (6, 3): stale. Final distances [0, 3, 1, 4], and the shortest path to 3 is 0 -> 2 -> 1 -> 3. The direct edge 0 -> 1 of weight 4 was beaten by the two-edge route of weight 3, which BFS would never notice.

## Code
```python
import heapq


def dijkstra(n, edges, source):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        if w < 0:
            raise ValueError("Dijkstra requires non-negative weights")
        adj[u].append((v, w))
    INF = float("inf")
    dist, parent = [INF] * n, [-1] * n
    dist[source] = 0
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue                            # stale entry, u already settled more cheaply
        for v, w in adj[u]:
            if d + w < dist[v]:                 # relax the edge
                dist[v] = d + w
                parent[v] = u
                heapq.heappush(heap, (dist[v], v))
    return dist, parent


def path_to(parent, target):
    path = []
    while target != -1:
        path.append(target)
        target = parent[target]
    return path[::-1]


edges = [(0, 1, 4), (0, 2, 1), (2, 1, 2), (1, 3, 1), (2, 3, 5)]
dist, parent = dijkstra(4, edges, 0)
assert dist == [0, 3, 1, 4]
assert path_to(parent, 3) == [0, 2, 1, 3]
dist2, _ = dijkstra(3, [(0, 1, 2)], 0)
assert dist2[2] == float("inf")                 # unreachable

import random


def brute_force(n, edges, s):                    # Bellman-Ford style reference
    d = [float("inf")] * n
    d[s] = 0
    for _ in range(n - 1):
        for u, v, w in edges:
            if d[u] + w < d[v]:
                d[v] = d[u] + w
    return d


random.seed(9)
for _ in range(100):
    n = random.randint(1, 15)
    es = [(random.randrange(n), random.randrange(n), random.randint(0, 20)) for _ in range(random.randint(0, 40))]
    assert dijkstra(n, es, 0)[0] == brute_force(n, es, 0)
print("all checks passed")
```

```cpp
#include <cassert>
#include <functional>
#include <iostream>
#include <limits>
#include <queue>
#include <tuple>
#include <utility>
#include <vector>

std::vector<long long> dijkstra(int n, const std::vector<std::tuple<int, int, int>>& edges, int src) {
    std::vector<std::vector<std::pair<int, int>>> adj(n);
    for (const auto& e : edges) adj[std::get<0>(e)].push_back({std::get<1>(e), std::get<2>(e)});
    const long long INF = std::numeric_limits<long long>::max();
    std::vector<long long> dist(n, INF);
    using Item = std::pair<long long, int>;
    std::priority_queue<Item, std::vector<Item>, std::greater<Item>> pq;   // min-heap
    dist[src] = 0;
    pq.push({0, src});
    while (!pq.empty()) {
        long long d = pq.top().first;
        int u = pq.top().second;
        pq.pop();
        if (d > dist[u]) continue;           // stale entry
        for (const auto& e : adj[u]) {
            int v = e.first, w = e.second;
            if (d + w < dist[v]) {
                dist[v] = d + w;
                pq.push({dist[v], v});
            }
        }
    }
    return dist;
}

int main() {
    std::vector<std::tuple<int, int, int>> edges = {
        std::make_tuple(0, 1, 4), std::make_tuple(0, 2, 1), std::make_tuple(2, 1, 2),
        std::make_tuple(1, 3, 1), std::make_tuple(2, 3, 5)};
    std::vector<long long> d = dijkstra(4, edges, 0);
    assert(d[0] == 0 && d[1] == 3 && d[2] == 1 && d[3] == 4);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
With a binary heap and lazy deletion, each edge relaxation may push one entry, so the heap holds O(E) entries and each operation costs O(log E) = O(log V). The total is O((V + E) log V) time and O(V + E) space. With an array instead of a heap, each of the V steps scans all vertices for the minimum, giving O(V squared), which is preferable when E is close to V squared. With a Fibonacci heap the bound is O(E + V log V). The algorithm is correct only for non-negative weights; with negative edges use Bellman-Ford, O(VE).

## Common Mistakes & Misconceptions
The best-known error is using Dijkstra with negative edge weights: it can settle a vertex too early and return wrong distances without any error message. Students forget the stale-entry check, so outdated heap entries relax edges with old distances and waste time (correctness usually survives, but the work can blow up). Marking a vertex as final when it is pushed instead of when it is popped gives wrong answers. Using a plain FIFO queue instead of a priority queue turns the algorithm into a buggy BFS. Initialising distances to a large number such as 999 instead of a true infinity causes wrong results on big graphs, and in C++ adding a weight to INT_MAX overflows to a negative number. Another misconception is that Dijkstra finds the longest path if you flip comparisons; longest paths are a different, much harder problem in general graphs.

## Builds On
This concept builds on Breadth-First Search: Dijkstra keeps the same structure of a frontier that expands from the source and settles vertices in order of distance, but orders the frontier by total weight rather than by edge count. It builds on Binary Heap, because the min-heap is what returns the closest unsettled vertex in O(log V) and makes the algorithm fast on sparse graphs. It also builds on Greedy Algorithms: at each step it makes the locally best choice (settle the nearest vertex) and never revisits it, and the correctness proof is a classic greedy-choice argument that relies on non-negative weights.

## Leads To
Bellman-Ford handles graphs with negative edges and detects negative cycles where Dijkstra cannot. A* search adds a heuristic estimate of the remaining distance to guide Dijkstra toward a target, which is what game and map pathfinding use. Dijkstra is also the core of link-state routing protocols, of Johnson's all-pairs algorithm (after reweighting), and of Prim's minimum spanning tree algorithm, which has the same heap-driven structure.

## Check Yourself
**Q1.** What condition on edge weights does Dijkstra's algorithm require?
**A1.** All edge weights must be non-negative.
**Q2.** What is the running time with a binary heap?
**A2.** O((V + E) log V).
**Q3.** When is a vertex's distance final?
**A3.** When it is popped from the priority queue with a distance equal to its current best distance.
