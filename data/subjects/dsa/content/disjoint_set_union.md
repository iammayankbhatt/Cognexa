---
id: disjoint_set_union
name: "Disjoint Set Union (Union-Find)"
cluster: trees
reviewed: false
sources:
  - "CLRS, Chapter 19 (Data Structures for Disjoint Sets)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.5 (Case Study: Union-Find)"
---

## Overview
A disjoint set union (DSU), also known as union-find, maintains a collection of non-overlapping sets over the elements 0 to n - 1. It supports two operations: find(x), which returns a representative (the root) of the set that contains x, and union(x, y), which merges the sets containing x and y. Two elements are in the same set exactly when find returns the same representative for both. With two small optimisations, union by size and path compression, each operation runs in nearly constant amortised time. DSU is the standard tool for connectivity questions on a changing graph, for detecting cycles while adding edges, and for Kruskal's minimum spanning tree algorithm.

## Intuition
Imagine people at a large party who gradually become friends. Whenever two people become friends, their whole friend groups merge into one. You often need to ask "are these two in the same group?" Instead of keeping each group as a list, give every group a leader. Each person remembers just one person who leads them closer to the leader; following these pointers up from anyone leads to the group's leader. Merging two groups simply makes one leader report to the other. Asking whether two people are in the same group means checking whether they have the same leader.

## How It Works
Representation. Store a parent array where parent[i] is the parent of i in a forest of rooted trees. A root has parent[root] = root. Each tree is one set, and its root is the representative. Initially every element is its own root, so there are n singleton sets.

Find. Follow parent pointers from x upward until reaching a root. The cost is the depth of x, which could be as large as n in a long chain.

Union. Find the roots of x and y. If they are the same, the elements are already in one set and nothing happens. Otherwise make one root the child of the other by setting parent[root_a] = root_b.

Union by size (or rank). Always attach the smaller tree below the larger one's root. This keeps trees shallow: a node's depth increases by one only when its tree is merged into a tree at least as large, so the tree size at least doubles each time, which bounds depth by log2 n.

Path compression. During find, make every node on the path point closer to (or directly at) the root. The simplest iterative form is path halving: while x is not a root, set parent[x] to its grandparent and move up. Later finds on those nodes are faster.

Combined cost. With both optimisations, a sequence of m operations on n elements takes O(m alpha(n)) time, where alpha is the inverse Ackermann function, which is at most 4 for any practical n. This is why each operation is called nearly constant amortised time. The amortised analysis argues that rare long finds pay for themselves by flattening the tree for many later finds.

Limitations. DSU supports merging but not splitting a set. It answers "same set?" but does not store the members in an easily listable order without extra bookkeeping.

## Worked Example
Start with six elements 0 to 5, each alone. union(0, 1): roots 0 and 1 have equal size, so attach 1 under 0 and the size of 0 becomes 2. union(2, 3): attach 3 under 2. union(1, 3): find(1) is 0 (path 1, 0) and find(3) is 2; both trees have size 2, so attach root 2 under root 0, giving size 4. union(4, 5): attach 5 under 4.

```
    0        4
   / \       |
  1   2      5
      |
      3
```

There are now two sets, {0, 1, 2, 3} and {4, 5}. find(3) walks 3, 2, 0, returns 0, and with path halving sets parent[3] to 0 on the way, so the next find(3) takes a single step. Checking connected(1, 3) gives find(1) = 0 and find(3) = 0, so True, while connected(1, 5) gives 0 and 4, so False.

## Code
```python
class DSU:
    def __init__(self, n):
        self.parent = list(range(n))
        self.size = [1] * n
        self.components = n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]     # path halving
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False                                     # already in the same set
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra                                 # attach the smaller tree
        self.size[ra] += self.size[rb]
        self.components -= 1
        return True

    def connected(self, a, b):
        return self.find(a) == self.find(b)


d = DSU(6)
for a, b in [(0, 1), (2, 3), (1, 3), (4, 5)]:
    assert d.union(a, b)
assert d.components == 2
assert d.connected(1, 3) and not d.connected(1, 5)
assert d.find(3) == 0 and d.parent[3] == 0
assert not d.union(0, 3)                                     # a redundant edge closes a cycle

# cycle detection while adding edges one by one
edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5)]
u = DSU(6)
first_cycle = next(e for e in edges if not u.union(*e))
assert first_cycle == (3, 0)

import random

random.seed(2)
n = 200
u2, label = DSU(n), list(range(n))                           # brute-force labels
for _ in range(400):
    a, b = random.randrange(n), random.randrange(n)
    u2.union(a, b)
    old, new = label[a], label[b]
    label = [new if x == old else x for x in label]
    x, y = random.randrange(n), random.randrange(n)
    assert u2.connected(x, y) == (label[x] == label[y])
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <numeric>
#include <utility>
#include <vector>

class DSU {
public:
    explicit DSU(int n) : parent_(n), size_(n, 1), components_(n) {
        std::iota(parent_.begin(), parent_.end(), 0);
    }

    int find(int x) {
        while (parent_[x] != x) {
            parent_[x] = parent_[parent_[x]];   // path halving
            x = parent_[x];
        }
        return x;
    }

    bool unite(int a, int b) {
        int ra = find(a), rb = find(b);
        if (ra == rb) return false;
        if (size_[ra] < size_[rb]) std::swap(ra, rb);
        parent_[rb] = ra;
        size_[ra] += size_[rb];
        --components_;
        return true;
    }

    bool connected(int a, int b) { return find(a) == find(b); }
    int components() const { return components_; }

private:
    std::vector<int> parent_, size_;
    int components_;
};

int main() {
    DSU d(6);
    d.unite(0, 1);
    d.unite(2, 3);
    d.unite(1, 3);
    d.unite(4, 5);
    assert(d.components() == 2);
    assert(d.connected(1, 3) && !d.connected(1, 5));
    assert(!d.unite(0, 3));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
With union by size and path compression, m operations on n elements take O(m alpha(n)) time, where alpha is the inverse Ackermann function and is below 5 for any input that fits in the universe, so each operation is practically O(1) amortised. With union by size alone, find costs O(log n) in the worst case. With path compression alone the amortised cost is O(log n). With neither, a chain of n elements makes find O(n). Space is O(n) for the parent and size arrays. Building the structure is O(n).

## Common Mistakes & Misconceptions
A common bug is merging the elements instead of their roots (setting parent[a] = b), which breaks the forest structure and loses earlier merges; always union the representatives returned by find. Another is forgetting the guard for equal roots, which makes the size count wrong or creates a self-loop. Students sometimes test connectivity by comparing parent[a] == parent[b], which is only right for direct children of the same root, instead of comparing find(a) == find(b). Recursion in find without compression on a long chain can overflow the stack, so an iterative find is safer. Many assume DSU can undo a union (it cannot without a special rollback design), or that it can list set members cheaply. Others think the O(alpha(n)) bound holds without both optimisations.

## Builds On
This concept builds on Tree Terminology & Properties. A DSU is a forest of rooted trees stored as a parent array, so ideas such as root, parent, depth and the height of a tree explain why shallow trees give fast finds and why the representative is simply the root. It also builds on Amortized Analysis: individual finds may be slow, but path compression flattens the tree and pays for later operations, so the guarantee is stated per sequence of operations rather than for each worst-case find.

## Leads To
Minimum Spanning Tree algorithms use DSU in Kruskal's method to decide whether an edge joins two different components (add it) or closes a cycle (skip it). The same structure powers cycle detection in undirected graphs, counting connected components in dynamic graphs, grid problems such as counting islands as land is added, and equivalence-class merging in compilers.

## Check Yourself
**Q1.** What does find(x) return?
**A1.** The representative (root) of the set containing x.
**Q2.** What does union by size do?
**A2.** It attaches the smaller tree under the root of the larger one so trees stay shallow.
**Q3.** What does path compression do?
**A3.** It makes nodes on the find path point closer to the root, so later finds are faster.
