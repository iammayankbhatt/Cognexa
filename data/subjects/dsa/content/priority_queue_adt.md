---
id: priority_queue_adt
name: "Priority Queue (ADT)"
cluster: linear
reviewed: false
sources:
  - "CLRS, Section 6.5 (Priority queues)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.4 (Priority queues)"
---

## Overview
A priority queue is a collection where each item carries a priority and the item with the highest priority (or, in a min-priority queue, the lowest key) is removed first, regardless of when it arrived. Its core operations are insert, peek at the best item and extract the best item. Unlike a plain queue, order of arrival does not decide who is served next. Priority queues drive schedulers, event simulations, Dijkstra's shortest-path algorithm, Huffman coding and "top k" problems.

## Intuition
Think of an emergency room. Patients do not see the doctor in arrival order; the one with the most serious condition goes next, and a new arrival with a critical injury jumps ahead of everyone waiting. The waiting room is a priority queue, and the triage nurse always asks "who is most urgent right now?". The ADT describes that behaviour without saying how the waiting room is organised.

## How It Works
The ADT offers insert(item, priority), peek() (look at the best item), extract() (remove and return it), isEmpty() and size(). A min-priority queue treats the smallest key as best, a max-priority queue the largest. Ties are resolved arbitrarily unless you add a tiebreaker such as an arrival counter to keep first-in-first-out order among equal priorities.

Because it is an ADT, many implementations are possible with different trade-offs. An unsorted array makes insert O(1) (append) but extract O(n) (scan for the best). A sorted array makes extract O(1) at the sorted end but insert O(n) because of shifting. A balanced search tree gives O(log n) for both. The best general choice is the binary heap, which gives O(log n) insert and O(log n) extract with O(1) peek, and builds an n-item queue in O(n); it is covered in its own concept.

Python offers the heapq module, a min-heap on a list: heappush, heappop and the best item at index 0. For a max-queue you push negated keys, or wrap items in tuples where the first element is the priority. A tuple like (priority, counter, item) keeps comparisons well defined when two items share a priority and the items themselves cannot be compared. C++ offers std::priority_queue, which is a max-heap by default; pass std::greater to get a min-heap.

Common applications: always process the earliest event first in a simulation; pick the closest unvisited vertex in Dijkstra; merge k sorted lists by always taking the smallest head; maintain the k largest values of a stream with a small min-queue of size k.

## Worked Example
Insert tasks with priorities into a min-priority queue: ("write report", 3), ("fix outage", 1), ("reply email", 2), then extract twice.

After the three inserts the best (smallest) priority is 1. Extract returns "fix outage". The remaining items have priorities 3 and 2, so the next extract returns "reply email", not "write report", even though the report arrived first. If a new task ("call client", 1) now arrives, it becomes the best and the next extract returns it ahead of "write report".

For top-k, keep a min-queue of size 3 over the stream 5, 1, 9, 3, 7. Push 5, 1, 9. Next 3 is larger than the smallest (1), so pop 1 and push 3: {3, 5, 9}. Next 7 beats 3, so pop 3 and push 7: {5, 7, 9}, the three largest values.

## Code
```python
import heapq


class UnsortedPQ:
    """Insert is O(1); extract-min scans the list, O(n)."""

    def __init__(self):
        self.items = []

    def insert(self, priority, item):
        self.items.append((priority, item))

    def extract_min(self):
        if not self.items:
            raise IndexError("extract from empty priority queue")
        best = min(range(len(self.items)), key=lambda i: self.items[i][0])
        return self.items.pop(best)


tasks = [(3, "write report"), (1, "fix outage"), (2, "reply email")]

pq = UnsortedPQ()
for p, t in tasks:
    pq.insert(p, t)
assert pq.extract_min() == (1, "fix outage")
assert pq.extract_min() == (2, "reply email")
pq.insert(1, "call client")
assert pq.extract_min() == (1, "call client")

heap = []
for p, t in tasks:
    heapq.heappush(heap, (p, t))                # heapq is a binary min-heap: O(log n)
assert heapq.heappop(heap) == (1, "fix outage")
assert heap[0] == (2, "reply email")            # peek is O(1)

# Ties: add a counter so equal priorities come out first-in first-out.
tied = []
for order, name in enumerate(["a", "b", "c"]):
    heapq.heappush(tied, (5, order, name))
assert [heapq.heappop(tied)[2] for _ in range(3)] == ["a", "b", "c"]

# A max-queue by negating the priority, and top-3 of a stream.
top = []
for v in [5, 1, 9, 3, 7]:
    heapq.heappush(top, v)
    if len(top) > 3:
        heapq.heappop(top)
assert sorted(top) == [5, 7, 9]
assert heapq.nlargest(2, [5, 1, 9, 3, 7]) == [9, 7]
print("all checks passed")
```

```cpp
#include <cassert>
#include <functional>
#include <iostream>
#include <queue>
#include <string>
#include <utility>
#include <vector>

int main() {
    // std::priority_queue is a max-heap by default; std::greater makes it a min-heap.
    using Task = std::pair<int, std::string>;
    std::priority_queue<Task, std::vector<Task>, std::greater<Task>> pq;
    pq.push({3, "write report"});
    pq.push({1, "fix outage"});
    pq.push({2, "reply email"});
    assert(pq.top().second == "fix outage");
    pq.pop();
    assert(pq.top().second == "reply email");
    pq.push({1, "call client"});
    assert(pq.top().second == "call client");

    // Top-3 of a stream with a min-heap of size 3.
    std::priority_queue<int, std::vector<int>, std::greater<int>> top;
    for (int v : {5, 1, 9, 3, 7}) {
        top.push(v);
        if (top.size() > 3) top.pop();
    }
    assert(top.top() == 5 && top.size() == 3);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Complexity depends on the implementation. Unsorted array: insert O(1), extract O(n). Sorted array: insert O(n), extract O(1). Binary heap: insert O(log n), extract O(log n), peek O(1), and building from n items O(n). Sorting n items by inserting all and extracting all costs O(n log n) with a heap. Space is O(n). The top-k pattern keeps a queue of size k, so each of n items costs O(log k) and the total is O(n log k) time and O(k) space.

## Common Mistakes & Misconceptions
Students expect a priority queue to iterate in sorted order; the underlying heap is only partly ordered, so printing the list shows the best item first and the rest in no particular order. Another mistake is treating Python's heapq as a max-heap: it is a min-heap, and pushing positive numbers returns the smallest first. When items are not comparable, pushing `(priority, item)` raises TypeError on ties, which a counter tiebreaker fixes. In C++, `std::priority_queue` returns the largest item, which surprises people who wanted the smallest. People also confuse a priority queue with a plain queue and expect first-in first-out order, or call "sorted list" the same thing even though maintaining sorted order makes inserts O(n).

## Builds On
This concept builds on Queue: a priority queue keeps the same insert-and-remove interface but replaces the "oldest first" rule with "highest priority first". Understanding enqueue, dequeue and the behaviour of an empty queue transfers directly, and the unsorted and sorted array implementations are variations on the queue's storage choices.

## Leads To
The binary heap is the standard efficient implementation of this ADT, with O(log n) insert and extract. Heap sort uses it for in-place sorting, and Dijkstra's algorithm and Prim's algorithm use it to pick the next closest vertex.

## Check Yourself
**Q1.** What does extract do in a min-priority queue?
**A1.** It removes and returns the item with the smallest priority.
**Q2.** What are insert and extract costs with an unsorted array?
**A2.** Insert is O(1) and extract is O(n), because the best item must be found by scanning.
**Q3.** How do you get a max-priority queue from Python's heapq?
**A3.** Push negated priorities (or negated keys), since heapq is a min-heap.
