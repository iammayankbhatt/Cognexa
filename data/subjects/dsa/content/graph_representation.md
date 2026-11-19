---
id: graph_representation
name: "Graph Basics & Representations"
cluster: graphs
reviewed: false
sources:
  - "CLRS, Section 22.1 (Representations of graphs) and Appendix B.4 (Graphs)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 4.1 (Undirected Graphs) and Section 4.2 (Directed Graphs)"
---

## Overview
A graph is a set of vertices (also called nodes) joined by edges. Where a tree has exactly one path between any two nodes, a graph can have many paths, cycles, or no path at all, which makes it the right model for roads, social networks, web links, dependencies and circuits. Edges may be undirected (a friendship) or directed (a one-way street, a prerequisite), and may carry a weight (a distance or cost). Before any graph algorithm can run, the graph has to be stored in memory, and the two standard choices, the adjacency list and the adjacency matrix, differ in memory use and in which questions they answer fast.

## Intuition
Think of a city map. You can describe it as a list: for every intersection, write the streets leaving it ("from A you can go to B and C"). That is an adjacency list. Or you can draw a big table with every intersection as both a row and a column and tick the cell when there is a street between the two. That is an adjacency matrix. The list is short when the city has few streets per intersection and the table answers "is there a street between A and F?" at a glance, but it must reserve a cell for every pair of intersections even though most pairs are not connected.

## How It Works
Vocabulary. A graph G = (V, E) has V vertices and E edges. In an undirected graph an edge {u, v} connects both ways, and in a directed graph an edge (u, v) goes only from u to v. Two vertices joined by an edge are adjacent (neighbours). The degree of a vertex is its number of incident edges; in a directed graph it splits into in-degree and out-degree. A path is a sequence of vertices joined by edges, a cycle is a path that returns to its start, and a graph is connected if every vertex can be reached from every other. A simple graph has no self-loops or repeated edges. A graph with E close to V squared is dense and one with E close to V is sparse. A tree is a connected acyclic undirected graph.

Adjacency list. Keep an array (or hash map) of size V where entry u holds the list of neighbours of u. For a weighted graph each entry stores pairs (neighbour, weight). An undirected edge {u, v} is stored twice, once in each list. Memory is O(V + E). Listing the neighbours of u takes time proportional to its degree, and testing whether (u, v) is an edge takes O(degree of u) unless the neighbours are in a hash set.

Adjacency matrix. Keep a V by V table where cell [u][v] is 1 (or the weight) if the edge exists and 0 (or infinity) otherwise. Memory is O(V squared) regardless of E. Testing an edge is O(1), but listing the neighbours of u takes O(V) because you must scan the whole row. An undirected graph gives a symmetric matrix.

Edge list. A plain list of (u, v, w) triples is the most compact form and is what some algorithms (Kruskal's, Bellman-Ford) consume directly, but neighbour lookup is slow.

Choosing. Most real graphs are sparse, so the adjacency list is the default because traversals then cost O(V + E). Use a matrix when the graph is dense, V is small, or constant-time edge lookup matters, as in Floyd-Warshall.

## Worked Example
Consider an undirected graph with vertices 0, 1, 2, 3 and edges 0-1, 0-2, 1-2, 2-3.

```
    0 --- 1
     \   /
      \ /
       2 --- 3
```

Adjacency list: 0: [1, 2]; 1: [0, 2]; 2: [0, 1, 3]; 3: [2]. The sum of the list lengths is 8, which is twice the number of edges (4) because each undirected edge appears twice. Adjacency matrix: row 0 is [0, 1, 1, 0], row 1 is [1, 0, 1, 0], row 2 is [1, 1, 0, 1], row 3 is [0, 0, 1, 0], and it is symmetric. The degree of vertex 2 is 3. Is there an edge 1-3? The matrix cell [1][3] is 0 in one step, whereas the list needs a scan of the two entries in list 1. Vertex 3 has a single neighbour, so adding a directed edge 3 -> 0 would add only one entry to list 3.

## Code
```python
from collections import defaultdict


class Graph:
    def __init__(self, n, directed=False):
        self.n = n
        self.directed = directed
        self.adj = [[] for _ in range(n)]           # adjacency list of (neighbour, weight)

    def add_edge(self, u, v, w=1):
        self.adj[u].append((v, w))
        if not self.directed:
            self.adj[v].append((u, w))

    def neighbors(self, u):
        return [v for v, _ in self.adj[u]]

    def degree(self, u):
        return len(self.adj[u])

    def has_edge(self, u, v):
        return any(x == v for x, _ in self.adj[u])

    def edge_count(self):
        total = sum(len(a) for a in self.adj)
        return total if self.directed else total // 2

    def to_matrix(self, absent=0):
        m = [[absent] * self.n for _ in range(self.n)]
        for u in range(self.n):
            for v, w in self.adj[u]:
                m[u][v] = w
        return m


g = Graph(4)
for u, v in [(0, 1), (0, 2), (1, 2), (2, 3)]:
    g.add_edge(u, v)
assert g.neighbors(2) == [0, 1, 3]
assert g.degree(2) == 3 and g.edge_count() == 4
assert g.has_edge(1, 2) and not g.has_edge(1, 3)
m = g.to_matrix()
assert m == [[0, 1, 1, 0], [1, 0, 1, 0], [1, 1, 0, 1], [0, 0, 1, 0]]
assert all(m[i][j] == m[j][i] for i in range(4) for j in range(4))   # undirected is symmetric

d = Graph(3, directed=True)
d.add_edge(0, 1, 5)
d.add_edge(1, 2, 7)
assert d.has_edge(0, 1) and not d.has_edge(1, 0)
assert d.edge_count() == 2 and d.to_matrix(float("inf"))[0][1] == 5

# build from an edge list with labels using a dictionary
labels = defaultdict(list)
for a, b in [("A", "B"), ("A", "C"), ("B", "C")]:
    labels[a].append(b)
    labels[b].append(a)
assert sorted(labels["C"]) == ["A", "B"]
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <utility>
#include <vector>

class Graph {
public:
    Graph(int n, bool directed = false) : adj_(n), directed_(directed) {}

    void addEdge(int u, int v, int w = 1) {
        adj_[u].push_back({v, w});
        if (!directed_) adj_[v].push_back({u, w});
    }

    int degree(int u) const { return static_cast<int>(adj_[u].size()); }

    bool hasEdge(int u, int v) const {
        for (const auto& e : adj_[u])
            if (e.first == v) return true;
        return false;
    }

    int edgeCount() const {
        int total = 0;
        for (const auto& a : adj_) total += static_cast<int>(a.size());
        return directed_ ? total : total / 2;
    }

    std::vector<std::vector<int>> toMatrix() const {
        std::size_t n = adj_.size();
        std::vector<std::vector<int>> m(n, std::vector<int>(n, 0));
        for (std::size_t u = 0; u < n; ++u)
            for (const auto& e : adj_[u]) m[u][e.first] = e.second;
        return m;
    }

private:
    std::vector<std::vector<std::pair<int, int>>> adj_;
    bool directed_;
};

int main() {
    Graph g(4);
    g.addEdge(0, 1);
    g.addEdge(0, 2);
    g.addEdge(1, 2);
    g.addEdge(2, 3);
    assert(g.degree(2) == 3 && g.edgeCount() == 4);
    assert(g.hasEdge(1, 2) && !g.hasEdge(1, 3));
    auto m = g.toMatrix();
    assert(m[2][3] == 1 && m[3][2] == 1 && m[0][3] == 0);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
An adjacency list uses O(V + E) memory and lets a full traversal run in O(V + E); listing neighbours of u costs O(deg(u)), and checking one edge costs O(deg(u)) (O(1) average with a hash set per vertex). An adjacency matrix uses O(V squared) memory; it checks an edge in O(1) but listing neighbours costs O(V), and a full traversal costs O(V squared). Adding an edge is O(1) in both. Removing an edge is O(deg(u)) in a list and O(1) in a matrix. For a graph with a million vertices and four million edges the list needs a few million entries while a matrix would need a trillion cells, which is why sparse graphs always use lists.

## Common Mistakes & Misconceptions
A frequent bug is adding an undirected edge in only one direction, which makes a traversal miss vertices that "should" be reachable. The opposite, storing a directed graph as if it were undirected, creates paths that do not exist. Students use an adjacency matrix for a large sparse graph and run out of memory, or forget that the matrix traversal is O(V squared) and not O(V + E). Vertex numbering errors are common: using 1-based labels with a 0-based array gives an IndexError. In weighted graphs, mixing "0 means no edge" with "0 is a valid weight" leads to wrong shortest paths, so use infinity or None for a missing edge. Some confuse a tree with any graph, or assume graphs have no cycles; self-loops and parallel edges also need an explicit policy.

## Builds On
This concept builds on Arrays. The adjacency matrix is a two-dimensional array, and the adjacency list is an array indexed by vertex number, so constant-time indexing by vertex is what makes both forms fast. It also builds on Singly Linked List: the adjacency list was traditionally a linked list per vertex, appending a neighbour in O(1) and walking the neighbours one by one, and the dynamic arrays used today play the same role. Understanding the memory and traversal costs of arrays against linked lists explains why list-versus-matrix trade-offs look the way they do.

## Leads To
Breadth-First Search and Depth-First Search traverse a graph through its neighbour lists. Bellman-Ford consumes an edge list, Floyd-Warshall works on a matrix of distances, and Minimum Spanning Tree algorithms use both edge lists (Kruskal) and adjacency lists (Prim). Almost every algorithm in the graphs cluster starts from one of these representations.

## Check Yourself
**Q1.** How much memory does an adjacency list use?
**A1.** O(V + E).
**Q2.** Which representation answers "is there an edge between u and v?" in O(1)?
**A2.** The adjacency matrix.
**Q3.** How many times does an undirected edge appear in an adjacency list?
**A3.** Twice, once in each endpoint's list.
