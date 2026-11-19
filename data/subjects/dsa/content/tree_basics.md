---
id: tree_basics
name: "Tree Terminology & Properties"
cluster: trees
reviewed: false
sources:
  - "CLRS, Appendix B.5 (Graphs and trees) and Chapter 10.4 (Representing rooted trees)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.2 (Binary search trees, tree vocabulary)"
---

## Overview
A tree is a hierarchical data structure made of nodes joined by edges, with exactly one node designated the root and exactly one path between the root and every other node. Unlike an array or a linked list, which are linear, a tree branches: each node can have several children. Trees model anything hierarchical, such as file systems, HTML documents, organisation charts and the call structure of a recursive function. This concept fixes the vocabulary (root, parent, child, leaf, depth, height, subtree) and the basic facts (n nodes have n - 1 edges) that every later tree concept uses.

## Intuition
Think of a family tree drawn from one ancestor downwards, or a folder on your computer. The top folder contains subfolders, which contain more subfolders and files. You can get from the top folder to any file by exactly one chain of folders, and no folder is ever inside two different parents. Files, which hold nothing further, are the leaves. That "one parent, one path from the top" rule is the heart of the definition.

## How It Works
A tree is built from nodes. Each node stores a value and references to its children, which is the same idea as a linked list node but with possibly more than one outgoing reference.

Vocabulary. The root is the single node with no parent. Every other node has exactly one parent. Nodes sharing a parent are siblings. A node with no children is a leaf, and a node with at least one child is an internal node. An ancestor of a node is any node on the path from the root down to its parent, and a descendant is any node below it. The subtree rooted at a node is that node together with all its descendants, and every child of a node is itself the root of a smaller tree, which is why tree algorithms are naturally recursive.

Measurements. The depth of a node is the number of edges on the path from the root to it, so the root has depth 0. The height of a node is the number of edges on the longest downward path to a leaf, so a leaf has height 0, and the height of the tree is the height of its root. The level of a node is its depth, and the degree of a node is its number of children.

Key properties. A tree with n nodes has exactly n - 1 edges, because every node except the root has exactly one parent edge. Removing any edge disconnects the tree, and adding any edge between two existing nodes creates a cycle, so a tree is a connected graph with no cycles. In a tree where every node has at most k children, the number of nodes at depth d is at most k to the power d, and a tree of height h has at most (k^(h+1) - 1) / (k - 1) nodes.

Representation. The usual representation is a node object holding a value and a list of children. Another common one is first-child and next-sibling, which uses two references per node and turns any tree into a binary shape. A parent array stores for each node the index of its parent, which is compact and is exactly what union-find uses later.

## Worked Example
Consider this tree, with A as the root.

```
        A
      / | \
     B  C  D
    / \     \
   E   F     G
```

A has children B, C, D, so its degree is 3. B, C and D are siblings. E, F, C and G are leaves, and A, B, D are internal nodes. The path from A to F is A, B, F, so F has depth 2. The height of B is 1 because its longest downward path (B to E) has one edge, the height of D is also 1, and the height of A is 2. The ancestors of F are B and A, and the descendants of A are all six other nodes. Counting nodes gives 7 and counting edges gives 6, matching n - 1.

## Code
```python
class Node:
    def __init__(self, value):
        self.value = value
        self.children = []

    def add(self, child):
        self.children.append(child)
        return child


def size(node):
    return 1 + sum(size(c) for c in node.children)


def height(node):                      # edges on the longest downward path
    if not node.children:
        return 0
    return 1 + max(height(c) for c in node.children)


def depth_of(node, target, d=0):       # edges from node down to the target value
    if node.value == target:
        return d
    for c in node.children:
        found = depth_of(c, target, d + 1)
        if found is not None:
            return found
    return None


def leaves(node):
    if not node.children:
        return [node.value]
    return [v for c in node.children for v in leaves(c)]


a = Node("A")
b, c, d = a.add(Node("B")), a.add(Node("C")), a.add(Node("D"))
b.add(Node("E"))
b.add(Node("F"))
d.add(Node("G"))

assert size(a) == 7
assert height(a) == 2 and height(b) == 1 and height(c) == 0
assert depth_of(a, "F") == 2 and depth_of(a, "A") == 0 and depth_of(a, "Z") is None
assert leaves(a) == ["E", "F", "C", "G"]
assert size(a) - 1 == 6                # n nodes, n - 1 edges
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

struct Node {
    std::string value;
    std::vector<std::unique_ptr<Node>> children;
    explicit Node(std::string v) : value(std::move(v)) {}
    Node* add(const std::string& v) {
        children.push_back(std::unique_ptr<Node>(new Node(v)));
        return children.back().get();
    }
};

int size(const Node* n) {
    int total = 1;
    for (const auto& c : n->children) total += size(c.get());
    return total;
}

int height(const Node* n) {
    int best = 0;
    for (const auto& c : n->children) best = std::max(best, 1 + height(c.get()));
    return best;
}

int main() {
    Node a("A");
    Node* b = a.add("B");
    a.add("C");
    Node* d = a.add("D");
    b->add("E");
    b->add("F");
    d->add("G");
    assert(size(&a) == 7);
    assert(height(&a) == 2 && height(b) == 1);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Computing size, height or the list of leaves visits each node once, so each takes O(n) time. The recursion uses O(h) stack space where h is the height, which is O(n) for a degenerate chain and O(log n) for a balanced tree. Finding the depth of a given node by searching from the root is O(n) in the worst case, but if each node stores a parent reference it is O(depth). Storing the tree needs O(n) memory.

## Common Mistakes & Misconceptions
Students mix up height and depth: depth counts down from the root to a node, height counts down from a node to its deepest leaf. They also disagree on whether the root is at level 0 or 1, and whether height counts edges or nodes, which causes off-by-one answers; this course counts edges, so a single node has height 0. Another symptom is code that loops forever because a node was added as a child of two parents, which creates a cycle or shared subtree and breaks the tree property. People say "a tree with n nodes has n edges" when the correct count is n - 1, and treat any graph that "looks like a tree" as one even though a disconnected graph or one with a cycle is not a tree.

## Builds On
This concept builds on Singly Linked List. A tree node is a linked-list node generalised to hold several next references, so the habits of creating nodes, following references and handling a missing (null) reference carry over directly. The difference is that a list has one successor per node, so it is a tree where every node has at most one child, while a tree node's children list lets the structure branch.

## Leads To
Binary Trees restrict every node to at most two children, which makes the shape easy to store and reason about. Trie uses a tree whose edges are labelled with characters, and Disjoint Set Union stores sets as trees held in a parent array. Tree vocabulary also appears in the lower-bound argument for comparison sorting, where a decision tree has one leaf per possible ordering.

## Check Yourself
**Q1.** How many edges does a tree with 12 nodes have?
**A1.** 11, because every node except the root has exactly one parent edge.
**Q2.** What is the height of a tree that consists of a single node?
**A2.** 0, counting edges on the longest downward path.
**Q3.** Can a node in a tree have two parents?
**A3.** No. Two parents would create a second path to the node, so the structure would no longer be a tree.
