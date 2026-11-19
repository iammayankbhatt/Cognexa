---
id: queue
name: "Queue (ADT & implementations)"
cluster: linear
reviewed: false
sources:
  - "CLRS, Section 10.1 (Stacks and queues)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.3 (Queues)"
---

## Overview
A queue is a collection with first-in, first-out behaviour: items leave in the same order they arrived. The operations are enqueue (add at the back), dequeue (remove from the front) and peek (read the front). Queues model waiting lines: print jobs, customers, messages between programs, and the frontier of breadth-first search. Like the stack, the queue is an abstract data type and can be built on an array or a linked list.

## Intuition
A queue is a line at a ticket counter. New arrivals join at the back, and the person at the front is served first. Nobody can cut in, so the order of service is the order of arrival. If service is slower than arrival, the line simply grows, and every person is eventually served in turn.

## How It Works
The ADT promises: enqueue(x) adds x at the back, dequeue() removes and returns the front item (underflow error when empty), peek() returns the front without removing it, and isEmpty() and size() report the state. All should be O(1).

A linked-list queue keeps two references: head for the front and tail for the back. Enqueue appends a node after the tail and updates tail; dequeue removes the head node and moves head forward. When the last node is removed, both head and tail must become null, a common edge case.

An array-based queue is trickier. Using a plain list and removing from index 0 shifts every remaining item, which makes dequeue O(n); that is why Python's `list.pop(0)` is a bad queue. A better array design keeps two indexes, front and back, and lets them move forward as items come and go, wrapping around the end of a fixed array (a circular buffer, covered later). In Python, use `collections.deque`, whose popleft and append are both O(1).

The queue's mirror image is the stack. Both restrict access to the ends, but a stack uses one end and a queue uses both. Typical uses: breadth-first search visits nodes level by level using a queue; schedulers hand out CPU time in arrival order; buffers between a fast producer and a slow consumer smooth out bursts.

## Worked Example
Process the operations enqueue A, enqueue B, dequeue, enqueue C, dequeue, dequeue on an empty queue.

Enqueue A: [A]. Enqueue B: [A, B] with A at the front. Dequeue returns A: [B]. Enqueue C: [B, C]. Dequeue returns B: [C]. Dequeue returns C: []. The items left in the order A, B, C, exactly the order they arrived. One more dequeue now would be underflow.

For a linked-list queue, enqueue A creates a node that is both head and tail. Enqueue B links after tail and moves tail to B. Dequeue A moves head to B. When C is dequeued last, head becomes null, so tail must also be reset to null.

## Code
```python
from collections import deque


class LinkedQueue:
    class _Node:
        def __init__(self, value):
            self.value = value
            self.next = None

    def __init__(self):
        self._head = None
        self._tail = None
        self._size = 0

    def enqueue(self, value):
        node = self._Node(value)
        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            self._tail = node
        self._size += 1

    def dequeue(self):
        if self._head is None:
            raise IndexError("dequeue from empty queue")
        node = self._head
        self._head = node.next
        if self._head is None:
            self._tail = None            # queue became empty: reset the tail too
        self._size -= 1
        return node.value

    def peek(self):
        if self._head is None:
            raise IndexError("peek at empty queue")
        return self._head.value

    def __len__(self):
        return self._size


q = LinkedQueue()
q.enqueue("A")
q.enqueue("B")
assert q.dequeue() == "A"
q.enqueue("C")
assert q.peek() == "B" and len(q) == 2
assert q.dequeue() == "B" and q.dequeue() == "C"
try:
    q.dequeue()
except IndexError:
    pass
else:
    raise AssertionError("expected underflow")
q.enqueue("D")                          # still works after becoming empty
assert q.dequeue() == "D"

d = deque()
d.append(1)
d.append(2)
assert d.popleft() == 1 and list(d) == [2]
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <queue>
#include <string>

int main() {
    std::queue<std::string> q;
    q.push("A");
    q.push("B");
    assert(q.front() == "A");
    q.pop();
    q.push("C");
    assert(q.front() == "B" && q.size() == 2);
    q.pop();
    assert(q.front() == "C");
    q.pop();
    assert(q.empty());

    q.push("D");  // still usable after becoming empty
    assert(q.front() == "D" && q.back() == "D");

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Enqueue, dequeue, peek, isEmpty and size are O(1) for a linked-list queue (with a tail pointer), for a circular-buffer queue and for Python's deque. A queue built on a plain Python list with `pop(0)` has O(n) dequeue because all remaining items shift, making n operations cost O(n squared). Space is O(n) for n stored items. Breadth-first search with a queue runs in time proportional to the number of nodes and edges, and the queue can hold up to O(V) nodes at once.

## Common Mistakes & Misconceptions
A frequent symptom is a slow program that "uses a list as a queue", repeatedly calling `pop(0)`, whose cost grows with the list length. Another is losing track of the tail pointer, so that after the queue empties and refills the tail still refers to a removed node and later items disappear. Students confuse queues with stacks and expect the newest item back first, or forget underflow on an empty queue. In breadth-first search, forgetting to mark a node as visited when enqueuing it (rather than when dequeuing) puts the same node on the queue several times. Finally, people assume a queue must be an array; the ADT is independent of its storage.

## Builds On
This concept builds on Arrays because an array-based queue stores its items in contiguous slots and tracks front and back indexes, which also explains why naive removal from the front is costly. It builds on Singly Linked List because a linked-list queue uses a head for dequeue and a tail for enqueue, giving constant-time operations at both ends with no shifting.

## Leads To
The deque and circular queue extend the idea to both ends and to a reusable ring of slots. The priority queue ADT changes the removal rule from arrival order to priority, level-order traversal of a tree uses a queue, and breadth-first search uses one to explore a graph layer by layer.

## Check Yourself
**Q1.** In what order are items removed from a queue?
**A1.** First in, first out: in the order they were added.
**Q2.** Why is `list.pop(0)` a poor dequeue in Python?
**A2.** It shifts all remaining elements, so it takes O(n) time instead of O(1).
**Q3.** What must be updated when the last node of a linked-list queue is dequeued?
**A3.** Both head and tail must be set to null.
