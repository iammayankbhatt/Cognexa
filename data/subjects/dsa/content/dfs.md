---
id: dfs
name: "Depth-First Search"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 22.3 (Depth-first search)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.1 (Depth-first search) and Section 4.2"
---

## Overview
Depth-first search (DFS) explores a graph by going as deep as possible along one path before backing up. From the current vertex it picks an unvisited neighbour and moves there, repeating until it reaches a vertex with no unvisited neighbours, and then it backtracks to the most recent vertex that still has an unexplored neighbour. It is implemented with recursion (the call stack) or with an explicit stack, and a visited marker prevents loops in graphs with cycles. DFS does not give shortest paths, but the order in which it enters and leaves vertices reveals the structure of the graph, which makes it the foundation of topological sorting, cycle detection, connected components, strongly connected components and many backtracking solutions.

## Intuition
Picture exploring a maze with a ball of string. You walk down a corridor, and at each junction you take the first unexplored passage. When you hit a dead end or a place you have already been, you wind the string back to the last junction that still has unexplored passages and try one of those. You finish a whole branch before returning to start another. That backing-up behaviour is what the call stack of a recursive function does automatically.

## How It Works
Recursive version. Keep a visited set. dfs(u): mark u visited, then for each neighbour v of u, if v is not visited, call dfs(v). When dfs(u) has looked at all neighbours it returns, which is the backtracking step. Starting from s visits exactly the vertices reachable from s.

Iterative version. Push the start vertex on a stack. Repeatedly pop a vertex, skip it if it is already visited, otherwise mark it, record it, and push its unvisited neighbours (in reverse order if you want the same order as the recursive version). The stack replaces the call stack and avoids recursion limits on deep graphs.

Timestamps. Record a discovery time when a vertex is first entered and a finish time when all its neighbours have been explored. The intervals [discovery, finish] of any two vertices are either nested or disjoint. If v is discovered while u is being explored, then v finishes before u, so [d(v), f(v)] lies inside [d(u), f(u)]. This parenthesis structure is what many DFS algorithms exploit.

Edge types in a directed graph. Tree edges lead to a newly discovered vertex. Back edges go from a vertex to one of its ancestors that is still being explored, which means a cycle. Forward edges lead to a finished descendant, and cross edges lead to a finished vertex in another branch. In an undirected graph every non-tree edge is a back edge, so any non-tree edge means a cycle.

Whole-graph DFS. To cover disconnected graphs, loop over all vertices and start a new DFS from each unvisited one. The set of vertices visited by each start forms one tree of the DFS forest.

Contrast with BFS. DFS goes deep and uses a stack, BFS goes wide and uses a queue. DFS uses memory proportional to the path depth, which can be much smaller than the BFS frontier, but it does not find shortest paths.

## Worked Example
Graph with edges 0-1, 0-2, 1-3, 2-3, 3-4, with adjacency lists 0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2, 4], 4: [3]. Start at 0.

Enter 0 (time 1). Its first neighbour 1 is unvisited, so enter 1 (time 2). Neighbour 0 is visited; neighbour 3 is new, so enter 3 (time 3). From 3, neighbour 1 is visited, neighbour 2 is new, so enter 2 (time 4). Vertex 2 has neighbours 0 and 3, both visited, so finish 2 (time 5). Back at 3, the next neighbour is 4, so enter 4 (time 6), finish 4 (time 7). Vertex 3 is done, finish 3 (time 8), then finish 1 (time 9), and at 0 the neighbour 2 is already visited, so finish 0 (time 10). The visiting order is 0, 1, 3, 2, 4. The tree edges are 0-1, 1-3, 3-2 and 3-4, and the edge 2-0 is a back edge that closes the cycle 0-1-3-2.

## Code
```python
def dfs_recursive(adj, start):
    visited, order = set(), []

    def visit(u):
        visited.add(u)
        order.append(u)
        for v in adj[u]:
            if v not in visited:
                visit(v)

    visit(start)
    return order


def dfs_iterative(adj, start):
    visited, order, stack = set(), [], [start]
    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        order.append(u)
        for v in reversed(adj[u]):             # reversed, to match the recursive order
            if v not in visited:
                stack.append(v)
    return order


def dfs_times(adj):
    n, clock = len(adj), [0]
    disc, fin = [0] * n, [0] * n

    def visit(u):
        clock[0] += 1
        disc[u] = clock[0]
        for v in adj[u]:
            if disc[v] == 0:
                visit(v)
        clock[0] += 1
        fin[u] = clock[0]

    for s in range(n):
        if disc[s] == 0:
            visit(s)
    return disc, fin


def components(adj):
    seen, comps = set(), []
    for s in range(len(adj)):
        if s not in seen:
            comp = dfs_iterative(adj, s)
            seen.update(comp)
            comps.append(sorted(comp))
    return comps


adj = [[1, 2], [0, 3], [0, 3], [1, 2, 4], [3]]
assert dfs_recursive(adj, 0) == [0, 1, 3, 2, 4]
assert dfs_iterative(adj, 0) == [0, 1, 3, 2, 4]
disc, fin = dfs_times(adj)
assert disc == [1, 2, 4, 3, 6] and fin == [10, 9, 5, 8, 7]
for u in range(5):                                          # intervals nest or are disjoint
    for v in range(5):
        if u != v:
            nested = disc[u] < disc[v] < fin[v] < fin[u]
            disjoint = fin[u] < disc[v] or fin[v] < disc[u]
            assert nested or disjoint or (disc[v] < disc[u] < fin[u] < fin[v])
assert components([[1], [0], [3], [2], []]) == [[0, 1], [2, 3], [4]]
deep = [[i + 1] if i < 5000 else [] for i in range(5001)]   # a long chain: iterative has no limit
assert len(dfs_iterative(deep, 0)) == 5001
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <stack>
#include <vector>

void dfsRecursive(const std::vector<std::vector<int>>& adj, int u, std::vector<bool>& seen,
                  std::vector<int>& order) {
    seen[u] = true;
    order.push_back(u);
    for (int v : adj[u])
        if (!seen[v]) dfsRecursive(adj, v, seen, order);
}

std::vector<int> dfsIterative(const std::vector<std::vector<int>>& adj, int start) {
    std::vector<bool> seen(adj.size(), false);
    std::vector<int> order;
    std::stack<int> st;
    st.push(start);
    while (!st.empty()) {
        int u = st.top();
        st.pop();
        if (seen[u]) continue;
        seen[u] = true;
        order.push_back(u);
        for (auto it = adj[u].rbegin(); it != adj[u].rend(); ++it)
            if (!seen[*it]) st.push(*it);
    }
    return order;
}

int main() {
    std::vector<std::vector<int>> adj = {{1, 2}, {0, 3}, {0, 3}, {1, 2, 4}, {3}};
    std::vector<bool> seen(adj.size(), false);
    std::vector<int> order;
    dfsRecursive(adj, 0, seen, order);
    assert((order == std::vector<int>{0, 1, 3, 2, 4}));
    assert(dfsIterative(adj, 0) == order);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
DFS visits each vertex once and scans each adjacency list once, so it takes O(V + E) time with an adjacency list and O(V squared) with a matrix. The extra space is the visited set plus the stack or recursion depth, which is O(V) in the worst case (a long path), and often much less than the frontier BFS would hold. Recursive DFS on a very deep graph can exceed the recursion limit (about 1000 frames by default in Python), so use an explicit stack when the depth may be large. DFS finds a path, not the shortest path.

## Common Mistakes & Misconceptions
The usual crash is a RecursionError or stack overflow on a long chain or large grid, because the recursion depth equals the path length; the cure is an iterative version or a larger limit. Forgetting the visited set makes DFS loop forever on any graph with a cycle, including every undirected graph (each edge leads back). Students mark vertices visited when they push them in the iterative version and then get an order that differs from the recursive one, or mark nothing at pop time and process duplicates. People expect DFS to find the shortest path to a vertex; the first path it finds can be very long. In directed graphs, confusing a cross or forward edge with a back edge leads to false cycle reports, because only an edge to a vertex that is still on the current path means a cycle. Neighbour order changes the visiting order but not the set of reachable vertices.

## Builds On
This concept builds on Graph Basics & Representations, because DFS walks the neighbours of each vertex, and the adjacency-list form is what gives the O(V + E) bound. It builds on Recursion: the natural definition "visit u, then run the same search from each unvisited neighbour" is recursive, the base case is a vertex with nothing new to visit, and the call stack is what remembers where to backtrack. It also builds on Stack (ADT & implementations), since the explicit-stack version replaces the call stack with an ordinary stack whose last-in first-out order gives the depth-first behaviour.

## Leads To
Topological Sort orders a directed acyclic graph by decreasing finish time. Cycle Detection looks for back edges found during the search. Connected & Strongly Connected Components use repeated DFS runs (Kosaraju and Tarjan algorithms) and finish times to split a graph into pieces. DFS is also the engine of backtracking, maze solving, finding bridges and articulation points, and tree traversals.

## Check Yourself
**Q1.** Which data structure (explicit or implicit) drives DFS?
**A1.** A stack, either the call stack of recursion or an explicit one.
**Q2.** Why does DFS need a visited set?
**A2.** Without it the search would revisit vertices and loop forever in a graph with cycles.
**Q3.** Does DFS find the shortest path between two vertices?
**A3.** No, it finds some path; BFS finds a fewest-edges path in unweighted graphs.
