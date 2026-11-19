---
id: b_tree
name: "B-Trees"
cluster: trees
reviewed: false
sources:
  - "CLRS, Chapter 18 (B-Trees)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 6.2 (B-Trees)"
---

## Overview
A B-tree is a balanced search tree whose nodes hold many keys and have many children, rather than one key and two children. All leaves are at the same depth, and every node except the root is at least half full. Because a node can have hundreds of children, the tree is very short: a B-tree with a million keys may be only three or four levels deep. This matters when each node is stored in a disk block, since reading a block is thousands of times slower than reading memory, and the cost of a search is the number of blocks read. B-trees and their variants are the standard index structure in databases and file systems.

## Intuition
Think of a printed encyclopedia. A binary search would need about twenty page flips to find a word among a million entries, but the book has index tabs on the spine, then guide words at the top of each page, so you find the word in three steps even though each step shows you many candidate entries at once. A B-tree node is like one page of guide words: it lists many sorted keys and tells you which child page covers each gap between them. Fewer, fatter steps beat many thin ones when each step is expensive.

## How It Works
Definition with minimum degree t (t >= 2). Every node holds between t - 1 and 2t - 1 keys, except the root, which may hold as few as 1. An internal node with k keys has k + 1 children. The keys in a node are sorted, and for key i the child before it holds only smaller keys and the child after it only larger ones. All leaves are at the same depth, which is why a B-tree is perfectly balanced in height.

Search. In the current node, find the first key that is greater than or equal to the target using a linear or binary search within the node. If it is equal, you found it. Otherwise move to the child that sits in the gap, or report absence at a leaf. The number of nodes visited equals the height.

Insert. Insertion always happens in a leaf. A full node (2t - 1 keys) is split in two: its median key moves up into the parent, and the other keys form two nodes of t - 1 keys each. The common one-pass method splits any full node on the way down so that the parent always has room for the promoted key. If the root is full, it is split and a new root is created, which is the only way the tree grows taller, and it grows at the top, so all leaves stay at equal depth.

Delete. Removing a key from a node that would drop below t - 1 keys requires borrowing a key from a sibling through the parent or merging with a sibling. Merging can propagate upward, and if the root ends up with no keys the tree becomes one level shorter.

Height. A B-tree with n keys and minimum degree t has height at most log_t((n + 1) / 2). With t = 100 and a billion keys the height is at most about five.

Variants. A B+ tree stores all data in the leaves and links the leaves in a list, which makes range scans fast, and it is what most databases actually use.

## Worked Example
Take t = 2, so each node holds 1 to 3 keys. Insert 1, 2, 3: the root is the single node [1, 2, 3], now full. Insert 4: the root is full, so split it. The median 2 moves up to a new root, leaving children [1] and [3], and then 4 joins [3] giving [3, 4]. Insert 5: it goes to [3, 4], which becomes [3, 4, 5]. Insert 6: the child [3, 4, 5] is full, so it is split before descending: 4 moves up into the root, which is now [2, 4], with children [1], [3] and [5]; then 6 is added to [5] giving [5, 6].

```
        [2 | 4]
       /   |    \
    [1]  [3]  [5 6]
```

All leaves are at depth 1, every non-root node has between 1 and 3 keys, and an inorder reading gives 1, 2, 3, 4, 5, 6. Searching for 5 reads the root, sees 5 is greater than 4, and goes to the last child, finding 5 after two node reads.

## Code
```python
from bisect import bisect_left, bisect_right, insort


class Node:
    def __init__(self, leaf):
        self.keys, self.children, self.leaf = [], [], leaf


class BTree:
    def __init__(self, t=2):
        self.t = t
        self.root = Node(leaf=True)

    def search(self, key, node=None):
        node = node or self.root
        i = bisect_left(node.keys, key)
        if i < len(node.keys) and node.keys[i] == key:
            return True
        return False if node.leaf else self.search(key, node.children[i])

    def _split_child(self, parent, i):
        t, y = self.t, parent.children[i]
        z = Node(y.leaf)
        median = y.keys[t - 1]
        z.keys, y.keys = y.keys[t:], y.keys[: t - 1]
        if not y.leaf:
            z.children, y.children = y.children[t:], y.children[:t]
        parent.keys.insert(i, median)
        parent.children.insert(i + 1, z)

    def insert(self, key):
        root = self.root
        if len(root.keys) == 2 * self.t - 1:            # root is full: the tree grows at the top
            new_root = Node(leaf=False)
            new_root.children = [root]
            self._split_child(new_root, 0)
            self.root = new_root
        self._insert_nonfull(self.root, key)

    def _insert_nonfull(self, node, key):
        if node.leaf:
            if key not in node.keys:
                insort(node.keys, key)
            return
        i = bisect_right(node.keys, key)
        if len(node.children[i].keys) == 2 * self.t - 1:
            self._split_child(node, i)
            if key > node.keys[i]:
                i += 1
        self._insert_nonfull(node.children[i], key)


def inorder(node):
    if node.leaf:
        return list(node.keys)
    out = []
    for i, child in enumerate(node.children):
        out += inorder(child)
        if i < len(node.keys):
            out.append(node.keys[i])
    return out


def leaf_depths(node, d=0):
    if node.leaf:
        return {d}
    return set().union(*(leaf_depths(c, d + 1) for c in node.children))


def sizes_ok(node, t, is_root=True):
    if len(node.keys) > 2 * t - 1 or (not is_root and len(node.keys) < t - 1):
        return False
    return node.leaf or all(sizes_ok(c, t, False) for c in node.children)


b = BTree(t=2)
for k in [1, 2, 3, 4, 5, 6]:
    b.insert(k)
assert b.root.keys == [2, 4]
assert [c.keys for c in b.root.children] == [[1], [3], [5, 6]]
assert b.search(5) and not b.search(7)

import random

random.seed(5)
for t in (2, 3, 5):
    tree = BTree(t)
    data = random.sample(range(100000), 2000)
    for k in data:
        tree.insert(k)
    assert inorder(tree.root) == sorted(data)
    assert len(leaf_depths(tree.root)) == 1
    assert sizes_ok(tree.root, t)
    assert all(tree.search(k) for k in data[:50])
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

const int T = 2;  // minimum degree: nodes hold T - 1 to 2T - 1 keys

struct Node {
    bool leaf;
    std::vector<int> keys;
    std::vector<Node*> kids;
    explicit Node(bool l) : leaf(l) {}
};

bool search(const Node* n, int key) {
    auto i = std::lower_bound(n->keys.begin(), n->keys.end(), key) - n->keys.begin();
    if (i < (long)n->keys.size() && n->keys[i] == key) return true;
    return n->leaf ? false : search(n->kids[i], key);
}

void splitChild(Node* parent, int i) {
    Node* y = parent->kids[i];
    Node* z = new Node(y->leaf);
    int median = y->keys[T - 1];
    z->keys.assign(y->keys.begin() + T, y->keys.end());
    y->keys.resize(T - 1);
    if (!y->leaf) {
        z->kids.assign(y->kids.begin() + T, y->kids.end());
        y->kids.resize(T);
    }
    parent->keys.insert(parent->keys.begin() + i, median);
    parent->kids.insert(parent->kids.begin() + i + 1, z);
}

void insertNonFull(Node* n, int key) {
    if (n->leaf) {
        auto pos = std::lower_bound(n->keys.begin(), n->keys.end(), key);
        if (pos == n->keys.end() || *pos != key) n->keys.insert(pos, key);
        return;
    }
    int i = std::upper_bound(n->keys.begin(), n->keys.end(), key) - n->keys.begin();
    if ((int)n->kids[i]->keys.size() == 2 * T - 1) {
        splitChild(n, i);
        if (key > n->keys[i]) ++i;
    }
    insertNonFull(n->kids[i], key);
}

Node* insert(Node* root, int key) {
    if ((int)root->keys.size() == 2 * T - 1) {
        Node* s = new Node(false);
        s->kids.push_back(root);
        splitChild(s, 0);
        root = s;
    }
    insertNonFull(root, key);
    return root;
}

void destroy(Node* n) {
    for (Node* c : n->kids) destroy(c);
    delete n;
}

int main() {
    Node* root = new Node(true);
    for (int k = 1; k <= 6; ++k) root = insert(root, k);
    assert((root->keys == std::vector<int>{2, 4}));
    assert((root->kids[2]->keys == std::vector<int>{5, 6}));
    assert(search(root, 5) && !search(root, 7));
    destroy(root);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Search and insert visit O(height) nodes, and the height is O(log_t n), so the number of disk reads is O(log_t n), far smaller than log2 n when t is large. Within a node the work is O(t) for a linear scan or O(log t) with binary search, so the CPU time is O(log n) overall and the main saving is in disk accesses. Insert and delete also write O(log_t n) nodes. Space is O(n), with nodes at least half full so utilisation is at least about 50 percent. A node is usually sized to match one disk block, for example 4 KB.

## Common Mistakes & Misconceptions
Students think a B-tree is just a binary search tree with extra keys, and miss that its purpose is to minimise disk reads, so node size is chosen to fit a block. A common implementation bug is splitting a node and forgetting to move the right half of the children along with the right half of the keys, which leaves a node with k keys but the wrong number of children and breaks searches. Another is the wrong median: with 2t - 1 keys the median is at index t - 1. Splitting only after inserting makes a node temporarily overflow the parent, so the one-pass method splits full nodes on the way down. People also assume the tree grows downward at the leaves; it grows upward when the root splits. Confusing a B-tree with a B+ tree (data only in leaves) is common.

## Builds On
This concept builds on Binary Search Trees. It keeps the central idea, that sorted keys guide a search to the right subtree, but widens each node from one key to many, so the "left or right" choice becomes "which of the k + 1 gaps". The balance rule is stricter than for a plain BST: all leaves share one depth, which is maintained by splitting rather than by the rotations used in AVL trees.

## Leads To
B+ trees and the indexes of relational databases and file systems (for example NTFS and ext4 directories) are variants of this design. The same idea of high branching to cut expensive accesses appears in LSM trees and in cache-aware data structures. 2-3 trees and 2-3-4 trees are B-trees with t = 2, and red-black trees can be seen as their binary encoding.

## Check Yourself
**Q1.** Why does a B-tree use nodes with many keys?
**A1.** To make the tree very short so that a search reads few disk blocks.
**Q2.** What happens when a node is full during insertion?
**A2.** It is split in two around its median key, and the median moves up to the parent.
**Q3.** How does the height of a B-tree increase?
**A3.** Only when the root splits, which adds a new root above the old one.
