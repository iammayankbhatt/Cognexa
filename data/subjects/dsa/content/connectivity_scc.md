---
id: connectivity_scc
name: "Connected & Strongly Connected Components"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 22.5 (Strongly connected components)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.1 (Connected components) and Section 4.2 (Strong connectivity, Kosaraju-Sharir)"
---

## Overview
A connected component of an undirected graph is a maximal group of vertices in which every vertex can reach every other. A strongly connected component (SCC) of a directed graph is a maximal group in which every vertex can reach every other following edge directions, so for any two vertices u and v in the group there is a path from u to v and a path from v to u. Splitting a graph into components answers questions such as "how many separate islands does this network have?", "which web pages all link to each other in a loop?" or "which modules depend on each other circularly?". Undirected components need one sweep of DFS or BFS. Strongly connected components need a little more, and Kosaraju's algorithm finds them with two DFS passes in linear time.

## Intuition
For an undirected graph, think of islands joined by two-way bridges: a component is everything you can walk to from where you stand. For a directed graph, imagine a city of one-way streets. A strongly connected district is a set of intersections where you can drive from any one to any other and come back. You might be able to drive from district A into district B but never return, so A and B are separate districts. If you shrink each district to a single point, the one-way connections between districts can never form a loop, otherwise those districts would merge into one.

## How It Works
Undirected components. Loop over all vertices. Whenever a vertex is not yet labelled, start a DFS or BFS from it and label everything it reaches with a new component number. Each start finds exactly one component, and the number of starts is the number of components. A union-find structure over the edges gives the same answer and also handles edges arriving over time.

Why directed graphs are harder. In a directed graph, reachability is not symmetric. A DFS from a vertex finds everything it can reach, which can include several SCCs plus everything downstream of them, so a single sweep does not separate them.

Kosaraju's algorithm. First pass: run DFS over the whole directed graph and record the vertices in order of finishing time. Second pass: build the reversed graph (every edge u -> v becomes v -> u). Process vertices in decreasing order of finish time from the first pass; for each unvisited vertex, a DFS on the reversed graph collects exactly one SCC. Why it works: the vertex with the latest finish time lies in a "source" SCC of the component graph. In the reversed graph, edges leaving that SCC are turned around so they lead into it, so a DFS from there cannot escape its own SCC. Removing it and repeating peels the SCCs off one by one.

Tarjan's algorithm. A single-pass alternative that tracks, for each vertex, its discovery index and the lowest index reachable through its subtree (low-link). When a vertex's low-link equals its own index, it is the root of an SCC, and the vertices above it on an auxiliary stack form that SCC.

Condensation graph. Replacing each SCC by one node gives a DAG, called the condensation. It can then be topologically sorted, which is used to solve 2-SAT problems and to order mutually dependent modules.

## Worked Example
Directed graph with vertices 0 to 6 and edges 0 -> 1, 1 -> 2, 2 -> 0, 1 -> 3, 3 -> 4, 4 -> 5, 5 -> 3. Vertex 6 has no edges.

```
  0 -> 1 -> 3 -> 4
  ^    |    ^    |
  |    v    |    v
  +--- 2    +--- 5        6
```

First pass (DFS from 0, neighbours in list order): enter 0, 1, 2; 2 sees 0 already visited and finishes; back at 1, go to 3, 4, 5; 5 sees 3 visited and finishes, then 4, 3, 1, 0 finish; finally 6 starts and finishes. The finish order is 2, 5, 4, 3, 1, 0, 6. Second pass on the reversed graph in decreasing finish order: start at 6 and collect {6}. Next 0: reversed edges from 0 lead to 2, then from 2 to 1, and from 1 back to 0, giving {0, 1, 2}; the reversed edge 3 -> 1 points into this group, not out of it, so the search stays inside. Next 1 and 3: 1 is done, and from 3 the reversed edges reach 5 and 4, giving {3, 4, 5}. So there are three SCCs. The condensation has the edge {0, 1, 2} -> {3, 4, 5}, with {6} isolated, and it is acyclic.

## Code
```python
def undirected_components(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    comp, count = [-1] * n, 0
    for s in range(n):
        if comp[s] != -1:
            continue
        comp[s], stack = count, [s]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if comp[v] == -1:
                    comp[v] = count
                    stack.append(v)
        count += 1
    return count, comp


def kosaraju(n, edges):
    adj = [[] for _ in range(n)]
    radj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        radj[v].append(u)

    seen, order = [False] * n, []

    def dfs1(u):                              # first pass: record finish order
        seen[u] = True
        for v in adj[u]:
            if not seen[v]:
                dfs1(v)
        order.append(u)

    for s in range(n):
        if not seen[s]:
            dfs1(s)

    comp = [-1] * n

    def dfs2(u, label):                        # second pass on the reversed graph
        comp[u] = label
        for v in radj[u]:
            if comp[v] == -1:
                dfs2(v, label)

    sccs = []
    for u in reversed(order):                  # decreasing finish time
        if comp[u] == -1:
            dfs2(u, len(sccs))
            sccs.append(sorted(x for x in range(n) if comp[x] == len(sccs)))
    return sccs


edges = [(0, 1), (1, 2), (2, 0), (1, 3), (3, 4), (4, 5), (5, 3)]
sccs = kosaraju(7, edges)
assert sorted(sccs) == [[0, 1, 2], [3, 4, 5], [6]]
assert kosaraju(3, [(0, 1), (1, 2)]) == [[0], [1], [2]]        # a chain: every vertex alone
assert len(kosaraju(4, [(0, 1), (1, 2), (2, 3), (3, 0)])) == 1  # one big cycle

count, comp = undirected_components(6, [(0, 1), (1, 2), (3, 4)])
assert count == 3 and comp[0] == comp[2] and comp[3] == comp[4] and comp[5] not in (comp[0], comp[3])
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <utility>
#include <vector>

class Kosaraju {
public:
    Kosaraju(int n, const std::vector<std::pair<int, int>>& edges)
        : adj_(n), radj_(n), seen_(n, false), comp_(n, -1) {
        for (const auto& e : edges) {
            adj_[e.first].push_back(e.second);
            radj_[e.second].push_back(e.first);
        }
        for (int s = 0; s < n; ++s)
            if (!seen_[s]) dfs1(s);
        for (auto it = order_.rbegin(); it != order_.rend(); ++it)
            if (comp_[*it] == -1) dfs2(*it, count_++);
    }

    int count() const { return count_; }
    int component(int v) const { return comp_[v]; }

private:
    std::vector<std::vector<int>> adj_, radj_;
    std::vector<bool> seen_;
    std::vector<int> comp_, order_;
    int count_ = 0;

    void dfs1(int u) {
        seen_[u] = true;
        for (int v : adj_[u])
            if (!seen_[v]) dfs1(v);
        order_.push_back(u);
    }

    void dfs2(int u, int label) {
        comp_[u] = label;
        for (int v : radj_[u])
            if (comp_[v] == -1) dfs2(v, label);
    }
};

int main() {
    Kosaraju k(7, {{0, 1}, {1, 2}, {2, 0}, {1, 3}, {3, 4}, {4, 5}, {5, 3}});
    assert(k.count() == 3);
    assert(k.component(0) == k.component(2) && k.component(3) == k.component(5));
    assert(k.component(0) != k.component(3) && k.component(6) != k.component(0));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Undirected components take O(V + E) time with DFS or BFS, or about O(E alpha(V)) with union-find. Kosaraju's algorithm runs two DFS passes and builds the reversed graph, each O(V + E), so it is O(V + E) overall, and it needs O(V + E) extra memory for the reversed graph. Tarjan's algorithm also runs in O(V + E) with a single pass and no reversed graph. Recursive implementations use stack depth up to V, so very large graphs need iterative versions to avoid recursion limits.

## Common Mistakes & Misconceptions
A common misconception is that a DFS from one vertex in a directed graph finds its SCC; it finds everything reachable, which can include vertices that cannot get back. Students also treat weakly connected components (connected when directions are ignored) as strongly connected ones. In Kosaraju's algorithm, typical bugs are running the second pass on the original graph instead of the reversed one, or processing vertices in increasing instead of decreasing finish order; both merge separate SCCs into one. Forgetting to start a new search from every unvisited vertex undercounts components in disconnected graphs. People assume a single vertex cannot be an SCC, but every vertex not on any cycle forms an SCC of size one. Another symptom is a RecursionError on large inputs because both passes recurse.

## Builds On
This concept builds on Depth-First Search. Counting undirected components is repeated DFS from unvisited vertices, and Kosaraju's algorithm uses DFS finish times in its first pass and a second DFS on the reversed graph, relying on the DFS property that a vertex finishes after everything reachable from it that was discovered during its visit. Tarjan's algorithm uses discovery times and the DFS tree directly.

## Leads To
The condensation graph of SCCs is a DAG, so it can be processed with topological sort, which is how 2-SAT problems, circular dependency reports in build tools and dead-code analysis in compilers work. Connected components underpin network reliability, image segmentation (flood fill) and clustering. Related ideas include bridges and articulation points (edges and vertices whose removal disconnects a graph), found with the same low-link technique as Tarjan's algorithm.

## Check Yourself
**Q1.** What is a strongly connected component?
**A1.** A maximal set of vertices in a directed graph where every vertex can reach every other along directed paths.
**Q2.** What are the two passes of Kosaraju's algorithm?
**A2.** A DFS that records finish order on the original graph, then DFS runs on the reversed graph in decreasing finish order.
**Q3.** What kind of graph do you get by shrinking each SCC to one node?
**A3.** A directed acyclic graph (the condensation).
