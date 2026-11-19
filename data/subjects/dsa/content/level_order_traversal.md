---
id: level_order_traversal
name: "Level-Order Traversal"
cluster: trees
reviewed: false
sources:
  - "CLRS, Section 10.1 (Stacks and queues) and Section 22.2 (Breadth-first search)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.2 (level-order traversal) and Section 4.1"
---

## Overview
Level-order traversal visits the nodes of a tree one depth at a time: first the root, then all nodes at depth 1 from left to right, then all nodes at depth 2, and so on. It is also called breadth-first traversal of a tree, because it explores wide before deep. The standard implementation uses a queue: take a node from the front, visit it, and add its children to the back. Level-order is the right tool when the answer depends on levels, such as printing a tree row by row, finding the shortest path to a node, computing the width of each level or the minimum depth.

## Intuition
Picture a rumour spreading through a company. The CEO tells their direct reports (level 1), those people each tell their own direct reports (level 2), and so on. Everyone at one level hears the news at the same time before the next level does. A queue models this perfectly because it serves people in the order they were told: whoever was added first is processed first, so a whole level is finished before the next one begins.

## How It Works
Basic algorithm. Create an empty queue and put the root in it. While the queue is not empty, remove the node at the front, visit it, and append its left child and then its right child if they exist. Because children are appended behind everything already waiting, nodes at depth d are all processed before any node at depth d + 1.

Grouping by level. Many problems need to know where one level ends. Before processing a level, record the current queue size k: exactly k nodes in the queue belong to the current level. Process k nodes, adding their children, and then the queue holds exactly the next level. This lets you build a list of lists, compute the maximum of each level, or pick the rightmost node of each level.

Why a queue and not a stack. A stack returns the most recently added node, which sends the traversal deep along one branch (depth-first). A queue returns the oldest waiting node, which keeps the traversal wide. Swapping the data structure is the only difference between the two traversals.

Connection to graph search. Level-order on a tree is breadth-first search specialised to trees. For a general graph you also need a visited set because cycles would otherwise cause repeats, but the queue discipline is identical, and the level number of a node equals its shortest distance in edges from the root.

## Worked Example
Tree:

```
        1
       / \
      2   3
     / \   \
    4   5   6
```

Queue starts as [1]. Level 0: size is 1, pop 1 and visit it, push 2 and 3, so the queue is [2, 3]. Level 1: size is 2. Pop 2, visit it, push 4 and 5, queue [3, 4, 5]. Pop 3, visit it, push 6, queue [4, 5, 6]. Level 2: size is 3, pop 4, 5 and 6, and none of them has children. The queue is empty and the traversal ends. Output grouped by level: [[1], [2, 3], [4, 5, 6]]. Flattened order: 1, 2, 3, 4, 5, 6.

## Code
```python
from collections import deque


class Node:
    def __init__(self, value, left=None, right=None):
        self.value, self.left, self.right = value, left, right


def level_order(root):
    if root is None:
        return []
    levels, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):          # exactly the nodes of this level
            node = queue.popleft()
            level.append(node.value)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        levels.append(level)
    return levels


def min_depth(root):                          # first leaf met in level order is the shallowest
    if root is None:
        return 0
    queue, depth = deque([root]), 0
    while queue:
        depth += 1
        for _ in range(len(queue)):
            node = queue.popleft()
            if not node.left and not node.right:
                return depth
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)


tree = Node(1, Node(2, Node(4), Node(5)), Node(3, None, Node(6)))
assert level_order(tree) == [[1], [2, 3], [4, 5, 6]]
assert level_order(None) == []
assert min_depth(tree) == 3          # node 3 has a right child, so the shallowest leaves are 4, 5, 6
assert min_depth(Node(7)) == 1
assert min_depth(Node(1, Node(2), Node(3, Node(4)))) == 2
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <queue>
#include <vector>

struct Node {
    int value;
    Node* left;
    Node* right;
    Node(int v, Node* l = nullptr, Node* r = nullptr) : value(v), left(l), right(r) {}
};

std::vector<std::vector<int>> levelOrder(Node* root) {
    std::vector<std::vector<int>> levels;
    if (!root) return levels;
    std::queue<Node*> q;
    q.push(root);
    while (!q.empty()) {
        std::vector<int> level;
        for (std::size_t k = q.size(); k > 0; --k) {   // exactly the nodes of this level
            Node* n = q.front();
            q.pop();
            level.push_back(n->value);
            if (n->left) q.push(n->left);
            if (n->right) q.push(n->right);
        }
        levels.push_back(level);
    }
    return levels;
}

int main() {
    Node n4(4), n5(5), n6(6);
    Node n2(2, &n4, &n5), n3(3, nullptr, &n6);
    Node root(1, &n2, &n3);
    auto levels = levelOrder(&root);
    assert(levels.size() == 3);
    assert((levels[0] == std::vector<int>{1}));
    assert((levels[1] == std::vector<int>{2, 3}));
    assert((levels[2] == std::vector<int>{4, 5, 6}));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Each node is enqueued once and dequeued once, so level-order runs in O(n) time. The queue holds at most one level at a time, so the extra space is O(w) where w is the maximum width of the tree: up to about n / 2 for a complete tree (the bottom level) and just 1 for a skewed one. This is the opposite trade-off from depth-first traversal, whose stack is O(h): a wide, shallow tree is cheap for depth-first and costly for level-order, and a narrow, deep tree is the reverse.

## Common Mistakes & Misconceptions
A common bug is using a list and calling pop(0) in Python, which works but is O(n) per removal and makes the traversal quadratic; use collections.deque with popleft. Another is using a stack by mistake, which produces depth-first order instead of level order. Forgetting to snapshot the queue length means levels get mixed together, because the loop condition len(queue) changes while the loop runs. Students also push None children onto the queue and then crash with AttributeError when popping them, or forget the empty-tree case. A conceptual error is believing level-order needs recursion; it is naturally iterative, with the queue doing the job of the call stack.

## Builds On
This concept builds on Binary Trees, because it follows the left and right child references and relies on each node having at most two children to enqueue. It builds on Queue (ADT & implementations), since the first-in first-out order is the whole mechanism: the queue guarantees that all nodes of depth d leave before any node of depth d + 1. Choosing an efficient queue implementation (a deque with O(1) operations) directly determines the O(n) running time.

## Leads To
Breadth-First Search on a graph is the same algorithm with a visited set added, and it finds shortest paths in unweighted graphs. Level-order is also used to serialise a tree in a form that can be rebuilt, to build a tree from an array level by level, and to solve level-based questions such as the right-side view of a tree or the lowest level containing a given value.

## Check Yourself
**Q1.** Which data structure drives level-order traversal?
**A1.** A queue, because nodes must be processed in the order they were discovered.
**Q2.** How can you tell when one level ends and the next begins?
**A2.** Record the queue size before processing a level; that many nodes belong to the level.
**Q3.** What is the extra space used by level-order on a tree?
**A3.** O(w), where w is the maximum number of nodes in any level.
