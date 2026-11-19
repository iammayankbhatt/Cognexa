---
id: binary_tree
name: "Binary Trees"
cluster: trees
reviewed: false
sources:
  - "CLRS, Section 10.4 (Representing rooted trees) and Appendix B.5.3 (Binary and positional trees)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.2 (Binary search trees, node structure)"
---

## Overview
A binary tree is a tree in which every node has at most two children, called the left child and the right child. The left and right positions are distinguished, so a node with only a right child is a different shape from a node with only a left child. Binary trees are the workhorse of the tree family: binary search trees, heaps, expression trees and most balanced trees are binary trees with extra rules. This concept covers the node structure, the special shapes (full, complete, perfect, degenerate), the counting facts about them and the two common representations.

## Intuition
Imagine a tournament bracket or a yes/no questionnaire: every question leads to at most two follow-ups, "yes" on one side and "no" on the other. Each node asks one question and sends you left or right. Because every step has at most two choices, a deep structure can still be navigated with a short sequence of binary decisions, which is why binary trees show up wherever a fast search is needed.

## How It Works
Node structure. A node holds a value and two references, left and right, either of which may be null. A tree is represented by a reference to its root, and an empty tree is a null root. A pointer-based node needs no array and grows one node at a time.

Shapes. A full binary tree is one where every node has either zero or two children. A perfect binary tree is full and has all leaves at the same depth. A complete binary tree has every level filled except possibly the last, and the last level is filled from the left. A degenerate (or skewed) tree has exactly one child per internal node, so it is really a linked list. A balanced tree keeps its height close to log n.

Counting facts. A perfect binary tree of height h has 2^(h+1) - 1 nodes and 2^h leaves. So a binary tree with n nodes has height at least floor(log2 n) and at most n - 1. At depth d there are at most 2^d nodes. In a full binary tree the number of leaves is one more than the number of internal nodes.

Array representation. A complete binary tree can be stored in an array without any pointers: put the root at index 0, then the children of the node at index i are at 2i + 1 and 2i + 2, and its parent is at (i - 1) // 2. Heaps use exactly this layout. For a tree that is not complete this wastes space, because missing nodes leave gaps, so pointer-based nodes are preferred for general shapes.

Recursive thinking. Because each child is the root of a smaller binary tree, almost every operation is expressed as "do something at this node, then solve the left subtree and the right subtree". Height, size and counting leaves all follow this pattern: the answer for a node is computed from the answers for its two children.

## Worked Example
Build the tree with root 1, left child 2, right child 3, and 2 having left child 4.

```
      1
     / \
    2   3
   /
  4
```

Height: node 4 has height 0, node 2 has height 1, node 3 has height 0, so the root has height 1 + max(1, 0) = 2. Size: 1 + size(left) + size(right) = 1 + 2 + 1 = 4. Leaves: 4 and 3. Is it full? No, because node 2 has one child. Is it complete? Reading level by level gives 1, 2, 3, 4, with the last level filled from the left, so yes. In the array layout this tree is [1, 2, 3, 4], and the children of index 1 (value 2) are at index 3 (value 4) and index 4 (missing).

## Code
```python
class Node:
    def __init__(self, value, left=None, right=None):
        self.value, self.left, self.right = value, left, right


def size(n):
    return 0 if n is None else 1 + size(n.left) + size(n.right)


def height(n):                       # empty tree has height -1, a leaf has height 0
    return -1 if n is None else 1 + max(height(n.left), height(n.right))


def count_leaves(n):
    if n is None:
        return 0
    if n.left is None and n.right is None:
        return 1
    return count_leaves(n.left) + count_leaves(n.right)


def is_full(n):
    if n is None:
        return True
    if (n.left is None) != (n.right is None):   # exactly one child
        return False
    return is_full(n.left) and is_full(n.right)


def from_array(a, i=0):              # complete tree stored in an array
    if i >= len(a):
        return None
    return Node(a[i], from_array(a, 2 * i + 1), from_array(a, 2 * i + 2))


root = from_array([1, 2, 3, 4])
assert size(root) == 4 and height(root) == 2 and count_leaves(root) == 2
assert not is_full(root)
assert is_full(from_array([1, 2, 3]))
assert height(None) == -1 and size(None) == 0
perfect = from_array(list(range(15)))            # perfect tree of height 3
assert size(perfect) == 2 ** 4 - 1 and count_leaves(perfect) == 2 ** 3
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

struct Node {
    int value;
    Node* left;
    Node* right;
    Node(int v, Node* l = nullptr, Node* r = nullptr) : value(v), left(l), right(r) {}
};

int size(const Node* n) { return n ? 1 + size(n->left) + size(n->right) : 0; }

int height(const Node* n) { return n ? 1 + std::max(height(n->left), height(n->right)) : -1; }

int countLeaves(const Node* n) {
    if (!n) return 0;
    if (!n->left && !n->right) return 1;
    return countLeaves(n->left) + countLeaves(n->right);
}

Node* fromArray(const std::vector<int>& a, std::size_t i = 0) {
    if (i >= a.size()) return nullptr;
    return new Node(a[i], fromArray(a, 2 * i + 1), fromArray(a, 2 * i + 2));
}

void destroy(Node* n) {
    if (!n) return;
    destroy(n->left);
    destroy(n->right);
    delete n;
}

int main() {
    Node* root = fromArray({1, 2, 3, 4});
    assert(size(root) == 4 && height(root) == 2 && countLeaves(root) == 2);
    destroy(root);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Size, height and leaf counting each visit every node once, so they take O(n) time and O(h) recursion stack, where h is the height. A binary tree with n nodes has height between floor(log2 n) and n - 1, so h ranges from O(log n) in a balanced tree to O(n) in a skewed one, and that gap is why balance matters. A pointer-based node costs two extra references per node, while the array form needs 2^(h+1) - 1 slots for a tree of height h, which is compact only when the tree is nearly complete.

## Common Mistakes & Misconceptions
A common symptom is an AttributeError or segmentation fault on "None" or null when code reads node.left.value without checking that the child exists. Another is a stack overflow in recursive height or size on a very skewed tree with many thousands of nodes. Students use "full", "complete" and "perfect" interchangeably, although they differ: a complete tree can have a node with one child, a full tree need not be complete. Height is miscounted by one when an empty tree is treated as height 0 instead of -1, and some assume every binary tree is balanced, when inserting sorted data into an ordinary binary search tree produces a chain.

## Builds On
This concept builds on Tree Terminology & Properties. All the vocabulary of root, leaf, depth, height and subtree is used unchanged, and the fact that a tree has n - 1 edges and one path to each node still holds. A binary tree adds one restriction (at most two ordered children), which is what makes the counting facts and the array representation possible.

## Leads To
Tree Traversals (pre/in/post-order) and Level-Order Traversal are the two standard ways to visit every node. Binary Search Trees add an ordering rule that makes search fast, and Binary Heap uses the complete-tree array layout described here.

## Check Yourself
**Q1.** How many nodes does a perfect binary tree of height 3 have?
**A1.** 15, because 2^4 - 1 = 15.
**Q2.** Where are the children of the node at array index i in a complete tree?
**A2.** At indexes 2i + 1 and 2i + 2.
**Q3.** What shape is a binary tree in which every node has exactly one child?
**A3.** A degenerate (skewed) tree, equivalent to a linked list, with height n - 1.
