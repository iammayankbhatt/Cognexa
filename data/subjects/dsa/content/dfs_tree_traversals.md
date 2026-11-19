---
id: dfs_tree_traversals
name: "Tree Traversals (pre/in/post-order)"
cluster: trees
reviewed: false
sources:
  - "CLRS, Section 12.1 (What is a binary search tree?, inorder tree walk)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.2 (Ordered operations) and Section 4.2 (depth-first search)"
---

## Overview
A traversal visits every node of a tree exactly once in a systematic order. The three depth-first orders for a binary tree differ only in when the node itself is processed relative to its two subtrees: preorder processes the node first (node, left, right), inorder processes it between the subtrees (left, node, right), and postorder processes it last (left, right, node). Each order solves different problems: preorder copies or serialises a tree, inorder reads a binary search tree in sorted order, and postorder deletes a tree or evaluates an expression because children are finished before their parent.

## Intuition
Imagine reading a book's table of contents with nested chapters. If you announce each chapter title before diving into its sections, that is preorder. If you announce a chapter only after finishing all its sections, such as writing a summary at the end, that is postorder. Inorder fits only when there are exactly two sides, like reading the left page, then the title in the middle, then the right page. In every case you go as deep as you can down one branch before backing up, which is what "depth-first" means.

## How It Works
The recursive definition is the simplest. For a node, if it is null return; otherwise do three things in an order that depends on the traversal. Preorder: visit(node), recurse left, recurse right. Inorder: recurse left, visit(node), recurse right. Postorder: recurse left, recurse right, visit(node). The recursion uses the call stack to remember where to return, so the structure is exactly "solve the same problem on each child".

The iterative version replaces the call stack with an explicit stack. For preorder, push the root, then repeatedly pop a node, visit it and push its right child and then its left child, so the left child is popped first. For inorder, walk left as far as possible pushing nodes, then pop one, visit it, and move to its right child. For postorder, a common trick is to do a modified preorder (node, right, left) and reverse the output.

Why three orders matter. In a binary search tree the left subtree holds smaller keys and the right subtree larger ones, so inorder visits the keys in ascending order. Preorder lists a parent before its children, so inserting nodes in preorder rebuilds the same tree. Postorder processes children before the parent, which is what you want when the parent's value depends on its children, such as the size or height of a subtree, the value of an arithmetic expression tree, or freeing memory.

Relationship to graph search. Tree traversals are depth-first search specialised to a tree. A tree has no cycles, so no visited set is needed, but the idea of going deep before wide is the same as in graph depth-first search.

## Worked Example
Take this tree.

```
        4
       / \
      2   6
     / \ / \
    1  3 5  7
```

Preorder (node, left, right): 4, 2, 1, 3, 6, 5, 7. Start at 4, go left to 2, then its left child 1, back to 3, then up and right to 6, then 5 and 7. Inorder (left, node, right): 1, 2, 3, 4, 5, 6, 7. The smallest node 1 comes out first because we go left as far as possible, and since this is a binary search tree the output is sorted. Postorder (left, right, node): 1, 3, 2, 5, 7, 6, 4. Every node appears after both its children, and the root is last.

## Code
```python
class Node:
    def __init__(self, value, left=None, right=None):
        self.value, self.left, self.right = value, left, right


def preorder(n, out):
    if n:
        out.append(n.value)
        preorder(n.left, out)
        preorder(n.right, out)
    return out


def inorder(n, out):
    if n:
        inorder(n.left, out)
        out.append(n.value)
        inorder(n.right, out)
    return out


def postorder(n, out):
    if n:
        postorder(n.left, out)
        postorder(n.right, out)
        out.append(n.value)
    return out


def inorder_iterative(root):
    out, stack, cur = [], [], root
    while cur or stack:
        while cur:                      # go as far left as possible
            stack.append(cur)
            cur = cur.left
        cur = stack.pop()
        out.append(cur.value)           # visit between the two subtrees
        cur = cur.right
    return out


def preorder_iterative(root):
    out, stack = [], [root] if root else []
    while stack:
        n = stack.pop()
        out.append(n.value)
        if n.right:
            stack.append(n.right)       # pushed first so it is visited second
        if n.left:
            stack.append(n.left)
    return out


tree = Node(4, Node(2, Node(1), Node(3)), Node(6, Node(5), Node(7)))
assert preorder(tree, []) == [4, 2, 1, 3, 6, 5, 7]
assert inorder(tree, []) == [1, 2, 3, 4, 5, 6, 7]
assert postorder(tree, []) == [1, 3, 2, 5, 7, 6, 4]
assert inorder_iterative(tree) == inorder(tree, [])
assert preorder_iterative(tree) == preorder(tree, [])
assert inorder(None, []) == []
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <stack>
#include <vector>

struct Node {
    int value;
    Node* left;
    Node* right;
    Node(int v, Node* l = nullptr, Node* r = nullptr) : value(v), left(l), right(r) {}
};

void preorder(const Node* n, std::vector<int>& out) {
    if (!n) return;
    out.push_back(n->value);
    preorder(n->left, out);
    preorder(n->right, out);
}

void inorder(const Node* n, std::vector<int>& out) {
    if (!n) return;
    inorder(n->left, out);
    out.push_back(n->value);
    inorder(n->right, out);
}

void postorder(const Node* n, std::vector<int>& out) {
    if (!n) return;
    postorder(n->left, out);
    postorder(n->right, out);
    out.push_back(n->value);
}

std::vector<int> inorderIterative(const Node* root) {
    std::vector<int> out;
    std::stack<const Node*> st;
    const Node* cur = root;
    while (cur || !st.empty()) {
        while (cur) {
            st.push(cur);
            cur = cur->left;
        }
        cur = st.top();
        st.pop();
        out.push_back(cur->value);
        cur = cur->right;
    }
    return out;
}

int main() {
    Node n1(1), n3(3), n5(5), n7(7);
    Node n2(2, &n1, &n3), n6(6, &n5, &n7);
    Node root(4, &n2, &n6);
    std::vector<int> pre, in, post;
    preorder(&root, pre);
    inorder(&root, in);
    postorder(&root, post);
    assert((pre == std::vector<int>{4, 2, 1, 3, 6, 5, 7}));
    assert((in == std::vector<int>{1, 2, 3, 4, 5, 6, 7}));
    assert((post == std::vector<int>{1, 3, 2, 5, 7, 6, 4}));
    assert(inorderIterative(&root) == in);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Every traversal visits each of the n nodes once and does constant work per node, so the time is O(n) for all three orders. The extra space is the recursion stack or the explicit stack, which holds at most one root-to-node path, so it is O(h) where h is the height: O(log n) for a balanced tree and O(n) for a skewed one. Using Morris traversal, which temporarily rewires null pointers, gets the space to O(1), at the cost of more complicated code.

## Common Mistakes & Misconceptions
Students confuse the three orders, typically writing the visit line in the wrong place: moving one line changes preorder into inorder. A frequent symptom is a "RecursionError: maximum recursion depth exceeded" on a long skewed tree, because the recursion depth equals the height. Forgetting the base case (checking for a null node) leads to an AttributeError on None. In the iterative preorder, pushing the left child before the right gives mirrored output. Many assume inorder returns sorted output for any binary tree, when this holds only for a binary search tree. Another misconception is that traversal order is the same as level-by-level order, which is a different traversal.

## Builds On
This concept builds on Binary Trees, because the three orders are defined by the left and right child structure of a binary tree: without two ordered children, "inorder" has no meaning. It builds on Recursion, since the natural solution handles the node and then solves the same problem on each subtree, and the call stack from recursion automatically remembers the path back up. Understanding the base case (the empty tree) and the recursive case is exactly the skill from recursion.

## Leads To
Segment Tree construction and queries are postorder and range-splitting traversals: a node's value is combined from its children after they are built. Depth-First Search on graphs generalises these traversals, adding a visited set so the walk never loops. Binary search trees use inorder to list keys in order, and expression evaluation uses postorder.

## Check Yourself
**Q1.** Which traversal of a binary search tree returns the keys in sorted order?
**A1.** Inorder (left, node, right).
**Q2.** Which traversal visits a node only after both of its children?
**A2.** Postorder.
**Q3.** How much extra space does a recursive traversal use on a tree of height h?
**A3.** O(h), for the call stack that holds the current root-to-node path.
