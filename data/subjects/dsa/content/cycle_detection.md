---
id: cycle_detection
name: "Cycle Detection"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 22.3 (Depth-first search, classification of edges, Lemma 22.11)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.1 (Cycle detection) and Section 4.2 (Directed cycle detection)"
---

## Overview
Cycle detection answers whether a graph contains a cycle, a path that starts and ends at the same vertex without reusing an edge. The question matters because many algorithms require acyclic input: a topological order exists only for a directed acyclic graph, a dependency system with a cycle can never be satisfied, a deadlock in an operating system is a cycle in a wait-for graph, and a spanning tree must avoid cycles. The method differs for undirected and directed graphs. In an undirected graph, depth-first search finds a cycle when it meets an already visited vertex that is not the parent it just came from. In a directed graph, DFS finds a cycle when it meets a vertex that is still on the current recursion path, which needs three states per vertex.

## Intuition
Imagine following a trail of one-way signs through a town while dropping breadcrumbs. If you ever step on your own breadcrumbs from the walk you are still on, the signs have led you in a loop. Breadcrumbs from an earlier walk that you already finished do not mean a loop: you just joined a road you explored before. That distinction between "on my current walk" and "explored earlier" is exactly why directed cycle detection needs a "currently active" mark in addition to "visited".

## How It Works
Undirected graphs with DFS. Run DFS and remember, for each vertex, the parent from which it was discovered. When scanning the neighbours of u, an unvisited neighbour is a tree edge and is explored. A visited neighbour other than the parent means there is a second route to it, so the graph has a cycle. The parent must be ignored because every undirected edge appears in both lists, so u always sees its parent again. With parallel edges (two edges between the same pair) the parent check needs edge ids rather than vertex ids.

Undirected graphs with union-find. Process the edges one by one with a disjoint set union. If both endpoints of an edge are already in the same set, adding the edge would close a cycle. This is how Kruskal's algorithm avoids cycles, and it works without building adjacency lists.

Directed graphs with three colours. Give every vertex a state: white (not yet visited), grey (visited and still on the recursion stack) and black (finished). DFS from u makes u grey, explores its neighbours, then makes u black. An edge from u to a grey vertex is a back edge to an ancestor on the current path, so there is a directed cycle. An edge to a black vertex is not a cycle, because that vertex's exploration is complete and cannot lead back to u. Using a plain visited flag would report false cycles in a graph like a diamond (0 -> 1, 0 -> 2, 1 -> 3, 2 -> 3).

Directed graphs with Kahn's algorithm. Repeatedly remove vertices of in-degree zero. If some vertices are never removed, they lie on a cycle or behind one.

Finding the cycle itself. Keep parent pointers during DFS. When a back edge u -> v is found, walk the parent pointers from u back to v to list the vertices of the cycle.

## Worked Example
Directed graph with edges 0 -> 1, 1 -> 2, 2 -> 0 and 2 -> 3.

```
  0 --> 1
  ^     |
  |     v
  +---- 2 --> 3
```

Start DFS at 0: 0 becomes grey. Go to 1: grey. Go to 2: grey. Vertex 2 has neighbour 0, which is grey, so 2 -> 0 is a back edge and the cycle is 0 -> 1 -> 2 -> 0. Now remove the edge 2 -> 0 and add 0 -> 2 instead. DFS from 0: 0 grey, 1 grey, 2 grey, 3 grey, then 3, 2 and 1 become black in turn. Back at 0, the edge 0 -> 2 leads to a black vertex, which is not a cycle, so the graph is acyclic. A simple visited flag would have wrongly reported a cycle at that point. In the undirected graph with edges 0-1, 1-2, 2-0, DFS from 0 reaches 1, then 2, and at 2 sees neighbour 0, which is visited and is not 2's parent (1), so there is a cycle.

## Code
```python
WHITE, GREY, BLACK = 0, 1, 2


def directed_cycle(n, edges):
    """Return one directed cycle as a list of vertices, or None."""
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
    color, parent = [WHITE] * n, [-1] * n

    def visit(u):
        color[u] = GREY
        for v in adj[u]:
            if color[v] == GREY:                    # back edge to the current path
                cycle, x = [v], u
                while x != v:
                    cycle.append(x)
                    x = parent[x]
                return cycle[:1] + cycle[1:][::-1]
            if color[v] == WHITE:
                parent[v] = u
                found = visit(v)
                if found:
                    return found
        color[u] = BLACK
        return None

    for s in range(n):
        if color[s] == WHITE:
            found = visit(s)
            if found:
                return found
    return None


def undirected_has_cycle(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = [False] * n
    for s in range(n):
        if seen[s]:
            continue
        seen[s] = True
        stack = [(s, -1)]
        while stack:
            u, par = stack.pop()
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append((v, u))
                elif v != par:
                    return True                     # visited and not the parent
    return False


def undirected_cycle_dsu(n, edges):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru == rv:
            return True
        parent[ru] = rv
    return False


assert directed_cycle(4, [(0, 1), (1, 2), (2, 0), (2, 3)]) == [0, 1, 2]
assert directed_cycle(4, [(0, 1), (1, 2), (0, 2), (2, 3)]) is None   # no false alarm
assert directed_cycle(4, [(0, 1), (0, 2), (1, 3), (2, 3)]) is None   # diamond
assert directed_cycle(1, [(0, 0)]) == [0]                             # self-loop
assert undirected_has_cycle(3, [(0, 1), (1, 2), (2, 0)])
assert not undirected_has_cycle(4, [(0, 1), (1, 2), (1, 3)])         # a tree
assert undirected_cycle_dsu(3, [(0, 1), (1, 2), (2, 0)])
assert not undirected_cycle_dsu(4, [(0, 1), (2, 3)])
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <utility>
#include <vector>

enum Color { WHITE, GREY, BLACK };

bool visit(int u, const std::vector<std::vector<int>>& adj, std::vector<Color>& color) {
    color[u] = GREY;
    for (int v : adj[u]) {
        if (color[v] == GREY) return true;                 // back edge
        if (color[v] == WHITE && visit(v, adj, color)) return true;
    }
    color[u] = BLACK;
    return false;
}

bool hasDirectedCycle(int n, const std::vector<std::pair<int, int>>& edges) {
    std::vector<std::vector<int>> adj(n);
    for (const auto& e : edges) adj[e.first].push_back(e.second);
    std::vector<Color> color(n, WHITE);
    for (int s = 0; s < n; ++s)
        if (color[s] == WHITE && visit(s, adj, color)) return true;
    return false;
}

int main() {
    assert(hasDirectedCycle(4, {{0, 1}, {1, 2}, {2, 0}, {2, 3}}));
    assert(!hasDirectedCycle(4, {{0, 1}, {0, 2}, {1, 3}, {2, 3}}));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
DFS-based detection, directed or undirected, takes O(V + E) time and O(V) extra space for the colour or visited array and the stack. The union-find method processes E edges with nearly constant amortised cost each, so O(E alpha(V)), and needs O(V) space. Kahn's algorithm also runs in O(V + E). The DFS can stop as soon as the first cycle is found, so on graphs with an early cycle it finishes much faster. Listing every cycle in a graph is a much harder problem, since there can be exponentially many.

## Common Mistakes & Misconceptions
The most common bug in directed graphs is using a single visited flag, which reports a cycle whenever two paths meet at the same vertex, as in a diamond; only an edge to a vertex still on the current path (grey) means a cycle. In undirected graphs the opposite mistake is forgetting to skip the parent, so every graph with at least one edge "has a cycle". Students apply the undirected method to a directed graph or the reverse. Forgetting to reset a vertex from grey to black after exploring it makes later branches see false back edges. Only starting DFS from vertex 0 misses cycles in other components. In recursive code on large graphs, the recursion limit can be hit before any cycle is found; an iterative version avoids it. Self-loops (u -> u) are cycles and should be handled explicitly.

## Builds On
This concept builds on Depth-First Search. The parent-tracking rule for undirected graphs and the grey/black colouring for directed graphs are both refinements of the DFS visit order, and they rely on the DFS fact that a vertex discovered from u finishes before u. The classification of edges as tree, back, forward and cross edges, which DFS introduces, is the theory behind the rule that only back edges mean a cycle.

## Leads To
Cycle detection is the check that decides whether a topological order exists, so it guards build systems, package managers and Cognexa's own prerequisite graph (the admin edge editor rejects any edge that would create a cycle). It is used to detect deadlocks in wait-for graphs, to keep spanning trees acyclic in Kruskal's algorithm through union-find, and in negative-cycle detection, where Bellman-Ford finds cycles whose total weight is below zero.

## Check Yourself
**Q1.** In a directed DFS, which edge indicates a cycle?
**A1.** An edge to a grey vertex, one that is still on the current recursion path (a back edge).
**Q2.** Why must the parent be ignored in undirected cycle detection?
**A2.** Because each undirected edge appears in both lists, so a vertex always sees its parent as a visited neighbour.
**Q3.** How does union-find detect a cycle in an undirected graph?
**A3.** An edge whose endpoints are already in the same set would close a cycle.
