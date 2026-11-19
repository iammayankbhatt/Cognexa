---
id: red_black_tree
name: "Red-Black Trees"
cluster: trees
reviewed: false
sources:
  - "CLRS, Chapter 13 (Red-Black Trees)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.3 (left-leaning red-black BSTs)"
---

## Overview
A red-black tree is a binary search tree in which every node is coloured red or black, and a small set of colouring rules forces the tree to stay approximately balanced. The rules guarantee that the longest root-to-leaf path is at most twice as long as the shortest one, so the height is O(log n) and search, insert and delete are all O(log n) in the worst case. Red-black trees balance more loosely than AVL trees, which means they need fewer rotations per update, and for this reason they are the structure behind many standard ordered maps and sets, such as C++ std::map and Java TreeMap.

## Intuition
An AVL tree is a strict teacher who corrects every small imbalance at once. A red-black tree is a relaxed one that allows some unevenness as long as a simple accounting rule holds: every path from the top to the bottom must pass through the same number of "black" nodes, and "red" nodes may only be used sparingly as extra spacers (never two in a row). Because red nodes can add at most as many steps as there are black ones, no path can be more than double any other. The colours are bookkeeping that turns a geometric balance rule into local, cheap checks.

## How It Works
The rules. (1) Every node is red or black. (2) The root is black. (3) A red node never has a red child, so there are no two consecutive red nodes on a path. (4) Every path from a node down to any of its null references contains the same number of black nodes. The number of black nodes on such a path is the black height.

Why the height is logarithmic. Let the black height of the root be b. By rule 4 every path has b black nodes, so the shortest path has at least b nodes and the tree has at least 2^b - 1 nodes, so b is at most log2(n + 1). By rule 3 at most every second node on a path is red, so the longest path has at most 2b nodes. Therefore the height is at most 2 log2(n + 1).

Insert. Insert the key as in a BST and colour the new node red (this keeps rule 4 intact). If its parent is also red, rule 3 is broken, and the repair depends on the colour of the uncle. If the uncle is red, recolour the parent, uncle and grandparent and continue the check from the grandparent. If the uncle is black, one or two rotations plus recolouring fix the tree locally and finish. Finally colour the root black.

Delete. Delete as in a BST. Removing a black node reduces a black height on one path, which creates a "double black" problem that is repaired by recolouring and up to three rotations. The case analysis is longer than for insertion, but the work stays O(log n).

Left-leaning variant. The Code section uses a left-leaning red-black tree (LLRB), a simpler variant in which red links may only lean left. It uses three small operations, rotate-left, rotate-right and flip-colours, and its insert fits in a few lines. It follows the same four rules and the same height bound.

Comparison with AVL. AVL trees are more strictly balanced (height about 1.44 log2 n against up to 2 log2 n), so lookups are slightly faster. Red-black trees do fewer rotations on insert and delete (at most 2 on insert), so write-heavy workloads often prefer them.

## Worked Example
Insert 1, 2, 3 into an empty left-leaning tree. Insert 1: a red node, then the root is made black. Insert 2: it goes right of 1 as red. A red right link is not allowed in the left-leaning form, so rotate left at 1: 2 becomes the top with red left child 1. Insert 3: it goes right of 2 as red, leaving 2 with a red left child 1 and a red right child 3. Flip colours: 2 turns red and its two children turn black, and finally the root is recoloured black.

```
    2 (black)
   /         \
  1 (black)  3 (black)
```

The result is perfectly balanced, whereas an ordinary BST would be a chain. Black height on every path is 1 (counting the nodes below the root), rule 3 and rule 4 hold, and inorder is 1, 2, 3.

## Code
```python
RED, BLACK = True, False


class Node:
    def __init__(self, key, color=RED):
        self.key, self.color, self.left, self.right = key, color, None, None


def is_red(n):
    return n is not None and n.color == RED


def rotate_left(h):
    x = h.right
    h.right, x.left = x.left, h
    x.color, h.color = h.color, RED
    return x


def rotate_right(h):
    x = h.left
    h.left, x.right = x.right, h
    x.color, h.color = h.color, RED
    return x


def flip_colors(h):
    h.color = RED
    h.left.color = h.right.color = BLACK


def insert(h, key):
    if h is None:
        return Node(key)
    if key < h.key:
        h.left = insert(h.left, key)
    elif key > h.key:
        h.right = insert(h.right, key)
    if is_red(h.right) and not is_red(h.left):
        h = rotate_left(h)                       # no right-leaning red links
    if is_red(h.left) and is_red(h.left.left):
        h = rotate_right(h)                      # no two reds in a row
    if is_red(h.left) and is_red(h.right):
        flip_colors(h)                           # split a temporary 4-node
    return h


def put(root, key):
    root = insert(root, key)
    root.color = BLACK
    return root


def black_height(n):                             # -1 if the paths disagree
    if n is None:
        return 0
    left, right = black_height(n.left), black_height(n.right)
    if left == -1 or right == -1 or left != right:
        return -1
    return left + (0 if is_red(n) else 1)


def no_red_red(n):
    if n is None:
        return True
    if is_red(n) and (is_red(n.left) or is_red(n.right)):
        return False
    return no_red_red(n.left) and no_red_red(n.right)


def height(n):
    return -1 if n is None else 1 + max(height(n.left), height(n.right))


def inorder(n):
    return inorder(n.left) + [n.key] + inorder(n.right) if n else []


root = None
for k in [1, 2, 3]:
    root = put(root, k)
assert root.key == 2 and not is_red(root) and not is_red(root.left)
root = None
for k in range(1, 1025):                         # sorted input is the worst case for a plain BST
    root = put(root, k)
assert inorder(root) == list(range(1, 1025))
assert not is_red(root) and no_red_red(root) and black_height(root) != -1
assert height(root) <= 2 * 11                    # 2 * log2(n + 1) is about 20
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>

enum Color { RED, BLACK };

struct Node {
    int key;
    Color color;
    Node* left = nullptr;
    Node* right = nullptr;
    explicit Node(int k) : key(k), color(RED) {}
};

bool isRed(const Node* n) { return n && n->color == RED; }

Node* rotateLeft(Node* h) {
    Node* x = h->right;
    h->right = x->left;
    x->left = h;
    x->color = h->color;
    h->color = RED;
    return x;
}

Node* rotateRight(Node* h) {
    Node* x = h->left;
    h->left = x->right;
    x->right = h;
    x->color = h->color;
    h->color = RED;
    return x;
}

void flipColors(Node* h) {
    h->color = RED;
    h->left->color = BLACK;
    h->right->color = BLACK;
}

Node* insert(Node* h, int key) {
    if (!h) return new Node(key);
    if (key < h->key) h->left = insert(h->left, key);
    else if (key > h->key) h->right = insert(h->right, key);
    if (isRed(h->right) && !isRed(h->left)) h = rotateLeft(h);
    if (isRed(h->left) && isRed(h->left->left)) h = rotateRight(h);
    if (isRed(h->left) && isRed(h->right)) flipColors(h);
    return h;
}

int blackHeight(const Node* n) {
    if (!n) return 0;
    int l = blackHeight(n->left), r = blackHeight(n->right);
    if (l == -1 || r == -1 || l != r) return -1;
    return l + (isRed(n) ? 0 : 1);
}

void destroy(Node* n) {
    if (!n) return;
    destroy(n->left);
    destroy(n->right);
    delete n;
}

int main() {
    Node* root = nullptr;
    for (int k = 1; k <= 1024; ++k) {
        root = insert(root, k);
        root->color = BLACK;
    }
    assert(!isRed(root));
    assert(blackHeight(root) != -1);
    destroy(root);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
The height is at most 2 log2(n + 1), so search, insert and delete are O(log n) in the worst case. An insertion performs at most two rotations, and recolouring may travel up the tree for O(log n) steps, which costs only O(1) per level. A deletion performs at most three rotations. Space is O(n) plus one colour bit per node. The balance is looser than in an AVL tree, so searches may go through up to about 40 percent more levels in the worst case, while updates tend to be cheaper.

## Common Mistakes & Misconceptions
A common misconception is that a red-black tree is perfectly balanced; it only guarantees that no path is more than twice as long as any other. Students colour the new node black instead of red, which instantly breaks the equal black-height rule and forces a messy repair. In the insertion fix-up, treating the uncle's colour carelessly (recolouring when a rotation is needed, or the reverse) leaves two reds in a row. Forgetting to paint the root black at the end of every insert breaks rule 2. A symptom of a mistake is a tree whose height grows beyond 2 log n on sorted input, usually because a rotation did not copy the colour correctly. People also believe red-black trees are faster than AVL trees for lookups, when AVL trees are slightly shorter and so slightly faster to search.

## Builds On
This concept builds on AVL Trees. Red-black trees use the same rotations to repair a binary search tree after an insert or delete, and the same goal of keeping height O(log n), so rotation mechanics and the idea of fixing a violation on the way back up the path are taken directly from AVL trees. What changes is the balance rule: instead of comparing subtree heights, a red-black tree uses colours and the equal-black-count rule, which gives cheaper updates at the price of a slightly taller tree.

## Leads To
Red-black trees implement the ordered containers in many standard libraries, so they underlie ordered maps, sets and priority schedulers (the Linux kernel's completely fair scheduler uses one). The related 2-3 tree and B-Tree structures show the same balance idea in a multiway form, and the left-leaning variant is a common route to understanding them.

## Check Yourself
**Q1.** What is forbidden about consecutive red nodes?
**A1.** A red node may not have a red child, so no path has two red nodes in a row.
**Q2.** What colour is a newly inserted node before any repair?
**A2.** Red, because that keeps the black height of every path unchanged.
**Q3.** What is the maximum height of a red-black tree with n nodes?
**A3.** About 2 log2(n + 1), so O(log n).
