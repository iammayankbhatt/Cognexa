---
id: bst
name: "Binary Search Trees"
cluster: trees
reviewed: false
sources:
  - "CLRS, Chapter 12 (Binary Search Trees)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.2 (Binary Search Trees)"
---

## Overview
A binary search tree (BST) is a binary tree with an ordering rule: for every node, all keys in its left subtree are smaller than the node's key and all keys in its right subtree are larger. This rule lets search, insert and delete discard half of the remaining tree at each step, in the same way binary search discards half of a sorted array, but with a structure that can grow and shrink cheaply. When the tree is reasonably balanced the operations take O(log n) time, but a plain BST has no balancing mechanism, so in the worst case it degenerates into a chain and the operations take O(n).

## Intuition
Think of a guessing game where you hold a secret number and the other player asks about a value. Each answer tells them "go lower" or "go higher". A BST stores the keys so that every node is exactly such a question: if the key you want is smaller, follow the left branch, otherwise follow the right. The shape of the tree records the sequence of questions that finds each value quickly, as long as the questions split the remaining possibilities roughly in half.

## How It Works
Ordering invariant. For every node x, every key in x's left subtree is less than x.key and every key in its right subtree is greater. This is a statement about the whole subtree, not only the immediate children: a node deep in the left subtree of x must still be smaller than x.

Search. Start at the root. If the target equals the current key, you are done. If it is smaller go to the left child, otherwise go to the right child. If you reach a null reference the key is absent. Each step moves down one level, so search costs O(h) where h is the height.

Insert. Search for the key; when you fall off the tree at a null child, attach a new node there. A new key always becomes a leaf, and duplicates are either rejected or handled by a count.

Minimum, maximum, successor. The minimum is the leftmost node, found by following left children, and the maximum is the rightmost. The successor of a node (the next larger key) is the minimum of its right subtree if there is one, and otherwise the nearest ancestor for which the node lies in the left subtree.

Delete. There are three cases. If the node is a leaf, simply remove it. If it has one child, replace the node by that child. If it has two children, find its inorder successor (the minimum of the right subtree), copy the successor's key into the node, and then delete the successor from the right subtree, which is easier because it has at most one child.

Inorder traversal of a BST gives the keys in ascending order, which is the easiest way to check the invariant and to print the contents sorted.

## Worked Example
Insert 8, 3, 10, 1, 6, 14 in that order. 8 becomes the root. 3 is less than 8, so it goes left. 10 goes right of 8. 1 is less than 8 and less than 3, so it becomes the left child of 3. 6 is less than 8, greater than 3, so it is the right child of 3. 14 is greater than 8 and greater than 10, so it is the right child of 10.

```
        8
       / \
      3   10
     / \    \
    1   6    14
```

Search for 6: compare with 8 (go left), with 3 (go right), find 6 in three comparisons. Delete 3, which has two children: its successor is the minimum of its right subtree, which is 6. Copy 6 into the node and delete the old 6 (a leaf). The tree is now 8 with left child 6 (which has left child 1) and right subtree 10 with child 14. Inorder gives 1, 6, 8, 10, 14.

## Code
```python
class Node:
    def __init__(self, key):
        self.key, self.left, self.right = key, None, None


def insert(root, key):
    if root is None:
        return Node(key)
    if key < root.key:
        root.left = insert(root.left, key)
    elif key > root.key:
        root.right = insert(root.right, key)
    return root                                  # equal keys are ignored


def search(root, key):
    while root and root.key != key:
        root = root.left if key < root.key else root.right
    return root is not None


def minimum(node):
    while node.left:
        node = node.left
    return node


def delete(root, key):
    if root is None:
        return None
    if key < root.key:
        root.left = delete(root.left, key)
    elif key > root.key:
        root.right = delete(root.right, key)
    else:
        if root.left is None:
            return root.right                    # zero or one child
        if root.right is None:
            return root.left
        succ = minimum(root.right)               # two children: use the inorder successor
        root.key = succ.key
        root.right = delete(root.right, succ.key)
    return root


def inorder(root):
    return inorder(root.left) + [root.key] + inorder(root.right) if root else []


def height(root):
    return -1 if root is None else 1 + max(height(root.left), height(root.right))


root = None
for k in [8, 3, 10, 1, 6, 14]:
    root = insert(root, k)
assert inorder(root) == [1, 3, 6, 8, 10, 14]
assert search(root, 6) and not search(root, 7)
root = delete(root, 3)
assert inorder(root) == [1, 6, 8, 10, 14] and root.left.key == 6
root = delete(root, 8)
assert inorder(root) == [1, 6, 10, 14]
chain = None
for k in range(1, 51):                            # sorted input gives a chain
    chain = insert(chain, k)
assert height(chain) == 49
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

struct Node {
    int key;
    Node* left = nullptr;
    Node* right = nullptr;
    explicit Node(int k) : key(k) {}
};

Node* insert(Node* root, int key) {
    if (!root) return new Node(key);
    if (key < root->key) root->left = insert(root->left, key);
    else if (key > root->key) root->right = insert(root->right, key);
    return root;
}

bool search(const Node* root, int key) {
    while (root && root->key != key) root = key < root->key ? root->left : root->right;
    return root != nullptr;
}

Node* minimum(Node* n) {
    while (n->left) n = n->left;
    return n;
}

Node* erase(Node* root, int key) {
    if (!root) return nullptr;
    if (key < root->key) {
        root->left = erase(root->left, key);
    } else if (key > root->key) {
        root->right = erase(root->right, key);
    } else if (!root->left) {
        Node* r = root->right;
        delete root;
        return r;
    } else if (!root->right) {
        Node* l = root->left;
        delete root;
        return l;
    } else {
        root->key = minimum(root->right)->key;
        root->right = erase(root->right, root->key);
    }
    return root;
}

void inorder(const Node* n, std::vector<int>& out) {
    if (!n) return;
    inorder(n->left, out);
    out.push_back(n->key);
    inorder(n->right, out);
}

void destroy(Node* n) {
    if (!n) return;
    destroy(n->left);
    destroy(n->right);
    delete n;
}

int main() {
    Node* root = nullptr;
    for (int k : {8, 3, 10, 1, 6, 14}) root = insert(root, k);
    std::vector<int> v;
    inorder(root, v);
    assert((v == std::vector<int>{1, 3, 6, 8, 10, 14}));
    assert(search(root, 6) && !search(root, 7));
    root = erase(root, 3);
    v.clear();
    inorder(root, v);
    assert((v == std::vector<int>{1, 6, 8, 10, 14}));
    destroy(root);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Search, insert and delete all cost O(h) time, where h is the height of the tree. For a balanced tree built from random-order insertions the expected height is O(log n), so the operations average O(log n). In the worst case, such as inserting keys in sorted order, the tree is a chain with h = n - 1, and each operation costs O(n). Space is O(n) for the nodes, plus O(h) recursion stack for the recursive versions. Inorder traversal takes O(n). Self-balancing trees such as AVL trees repair the shape after each change to keep h at O(log n).

## Common Mistakes & Misconceptions
The most common wrong belief is that a BST is valid if each node is larger than its left child and smaller than its right child; the rule applies to whole subtrees, so a node in the right subtree of the root must be greater than the root even if it is the left child of something. A symptom is a "valid-looking" tree where search misses a key that is present. Another is a slow BST: inserting already sorted data makes a chain and everything becomes O(n), and students expect O(log n) regardless. Deleting a node with two children by simply removing it breaks the tree, and forgetting to reattach the returned subtree root (root.left = delete(root.left, key)) leaves the tree unchanged. Duplicates need a stated policy, and recursion on a deep chain can hit the recursion limit.

## Builds On
This concept builds on Binary Trees, since the BST is a binary tree with left and right children and the shape counting facts such as height versus size apply unchanged. It also builds on Binary Search: the BST is the pointer-based form of the same "compare with the middle and discard half" idea, and its search path corresponds to the sequence of midpoints that binary search would examine. The difference is that insertion and deletion on a BST cost O(h) without shifting elements, whereas a sorted array needs O(n) shifting.

## Leads To
AVL Trees add rotations that keep the height at O(log n) after every insert and delete, fixing the worst-case chain. B-Trees generalise the ordering idea to nodes with many keys for disk storage. BSTs are also the basis of ordered maps and sets (such as std::map), range queries and successor lookups.

## Check Yourself
**Q1.** What does an inorder traversal of a BST produce?
**A1.** The keys in ascending sorted order.
**Q2.** What is the worst-case height of a BST with n nodes, and when does it occur?
**A2.** n - 1, when keys are inserted in sorted (or reverse sorted) order and the tree becomes a chain.
**Q3.** How do you delete a node that has two children?
**A3.** Replace its key with its inorder successor (the minimum of the right subtree) and delete that successor node.
