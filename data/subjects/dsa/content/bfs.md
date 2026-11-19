---
id: bfs
name: "Breadth-First Search"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 22.2 (Breadth-first search)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.1 (Breadth-first search, shortest paths)"
---

## Overview
Breadth-first search (BFS) explores a graph in layers: first the start vertex, then all vertices one edge away, then all vertices two edges away, and so on. It uses a queue so that vertices discovered earlier are expanded earlier, and a visited marker so that no vertex is processed twice even when the graph has cycles. The main reason to use BFS is that, in an unweighted graph, the first time it reaches a vertex is along a path with the fewest edges, so BFS computes shortest path lengths from the start. It is also used to test reachability, count connected components, find the shortest route through a maze or a word ladder, and spread a signal level by level.

## Intuition
Drop a pebble into a still pond. The ripple reaches all points one metre away at the same moment, then all points two metres away, and so on outward in rings. BFS is that ripple moving through the graph: every vertex at distance 1 is reached before any vertex at distance 2. Because the ripple never reaches a place sooner than the shortest route allows, the time a vertex is first reached tells you its distance.

## How It Works
Setup. Give every vertex a distance of "unknown" (for example -1) and put the start vertex s in a queue with distance 0 and mark it visited. Visited must be marked when a vertex is added to the queue, not when it is removed, otherwise the same vertex can be queued many times.

Main loop. While the queue is not empty, remove the front vertex u. For each neighbour v of u that has not been visited, mark v visited, set dist[v] = dist[u] + 1, record parent[v] = u and append v to the queue. When the queue is empty every vertex reachable from s has been processed.

Why distances are correct. The queue always holds vertices in non-decreasing order of distance, with at most two distinct distance values (d and d + 1) at once. A vertex's first discovery happens from a vertex of minimal distance, so no shorter path can exist. This argument needs all edges to have the same cost, so BFS gives shortest paths only for unweighted graphs (or graphs where every edge counts as one step).

Recovering the path. Follow parent pointers from the target back to the start and reverse the result. The parent pointers form a BFS tree rooted at the start.

Disconnected graphs. A single BFS reaches only the component of the start. To visit everything, run BFS from every vertex that is still unvisited, and count how many runs are needed to get the number of connected components.

Grids. A maze or grid is a graph where each cell is a vertex and its up, down, left and right neighbours are adjacent, so BFS from the start cell finds the shortest path length in steps.

## Worked Example
Graph with edges 0-1, 0-2, 1-3, 2-3, 3-4. Start at 0.

```
    0
   / \
  1   2
   \ /
    3
    |
    4
```

Queue = [0], dist[0] = 0. Remove 0: neighbours 1 and 2 are new, so dist[1] = dist[2] = 1, parents 0, queue = [1, 2]. Remove 1: neighbour 0 is visited, neighbour 3 is new with dist 2 and parent 1, queue = [2, 3]. Remove 2: neighbours 0 and 3 are both visited, nothing is added. Remove 3: neighbours 1 and 2 are visited, 4 is new with dist 3 and parent 3, queue = [4]. Remove 4: no new neighbours. The visiting order is 0, 1, 2, 3, 4, the distances are [0, 1, 1, 2, 3], and the shortest path to 4 is 0, 1, 3, 4 (found through the parents 4 -> 3 -> 1 -> 0). Vertex 3 is reachable by two paths of equal length, but only the first one found is recorded.

## Code
```python
from collections import deque


def bfs(adj, start):
    n = len(adj)
    dist = [-1] * n
    parent = [-1] * n
    dist[start] = 0                       # visited is the same as dist != -1
    queue = deque([start])
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in adj[u]:
            if dist[v] == -1:             # mark on discovery, not on removal
                dist[v] = dist[u] + 1
                parent[v] = u
                queue.append(v)
    return order, dist, parent


def path_to(parent, target):
    path = []
    while target != -1:
        path.append(target)
        target = parent[target]
    return path[::-1]


def count_components(adj):
    seen, count = [False] * len(adj), 0
    for s in range(len(adj)):
        if not seen[s]:
            count += 1
            order, _, _ = bfs(adj, s)
            for v in order:
                seen[v] = True
    return count


def grid_shortest(grid, start, goal):          # '#' is a wall, '.' is open
    rows, cols = len(grid), len(grid[0])
    dist = {start: 0}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        if (r, c) == goal:
            return dist[(r, c)]
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                queue.append((nr, nc))
    return -1


adj = [[1, 2], [0, 3], [0, 3], [1, 2, 4], [3]]
order, dist, parent = bfs(adj, 0)
assert order == [0, 1, 2, 3, 4] and dist == [0, 1, 1, 2, 3]
assert path_to(parent, 4) == [0, 1, 3, 4]
assert count_components([[1], [0], [3], [2], []]) == 3
maze = ["..#.", ".##.", "...."]
assert grid_shortest(maze, (0, 0), (0, 3)) == 7
assert grid_shortest(["..#", "###", "..."], (0, 0), (2, 2)) == -1
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <queue>
#include <vector>

std::vector<int> bfsDistances(const std::vector<std::vector<int>>& adj, int start) {
    std::vector<int> dist(adj.size(), -1);
    std::queue<int> q;
    dist[start] = 0;
    q.push(start);
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int v : adj[u]) {
            if (dist[v] == -1) {          // mark when discovered
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
    return dist;
}

int main() {
    std::vector<std::vector<int>> adj = {{1, 2}, {0, 3}, {0, 3}, {1, 2, 4}, {3}};
    std::vector<int> d = bfsDistances(adj, 0);
    assert((d == std::vector<int>{0, 1, 1, 2, 3}));
    std::vector<std::vector<int>> split = {{1}, {0}, {3}, {2}};
    std::vector<int> e = bfsDistances(split, 0);
    assert(e[2] == -1 && e[3] == -1);     // unreachable vertices keep -1
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
BFS visits each vertex once and examines each adjacency entry once, so it runs in O(V + E) time with an adjacency list (O(V squared) with a matrix). The queue and the distance array need O(V) extra space; in the worst case the queue holds a whole layer, which can be nearly all vertices. Because it keeps an entire frontier in memory, BFS can use far more memory than depth-first search on wide graphs. The shortest-path property holds only for unweighted edges; with varying weights you need Dijkstra's algorithm.

## Common Mistakes & Misconceptions
The classic mistake is marking a vertex visited when it is removed from the queue instead of when it is added, so the same vertex enters the queue many times and the work blows up or the output has duplicates. Another is using a stack instead of a queue, which is not BFS and gives wrong distances. Students use Python's list.pop(0) as the queue, which makes each removal O(n) and the whole search slow; collections.deque fixes this. Forgetting to handle disconnected graphs leaves vertices with distance -1 that are then used as if they were real distances. A conceptual error is applying BFS to weighted graphs and expecting cheapest paths: it finds paths with fewest edges, not least total weight. Finally, people forget that BFS needs the visited check even in a tree-like graph if edges are undirected, because a child sees its parent as a neighbour.

## Builds On
This concept builds on Graph Basics & Representations. BFS is written against an adjacency list (neighbour lookup by vertex index), and its O(V + E) running time depends on that representation: with an adjacency matrix each vertex would cost O(V) to scan. The vocabulary of neighbours, paths, connected components and directed versus undirected edges comes from there too. It also builds on Queue (ADT & implementations): the first-in first-out discipline is exactly what orders the exploration layer by layer, and an O(1) enqueue and dequeue (such as a deque or circular buffer) is needed to reach the linear time bound.

## Leads To
Dijkstra's Shortest Path replaces the plain queue with a priority queue so that edges with different weights are handled, and can be seen as BFS generalised to weights. BFS is also the base of shortest-path problems in grids and word ladders, bipartite checking by two-colouring layers, level-order traversal of trees, and the search step of maximum-flow algorithms such as Edmonds-Karp.

## Check Yourself
**Q1.** Which data structure does BFS use to decide the next vertex?
**A1.** A queue.
**Q2.** What does BFS compute in an unweighted graph?
**A2.** The fewest-edges (shortest path) distance from the start to every reachable vertex.
**Q3.** When should a vertex be marked visited?
**A3.** When it is first discovered and added to the queue.
