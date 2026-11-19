---
id: avl_tree
name: "AVL Trees"
cluster: trees
reviewed: false
sources:
  - "CLRS, Problem 13-3 (AVL trees) and Chapter 13 introduction (balanced search trees)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.3 (Balanced Search Trees, rotations)"
---

## Overview
An AVL tree is a binary search tree that keeps itself height-balanced. For every node, the heights of its left and right subtrees differ by at most 1. After each insertion or deletion, the tree checks the balance along the path it changed and repairs any violation with small local restructurings called rotations. This guarantees the height stays O(log n), so search, insert and delete are all O(log n) in the worst case, unlike a plain binary search tree whose height can reach n - 1.

## Intuition
Imagine stacking boxes on two shelves hanging from a balance beam. A little difference between the two sides is fine, but as soon as one side becomes two levels heavier than the other the beam tilts too far, and you fix it by moving a single box across rather than rebuilding the whole shelf. An AVL tree tolerates a tilt of 1 and immediately fixes a tilt of 2 with one local rotation, so the structure never drifts into a long chain.

## How It Works
Balance factor. Each node stores its height. The balance factor of a node is height(left) - height(right), and in an AVL tree it must always be -1, 0 or +1. A missing child has height -1.

Rotations. A rotation is a local change of a few references that preserves the inorder order of the keys, which means the binary search tree property stays valid, but changes the heights. A right rotation at node y with left child x makes x the new subtree root, y becomes x's right child, and x's old right subtree becomes y's left subtree. A left rotation is the mirror image. Each rotation changes only a constant number of references, so it takes O(1) time.

Four imbalance cases after inserting into a subtree of node z whose balance factor becomes +2 or -2. Left-Left (balance +2, left child's balance >= 0): fix with one right rotation at z. Right-Right (balance -2, right child's balance <= 0): one left rotation at z. Left-Right (balance +2, left child's balance < 0): first left-rotate the left child, which turns it into the Left-Left case, then right-rotate z. Right-Left is the mirror: right-rotate the right child, then left-rotate z.

Insert. Insert as in a binary search tree, then walk back up the path to the root, updating heights and rebalancing the first unbalanced node found. After an insertion, a single rotation or double rotation always restores the height of that subtree to what it was before the insertion, so no further changes are needed higher up.

Delete. Delete as in a binary search tree, then walk back up updating heights and rebalancing. Unlike insertion, a deletion can require a rotation at several levels on the way up, but the path is only O(log n) long, so the total is still O(log n).

Height bound. The smallest AVL tree of height h has N(h) = N(h - 1) + N(h - 2) + 1 nodes, which grows like the Fibonacci numbers. So n nodes force the height to be at most about 1.44 log2 n, which is the source of the logarithmic guarantee.

## Worked Example
Insert 10, 20, 30 into an empty AVL tree. After 10 and 20, the tree is 10 with right child 20, which is fine (balance -1 at 10). Insert 30: it goes right of 20, so 10 now has balance factor -2 (left height -1, right height 1), a Right-Right case.

```
  10                 20
    \               /  \
     20     --->   10   30
       \
        30
```

A left rotation at 10 makes 20 the root, with 10 as its left child and 30 as its right child. All balance factors are now 0, and inorder is still 10, 20, 30. A plain BST would have kept the chain. Next insert 25: it goes under 30 as its left child, giving 30 balance +1, 20 balance -1, still valid, so nothing is rotated.

## Code
```python
class Node:
    def __init__(self, key):
        self.key, self.left, self.right, self.height = key, None, None, 0


def h(n):
    return -1 if n is None else n.height


def update(n):
    n.height = 1 + max(h(n.left), h(n.right))


def balance(n):
    return h(n.left) - h(n.right)


def rotate_right(y):
    x = y.left
    y.left, x.right = x.right, y
    update(y)
    update(x)
    return x


def rotate_left(x):
    y = x.right
    x.right, y.left = y.left, x
    update(x)
    update(y)
    return y


def rebalance(n):
    update(n)
    b = balance(n)
    if b > 1:
        if balance(n.left) < 0:
            n.left = rotate_left(n.left)           # Left-Right case
        return rotate_right(n)
    if b < -1:
        if balance(n.right) > 0:
            n.right = rotate_right(n.right)        # Right-Left case
        return rotate_left(n)
    return n


def insert(n, key):
    if n is None:
        return Node(key)
    if key < n.key:
        n.left = insert(n.left, key)
    elif key > n.key:
        n.right = insert(n.right, key)
    else:
        return n
    return rebalance(n)


def inorder(n):
    return inorder(n.left) + [n.key] + inorder(n.right) if n else []


def is_avl(n):
    if n is None:
        return True
    return abs(balance(n)) <= 1 and is_avl(n.left) and is_avl(n.right)


root = None
for k in [10, 20, 30]:
    root = insert(root, k)
assert root.key == 20 and root.left.key == 10 and root.right.key == 30
root = None
for k in range(1, 1001):                           # sorted input stays balanced
    root = insert(root, k)
assert is_avl(root) and inorder(root) == list(range(1, 1001))
assert root.height <= 11                           # about 1.44 * log2(1000)
lr = None
for k in [30, 10, 20]:                             # Left-Right case
    lr = insert(lr, k)
assert lr.key == 20 and lr.left.key == 10 and lr.right.key == 30
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

struct Node {
    int key;
    int height = 0;
    Node* left = nullptr;
    Node* right = nullptr;
    explicit Node(int k) : key(k) {}
};

int h(const Node* n) { return n ? n->height : -1; }
void update(Node* n) { n->height = 1 + std::max(h(n->left), h(n->right)); }
int balance(const Node* n) { return h(n->left) - h(n->right); }

Node* rotateRight(Node* y) {
    Node* x = y->left;
    y->left = x->right;
    x->right = y;
    update(y);
    update(x);
    return x;
}

Node* rotateLeft(Node* x) {
    Node* y = x->right;
    x->right = y->left;
    y->left = x;
    update(x);
    update(y);
    return y;
}

Node* rebalance(Node* n) {
    update(n);
    int b = balance(n);
    if (b > 1) {
        if (balance(n->left) < 0) n->left = rotateLeft(n->left);
        return rotateRight(n);
    }
    if (b < -1) {
        if (balance(n->right) > 0) n->right = rotateRight(n->right);
        return rotateLeft(n);
    }
    return n;
}

Node* insert(Node* n, int key) {
    if (!n) return new Node(key);
    if (key < n->key) n->left = insert(n->left, key);
    else if (key > n->key) n->right = insert(n->right, key);
    else return n;
    return rebalance(n);
}

void destroy(Node* n) {
    if (!n) return;
    destroy(n->left);
    destroy(n->right);
    delete n;
}

int main() {
    Node* root = nullptr;
    for (int k = 1; k <= 1000; ++k) root = insert(root, k);
    assert(root->height <= 11);
    destroy(root);

    Node* t = nullptr;
    for (int k : {10, 20, 30}) t = insert(t, k);
    assert(t->key == 20 && t->left->key == 10 && t->right->key == 30);
    destroy(t);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Height is at most about 1.44 log2(n + 2), so search, insert and delete are all O(log n) in the worst case, not just on average. Each insertion performs at most one single or double rotation, and a deletion may perform O(log n) rotations along the path, each rotation costing O(1). Space is O(n) for the nodes plus one extra integer per node for the height (or two bits if only the balance factor is stored). Compared with a plain BST, an AVL tree pays a constant overhead on every update to guarantee the logarithmic bound.

## Common Mistakes & Misconceptions
A typical bug is forgetting to update the heights after a rotation, so later balance factors are computed from stale values and the tree slowly becomes unbalanced; rotate, then update the lower node first and the new root second. Students choose the wrong rotation: a zig-zag shape (Left-Right or Right-Left) cannot be fixed by one rotation, and applying a single rotation just moves the imbalance. Another is thinking AVL trees are perfectly balanced; they only guarantee that the subtree heights differ by at most one, so the tree can be noticeably uneven. People also assume rotations change the sorted order, but a rotation preserves inorder order. Using the recursive code on very large inputs is safe, because the height is only O(log n).

## Builds On
This concept builds on Binary Search Trees. An AVL tree is a binary search tree, so search, the inorder property and the way insert and delete first work like a plain BST are all reused, and the rotations are valid exactly because they preserve the BST ordering. What the AVL tree adds is the balance condition and the repair step, which fixes the worst case from the BST concept where sorted insertions create a chain of height n - 1.

## Leads To
Red-Black Trees relax the balance rule to colours and fewer rotations, so updates are cheaper while the height is still O(log n); they are used in many standard library ordered maps. The idea of local repair by rotation also appears in splay trees and treaps, and B-Trees solve a related balancing problem for disk-based storage.

## Check Yourself
**Q1.** What is the balance factor rule for an AVL tree?
**A1.** For every node the heights of the left and right subtrees differ by at most 1.
**Q2.** Which rotations fix a Left-Right imbalance?
**A2.** A left rotation on the left child, then a right rotation on the unbalanced node.
**Q3.** What is the worst-case height of an AVL tree with n nodes?
**A3.** About 1.44 log2 n, which is O(log n).
