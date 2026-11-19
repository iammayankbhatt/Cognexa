---
id: binary_heap
name: "Binary Heap"
cluster: trees
reviewed: false
sources:
  - "CLRS, Chapter 6 (Heapsort), Sections 6.1 to 6.5 (heaps and priority queues)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.4 (Priority Queues)"
---

## Overview
A binary heap is a complete binary tree stored in an array that keeps its most important element at the root. In a min-heap every node is less than or equal to its children, so the minimum is at index 0; in a max-heap every node is greater than or equal to its children, so the maximum is at index 0. This gives O(1) access to the extreme element and O(log n) insertion and removal of it, and the heap can be built from an unordered array in O(n). A binary heap is the standard way to implement a priority queue, and it is the engine behind heap sort, Dijkstra's algorithm, Prim's algorithm and top-k selection.

## Intuition
Imagine a company hierarchy where every manager is at least as senior as their direct reports. You cannot tell who is the second most senior just by looking at the layout, but you always know who is at the top. When a new hire joins at the bottom, you let them swap upward past anyone they outrank. When the boss leaves, you promote the person from the bottom to the top temporarily and let them sink down past anyone more senior. A heap keeps only this partial order, not a full sorted order, and that is why it is cheaper to maintain than a sorted list.

## How It Works
Shape property. The tree is complete: all levels are full except possibly the last, which is filled from the left. This makes the array representation exact, with no gaps. With zero-based indexes the children of index i are 2i + 1 and 2i + 2, and the parent is (i - 1) // 2. The height is floor(log2 n), so any walk from root to leaf has O(log n) steps.

Heap property. For a min-heap, a[parent] <= a[child] for every node. Only parent and child are compared, siblings are unordered.

Insert (push). Append the new item at the end of the array, so the shape stays complete, then sift it up: while it is smaller than its parent, swap them. It moves at most the height of the tree, so insertion costs O(log n).

Extract-min (pop). The minimum is at index 0. Move the last element to the root, shrink the array by one, then sift it down: while it is larger than its smallest child, swap with that smaller child. This costs O(log n). Using the last element keeps the shape complete.

Peek. Read a[0] in O(1).

Build-heap. Given an arbitrary array, call sift-down on every non-leaf node from index n // 2 - 1 down to 0. This is O(n), not O(n log n), because half the nodes are leaves that need no work and most other nodes sit near the bottom, so little sifting occurs. Inserting the n items one by one would cost O(n log n).

Variants. A max-heap flips every comparison. Many libraries (Python's heapq) provide only a min-heap; to get a max-heap, store negated keys. To change a stored priority you need to know the item's position, which is why some designs keep a position map.

## Worked Example
Insert 5, 3, 8, 1 into an empty min-heap. Insert 5: [5]. Insert 3: append, [5, 3]; 3 is less than its parent 5, so swap: [3, 5]. Insert 8: [3, 5, 8]; 8 is larger than its parent, so it stays. Insert 1: append, [3, 5, 8, 1]; its parent is index 1 (value 5), swap: [3, 1, 8, 5]; its new parent is index 0 (value 3), swap: [1, 3, 8, 5].

```
      1
     / \
    3   8
   /
  5
```

Now extract-min: return 1. Move the last element 5 to the root: [5, 3, 8]. Sift down: the smaller child of 5 is 3, which is smaller than 5, so swap: [3, 5, 8]. Node 5 has no children left (index 1's children would be at 3 and 4, beyond the size), so stop. The next minimum is 3.

## Code
```python
class MinHeap:
    def __init__(self):
        self.a = []

    def push(self, x):
        a = self.a
        a.append(x)
        i = len(a) - 1
        while i > 0 and a[i] < a[(i - 1) // 2]:         # sift up
            a[i], a[(i - 1) // 2] = a[(i - 1) // 2], a[i]
            i = (i - 1) // 2

    def pop(self):
        a = self.a
        top = a[0]
        last = a.pop()
        if a:
            a[0] = last
            self._sift_down(0)
        return top

    def _sift_down(self, i):
        a, n = self.a, len(self.a)
        while True:
            smallest = i
            for c in (2 * i + 1, 2 * i + 2):
                if c < n and a[c] < a[smallest]:
                    smallest = c
            if smallest == i:
                return
            a[i], a[smallest] = a[smallest], a[i]
            i = smallest

    @classmethod
    def from_list(cls, items):                           # build-heap in O(n)
        h = cls()
        h.a = list(items)
        for i in range(len(h.a) // 2 - 1, -1, -1):
            h._sift_down(i)
        return h


h = MinHeap()
for x in [5, 3, 8, 1]:
    h.push(x)
assert h.a == [1, 3, 8, 5]
assert h.pop() == 1 and h.a == [3, 5, 8]
assert [h.pop(), h.pop(), h.pop()] == [3, 5, 8]

import heapq
import random

random.seed(3)
data = [random.randint(0, 100) for _ in range(200)]
built = MinHeap.from_list(data)
assert all(built.a[(i - 1) // 2] <= built.a[i] for i in range(1, len(built.a)))
out = [built.pop() for _ in range(len(data))]
assert out == sorted(data)
ref = list(data)
heapq.heapify(ref)
assert [heapq.heappop(ref) for _ in range(len(ref))] == sorted(data)
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <queue>
#include <vector>

struct MinHeap {
    std::vector<int> a;

    void push(int x) {
        a.push_back(x);
        std::size_t i = a.size() - 1;
        while (i > 0 && a[i] < a[(i - 1) / 2]) {
            std::swap(a[i], a[(i - 1) / 2]);
            i = (i - 1) / 2;
        }
    }

    int pop() {
        int top = a[0];
        a[0] = a.back();
        a.pop_back();
        siftDown(0);
        return top;
    }

    void siftDown(std::size_t i) {
        while (true) {
            std::size_t smallest = i;
            for (std::size_t c : {2 * i + 1, 2 * i + 2})
                if (c < a.size() && a[c] < a[smallest]) smallest = c;
            if (smallest == i) return;
            std::swap(a[i], a[smallest]);
            i = smallest;
        }
    }
};

int main() {
    MinHeap h;
    for (int x : {5, 3, 8, 1}) h.push(x);
    assert((h.a == std::vector<int>{1, 3, 8, 5}));
    assert(h.pop() == 1);
    assert((h.a == std::vector<int>{3, 5, 8}));

    std::priority_queue<int, std::vector<int>, std::greater<int>> pq;  // library min-heap
    for (int x : {5, 3, 8, 1}) pq.push(x);
    assert(pq.top() == 1);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Peek is O(1). Push and pop are O(log n) because they move along one path of length at most the height floor(log2 n). Build-heap is O(n). Searching for an arbitrary value is O(n) because a heap gives no ordering between siblings, and extracting all items in order costs O(n log n), which is exactly heap sort. Space is O(n) with no pointers, since the array layout needs no extra memory. Changing the priority of an item (decrease-key) is O(log n) if its position is known.

## Common Mistakes & Misconceptions
A frequent belief is that a heap is a sorted array; reading the array from left to right does not give sorted order, only the root is guaranteed to be the minimum. Symptoms of wrong index formulas are IndexError or a heap that silently stops working: for zero-based arrays the children are 2i + 1 and 2i + 2, not 2i and 2i + 1. In pop, forgetting to move the last element to the root or sifting down with the old size gives a corrupted heap. Python's heapq is only a min-heap, so users who want the largest item and push positive numbers get the smallest; push negatives instead. Another misconception is that build-heap is O(n log n), and that a heap can find an arbitrary element quickly. A heap also does not support efficient deletion by value without extra bookkeeping.

## Builds On
This concept builds on Binary Trees, because the heap is a complete binary tree, and its shape rules (levels, height log n, array indexing for parent and children) come from there. It also builds on Priority Queue (ADT): the priority queue defines what operations are required (insert and remove the highest priority element), and the binary heap is the data structure that supplies them in O(log n), which is much faster than the O(n) of an unsorted list or a sorted array.

## Leads To
Heap Sort uses a max-heap to sort in place in O(n log n). Dijkstra's Shortest Path uses a min-heap to pick the closest unvisited vertex, and Minimum Spanning Tree algorithms such as Prim's use one to pick the cheapest crossing edge. Top-k problems keep a heap of size k, and event simulations and schedulers use heaps to fetch the next event.

## Check Yourself
**Q1.** Where is the smallest element of a min-heap?
**A1.** At index 0, the root.
**Q2.** What is the cost of inserting into a binary heap of n items?
**A2.** O(log n), because the new item sifts up along one root-to-leaf path.
**Q3.** Is the array of a binary heap sorted?
**A3.** No. Only the parent-child ordering is guaranteed, not the order of siblings or of the whole array.
