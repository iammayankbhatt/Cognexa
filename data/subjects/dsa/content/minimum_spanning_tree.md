---
id: minimum_spanning_tree
name: "Minimum Spanning Tree (Kruskal & Prim)"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Chapter 23 (Minimum Spanning Trees), Sections 23.1 and 23.2"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.3 (Minimum Spanning Trees)"
---

## Overview
A spanning tree of a connected, undirected, weighted graph is a subset of its edges that connects all V vertices with no cycles, so it has exactly V - 1 edges. A minimum spanning tree (MST) is a spanning tree whose total edge weight is as small as possible. MSTs answer questions such as "what is the cheapest way to lay cable so that every building is connected?" Two classic greedy algorithms find one: Kruskal's algorithm adds edges in increasing weight order, skipping any that would close a cycle, using union-find; Prim's algorithm grows a single tree from a start vertex, always adding the cheapest edge leaving the tree, using a priority queue. Both run in O(E log V).

## Intuition
Imagine connecting villages with roads at the lowest total cost. Kruskal's approach is to look at all possible roads sorted from cheapest to most expensive and build each one unless the two villages are already connected by roads you built, because then the new road would be wasted. Prim's approach is to start in one village and keep building the cheapest road from the connected area to any village not yet connected, like spreading outward. Both are greedy, choosing the cheapest safe option now, and a property of cuts guarantees that greed is never punished here.

## How It Works
The cut property. Split the vertices into any two non-empty groups (a cut). The lightest edge crossing the cut belongs to some MST. Both algorithms only ever add such an edge, which is why their greedy choices are safe. A related cycle property says the heaviest edge on any cycle (if unique) is in no MST.

Kruskal's algorithm. Sort all edges by weight. Start with a union-find structure where each vertex is its own component. For each edge (u, v, w) in sorted order: if find(u) != find(v), the edge joins two different components, so add it to the tree and union them; otherwise it would form a cycle, so skip it. Stop after V - 1 edges are added. The edge considered is always the lightest edge crossing the cut between u's component and the rest.

Prim's algorithm. Pick a start vertex and mark it as in the tree. Push all its edges into a min-heap keyed by weight. Repeatedly pop the lightest edge; if it leads to a vertex already in the tree, discard it (lazy deletion); otherwise add the edge and the vertex to the tree and push that vertex's edges to vertices not yet in the tree. Stop when all vertices are in the tree. Each added edge is the lightest one crossing the cut between the tree and the rest.

Uniqueness. If all edge weights are distinct the MST is unique. With equal weights there may be several MSTs with the same total.

Disconnected graphs. If the graph is not connected there is no spanning tree. Kruskal's then naturally produces a minimum spanning forest (one tree per component), while Prim's covers only the start vertex's component.

Choosing between them. Kruskal's is simple when edges come as a list and the graph is sparse. Prim's with a heap suits adjacency lists, and an array-based Prim's in O(V squared) is best for dense graphs.

## Worked Example
Vertices 0 to 3 and edges 0-1 (1), 1-2 (2), 0-2 (3), 2-3 (4), 1-3 (5).

```
    0 --1-- 1
     \     / \
      3   2   5
       \ /     \
        2 --4-- 3
```

Kruskal's: sorted edges 0-1 (1), 1-2 (2), 0-2 (3), 2-3 (4), 1-3 (5). Take 0-1, components {0, 1}. Take 1-2, components {0, 1, 2}. Skip 0-2, because 0 and 2 are already connected. Take 2-3, all vertices connected after V - 1 = 3 edges. Total weight 1 + 2 + 4 = 7. Prim's from 0: the heap holds 0-1 (1) and 0-2 (3); take 0-1. Push 1-2 (2) and 1-3 (5); take 1-2. Push 2-3 (4); the heap's minimum is 0-2 (3) but 2 is already in the tree, so discard it; take 2-3 (4). Same tree, total 7.

## Code
```python
import heapq


class DSU:
    def __init__(self, n):
        self.parent, self.size = list(range(n)), [1] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return True


def kruskal(n, edges):
    dsu, tree, total = DSU(n), [], 0
    for u, v, w in sorted(edges, key=lambda e: e[2]):
        if dsu.union(u, v):                       # skip edges that would close a cycle
            tree.append((u, v, w))
            total += w
            if len(tree) == n - 1:
                break
    return total, tree


def prim(n, edges, start=0):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((w, v))
        adj[v].append((w, u))
    in_tree, total, count = [False] * n, 0, 0
    heap = [(0, start)]
    while heap and count < n:
        w, u = heapq.heappop(heap)
        if in_tree[u]:
            continue                              # stale: u was reached by a cheaper edge
        in_tree[u] = True
        total += w
        count += 1
        for wv, v in adj[u]:
            if not in_tree[v]:
                heapq.heappush(heap, (wv, v))
    return total if count == n else None          # None: the graph is disconnected


edges = [(0, 1, 1), (1, 2, 2), (0, 2, 3), (2, 3, 4), (1, 3, 5)]
total, tree = kruskal(4, edges)
assert total == 7 and tree == [(0, 1, 1), (1, 2, 2), (2, 3, 4)]
assert prim(4, edges) == 7 and prim(4, edges, start=3) == 7
assert prim(4, [(0, 1, 1), (2, 3, 1)]) is None

import random

random.seed(8)
for _ in range(100):
    n = random.randint(2, 12)
    es = [(i - 1, i, random.randint(1, 30)) for i in range(1, n)]          # a path keeps it connected
    es += [(random.randrange(n), random.randrange(n), random.randint(1, 30)) for _ in range(random.randint(0, 25))]
    es = [e for e in es if e[0] != e[1]]
    k_total, k_tree = kruskal(n, es)
    assert len(k_tree) == n - 1 and k_total == prim(n, es)
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <numeric>
#include <tuple>
#include <vector>

struct DSU {
    std::vector<int> parent;
    explicit DSU(int n) : parent(n) { std::iota(parent.begin(), parent.end(), 0); }
    int find(int x) {
        while (parent[x] != x) x = parent[x] = parent[parent[x]];
        return x;
    }
    bool unite(int a, int b) {
        a = find(a);
        b = find(b);
        if (a == b) return false;
        parent[b] = a;
        return true;
    }
};

long long kruskal(int n, std::vector<std::tuple<int, int, int>> edges) {
    std::sort(edges.begin(), edges.end(),
              [](const std::tuple<int, int, int>& a, const std::tuple<int, int, int>& b) {
                  return std::get<2>(a) < std::get<2>(b);
              });
    DSU dsu(n);
    long long total = 0;
    int used = 0;
    for (const auto& e : edges) {
        if (dsu.unite(std::get<0>(e), std::get<1>(e))) {
            total += std::get<2>(e);
            if (++used == n - 1) break;
        }
    }
    return total;
}

int main() {
    std::vector<std::tuple<int, int, int>> edges = {
        std::make_tuple(0, 1, 1), std::make_tuple(1, 2, 2), std::make_tuple(0, 2, 3),
        std::make_tuple(2, 3, 4), std::make_tuple(1, 3, 5)};
    assert(kruskal(4, edges) == 7);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Kruskal's algorithm is dominated by sorting the edges, O(E log E) = O(E log V), plus nearly constant-time union-find operations, so O(E log V) total and O(V + E) space. Prim's algorithm with a binary heap and lazy deletion is also O(E log V), because each edge may be pushed and popped once. Prim's with an adjacency matrix and an array of best edge weights is O(V squared), which is optimal for dense graphs. With a Fibonacci heap Prim's runs in O(E + V log V). The resulting tree always has V - 1 edges.

## Common Mistakes & Misconceptions
A common mistake is confusing a minimum spanning tree with a shortest path tree: the MST minimises the total weight of all edges, not the distance from one source, so the path between two vertices in the MST can be longer than their shortest path. In Kruskal's algorithm, checking only whether both endpoints have been "seen" instead of whether they are in the same component wrongly skips edges that join two separate groups. Forgetting to stop or not checking for disconnected input produces a forest without warning. In Prim's, marking a vertex as in the tree when it is pushed instead of when it is popped can choose a heavier edge. Students apply these algorithms to directed graphs, where the MST problem is different (minimum arborescence). Another misconception is that negative weights break MST algorithms; they do not, since only the order of weights matters.

## Builds On
This concept builds on Graph Basics & Representations, because Kruskal's reads an edge list and Prim's walks adjacency lists. It builds on Disjoint Set Union (Union-Find), which is how Kruskal's tests in nearly constant time whether an edge's endpoints are already connected. It builds on Binary Heap, which gives Prim's the cheapest crossing edge in O(log V). It also builds on Greedy Algorithms: both methods make the locally cheapest safe choice at each step, and the cut property is the greedy-choice proof that this produces a global optimum.

## Leads To
MSTs are used to design networks (power grids, roads, cable and pipelines), to approximate the travelling salesman problem within a factor of two, for single-linkage clustering (remove the heaviest MST edges to form clusters), and in image segmentation. Other MST algorithms such as Boruvka's are the basis of parallel and distributed versions.

## Check Yourself
**Q1.** How many edges does a spanning tree of V vertices have?
**A1.** V - 1.
**Q2.** How does Kruskal's algorithm decide whether to skip an edge?
**A2.** It skips the edge if both endpoints are already in the same union-find component, because adding it would form a cycle.
**Q3.** Does the MST give the shortest path between every pair of vertices?
**A3.** No, it minimises the total weight of the tree, not individual path lengths.
