---
id: topological_sort
name: "Topological Sort"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 22.4 (Topological sort)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.2 (Directed acyclic graphs and topological order)"
---

## Overview
A topological sort of a directed graph is a linear ordering of its vertices in which every edge u -> v puts u before v. It exists exactly when the graph has no directed cycle, that is, when it is a directed acyclic graph (DAG). Topological order answers the question "in what order can I do these tasks so that every task comes after the things it depends on?" Typical uses are scheduling a build, ordering course prerequisites, resolving package dependencies, and evaluating spreadsheet cells. Two standard algorithms compute it in O(V + E): one based on depth-first search finish times and one (Kahn's algorithm) that repeatedly removes vertices with no incoming edges.

## Intuition
Getting dressed is a topological problem: socks before shoes, trousers before belt, shirt before tie. Many valid orders exist, but any order that puts shoes before socks is wrong. If the rules were circular ("socks after shoes, shoes after socks") there would be no valid order at all, which is why a cycle makes topological sorting impossible. Both algorithms find an order that respects every "must come before" rule, or discover a cycle.

## How It Works
Edge direction. An edge u -> v means u must come before v. In this project's concept graph, an edge A -> B in PREREQUISITE_OF means A must be learned before B, so a topological order of that graph is a valid study order.

DFS-based method. Run a depth-first search over the whole graph. When a vertex finishes (all its descendants are done), push it onto a list. The reverse of this finish order is a topological order. Why it works: for an edge u -> v, v finishes before u (unless there is a cycle), so after reversing, u comes first. To detect a cycle during this DFS, track the vertices currently on the recursion path; meeting one of them again means a back edge and a cycle.

Kahn's algorithm. Compute the in-degree (number of incoming edges) of every vertex. Put all vertices with in-degree 0 in a queue; these have no unmet dependencies. Repeatedly remove a vertex u from the queue, append it to the output, and for each edge u -> v decrease the in-degree of v by one; when it reaches 0, push v. If the output contains fewer than V vertices at the end, the leftover vertices lie on or behind a cycle, so no topological order exists.

Non-uniqueness. A DAG usually has many valid orders. If you need a specific one, for example alphabetical among ties, use a priority queue instead of a plain queue in Kahn's algorithm. The order is unique only if the DAG contains a path through all vertices.

Related uses. Once vertices are in topological order, the longest path in a DAG, the number of paths and shortest paths with any edge weights can be computed in one pass in O(V + E), which is why dynamic programming over a DAG relies on this order.

## Worked Example
Tasks 0 to 4 with edges 0 -> 1, 0 -> 2, 1 -> 3, 2 -> 3, 3 -> 4.

```
    0
   / \
  1   2
   \ /
    3
    |
    4
```

Kahn's algorithm: in-degrees are [0, 1, 1, 2, 1], so only 0 starts in the queue. Remove 0 and output it; the in-degree of 1 and 2 drops to 0, so both are queued. Remove 1: the in-degree of 3 drops from 2 to 1. Remove 2: it drops to 0, so 3 is queued. Remove 3: the in-degree of 4 becomes 0, so 4 is queued. Remove 4. Output: 0, 1, 2, 3, 4. A DFS from 0 finishes the vertices in the order 4, 3, 1, 2, 0, and reversing gives 0, 2, 1, 3, 4, a different but equally valid order. If an extra edge 4 -> 0 is added, every vertex always has an incoming edge from the cycle, no vertex ever reaches in-degree 0 at the start, the output is empty (fewer than 5 vertices), and the algorithm reports a cycle.

## Code
```python
from collections import deque


def topo_kahn(n, edges):
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for u, v in edges:
        adj[u].append(v)
        indeg[v] += 1
    queue = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return order if len(order) == n else None        # None means there is a cycle


def topo_dfs(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
    state = [0] * n                                   # 0 new, 1 on the current path, 2 done
    finished = []

    def visit(u):
        state[u] = 1
        for v in adj[u]:
            if state[v] == 1:
                return False                          # back edge: cycle
            if state[v] == 0 and not visit(v):
                return False
        state[u] = 2
        finished.append(u)
        return True

    for s in range(n):
        if state[s] == 0 and not visit(s):
            return None
    return finished[::-1]


def is_topological(order, edges):
    pos = {v: i for i, v in enumerate(order)}
    return all(pos[u] < pos[v] for u, v in edges)


edges = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)]
assert topo_kahn(5, edges) == [0, 1, 2, 3, 4]
assert topo_dfs(5, edges) == [0, 2, 1, 3, 4]
assert is_topological(topo_kahn(5, edges), edges)
assert is_topological(topo_dfs(5, edges), edges)
cyclic = edges + [(4, 0)]
assert topo_kahn(5, cyclic) is None and topo_dfs(5, cyclic) is None
assert topo_kahn(3, []) == [0, 1, 2]                  # no edges: any order works

import random

random.seed(4)
for _ in range(100):                                  # random DAGs: edges only go from lower to higher id
    n = random.randint(1, 12)
    es = [(u, v) for u in range(n) for v in range(u + 1, n) if random.random() < 0.3]
    random.shuffle(es)
    perm = list(range(n))
    random.shuffle(perm)                              # relabel so ids are not already sorted
    es2 = [(perm[u], perm[v]) for u, v in es]
    assert is_topological(topo_kahn(n, es2), es2)
    assert is_topological(topo_dfs(n, es2), es2)
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <queue>
#include <utility>
#include <vector>

// Returns an empty vector when the graph has a cycle.
std::vector<int> topoKahn(int n, const std::vector<std::pair<int, int>>& edges) {
    std::vector<std::vector<int>> adj(n);
    std::vector<int> indeg(n, 0);
    for (const auto& e : edges) {
        adj[e.first].push_back(e.second);
        ++indeg[e.second];
    }
    std::queue<int> q;
    for (int i = 0; i < n; ++i)
        if (indeg[i] == 0) q.push(i);
    std::vector<int> order;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        order.push_back(u);
        for (int v : adj[u])
            if (--indeg[v] == 0) q.push(v);
    }
    if (static_cast<int>(order.size()) != n) order.clear();
    return order;
}

int main() {
    std::vector<std::pair<int, int>> edges = {{0, 1}, {0, 2}, {1, 3}, {2, 3}, {3, 4}};
    assert((topoKahn(5, edges) == std::vector<int>{0, 1, 2, 3, 4}));
    edges.push_back({4, 0});
    assert(topoKahn(5, edges).empty());
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Both algorithms take O(V + E) time: each vertex is processed once and each edge is examined once (to compute in-degrees and to decrement them in Kahn's algorithm, or to follow the edge in DFS). The extra space is O(V) for the in-degree array and queue, or for the state array and the recursion stack. Producing a specific order such as the lexicographically smallest with a priority queue costs O(V log V + E). The ordering is not unique, and a graph with a cycle has no topological order at all.

## Common Mistakes & Misconceptions
A common error is forgetting to reverse the finish order in the DFS method, which produces an order where every dependency comes after its dependent. Another is applying topological sort to an undirected graph or a graph with cycles and not checking the result: the DFS method without cycle detection quietly returns an invalid order for a cyclic graph, and Kahn's returns fewer than V vertices. Students assume the answer is unique and write tests that compare to one fixed list, which fails with another valid order. Reading the edge direction backwards (treating u -> v as "v before u") gives the reversed ordering. People also confuse topological order with sorting by value: the order depends only on the edges, so disconnected vertices can appear anywhere. For very deep graphs, recursive DFS can hit the recursion limit, and Kahn's avoids that.

## Builds On
This concept builds on Depth-First Search. The DFS-based method needs the finish times that DFS produces, the idea that a vertex finishes only after everything it points to has finished, and the three-state marking (new, on the current path, done) that identifies back edges and therefore cycles. Understanding why a DFS back edge means a cycle is exactly what shows when a topological order cannot exist.

## Leads To
Dynamic programming on DAGs processes states in topological order so that every subproblem is solved before the ones that depend on it, a link to Dynamic Programming (memoization & tabulation). Topological order is also used for build systems and task schedulers, for course planning, for evaluating formulas in dependency order, and for finding the longest and shortest paths in a DAG in linear time. In Cognexa itself, the prerequisite graph must stay a DAG so a study order always exists.

## Check Yourself
**Q1.** When does a topological order exist?
**A1.** Exactly when the directed graph has no cycle (it is a DAG).
**Q2.** How does Kahn's algorithm detect a cycle?
**A2.** If the output has fewer vertices than the graph, some vertices never reached in-degree 0, so a cycle exists.
**Q3.** Is a topological order unique?
**A3.** Not in general; many DAGs have several valid orders.
