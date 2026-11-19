---
id: deque_circular_queue
name: "Deque & Circular Queue"
cluster: linear
reviewed: false
sources:
  - "CLRS, Section 10.1 (Exercises on deques and queues in arrays)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.3 (Queues; resizing arrays)"
---

## Overview
A deque (double-ended queue, pronounced "deck") allows adding and removing at both ends in constant time. A circular queue, also called a ring buffer, stores a queue in a fixed-size array by letting the front and back indexes wrap around from the end of the array to the start, so freed slots are reused instead of wasted. Together they give fast two-ended access without shifting elements. They power sliding-window algorithms, undo/redo buffers, task schedulers and streaming data buffers.

## Intuition
Picture a circular running track with a fixed number of bays. Runners join at the back of the line and leave from the front, and when the line reaches the last bay it simply continues into bay zero, as long as that bay is free. Nobody has to shuffle down the line to make room. A deque is more like a corridor with doors at both ends: people can enter or leave through either.

## How It Works
A circular queue uses an array of capacity C, a `head` index (the front) and a count of stored items. Enqueue writes at index `(head + count) mod C` and increases count. Dequeue reads at `head`, advances head to `(head + 1) mod C` and decreases count. The modulo wraps indexes past the end back to 0. Because the array has fixed size, an enqueue when count equals C must fail, or the structure must be resized by copying into a larger array in order.

There is a classic puzzle: if you track only head and tail indexes, the state "empty" and the state "full" look identical, because head equals tail in both. Three fixes are common: keep a separate count, keep one slot permanently unused, or keep a boolean flag. Using a count, as above, is simplest.

A deque supports push_front, push_back, pop_front and pop_back. Implemented as a circular buffer, push_front moves head backward with `(head - 1 + C) mod C` and writes there. Python's `collections.deque` is built from linked blocks and offers O(1) append, appendleft, pop and popleft; C++'s std::deque offers the same with random access too.

Deques generalise both stacks and queues: restricting yourself to one end gives a stack, and using push_back with pop_front gives a queue. A well-known use is the sliding-window maximum: a deque keeps candidate indexes in decreasing order of value, popping from the back when a bigger value arrives and from the front when an index leaves the window.

Compared with a linked list, a ring buffer has better memory locality and no per-node allocation, but a fixed capacity unless it is resized.

## Worked Example
Take a ring buffer of capacity 4. Enqueue A, B, C: they go to indexes 0, 1, 2 (head 0, count 3). Dequeue returns A, so head becomes 1 and count 2. Enqueue D at index (1 + 2) mod 4 = 3 and enqueue E at index (1 + 3) mod 4 = 0, which reuses the slot freed by A. Now count is 4 and the buffer is full: slots are [E, B, C, D] with head at index 1, so the logical order is B, C, D, E. Another enqueue would fail. Dequeue returns B and head moves to index 2.

With a deque, pushing 1 and 2 at the back and 0 at the front gives [0, 1, 2]. Popping from the back returns 2 and popping from the front returns 0.

## Code
```python
from collections import deque


class RingBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = [None] * capacity
        self.head = 0
        self.count = 0

    def enqueue(self, value):
        if self.count == self.capacity:
            raise OverflowError("queue is full")
        self.data[(self.head + self.count) % self.capacity] = value
        self.count += 1

    def dequeue(self):
        if self.count == 0:
            raise IndexError("dequeue from empty queue")
        value = self.data[self.head]
        self.data[self.head] = None
        self.head = (self.head + 1) % self.capacity
        self.count -= 1
        return value

    def to_list(self):
        return [self.data[(self.head + i) % self.capacity] for i in range(self.count)]


rb = RingBuffer(4)
for v in "ABC":
    rb.enqueue(v)
assert rb.dequeue() == "A"
rb.enqueue("D")
rb.enqueue("E")                      # wraps around into the slot freed by A
assert rb.to_list() == ["B", "C", "D", "E"] and rb.count == 4
try:
    rb.enqueue("F")
except OverflowError:
    pass
else:
    raise AssertionError("expected a full buffer")
assert rb.dequeue() == "B" and rb.to_list() == ["C", "D", "E"]

d = deque()
d.append(1)
d.append(2)
d.appendleft(0)
assert list(d) == [0, 1, 2]
assert d.pop() == 2 and d.popleft() == 0 and list(d) == [1]


def window_max(values, k):
    """Sliding-window maximum with a deque of indexes (decreasing values)."""
    result, window = [], deque()
    for i, v in enumerate(values):
        while window and values[window[-1]] <= v:
            window.pop()
        window.append(i)
        if window[0] <= i - k:
            window.popleft()
        if i >= k - 1:
            result.append(values[window[0]])
    return result


assert window_max([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]
print("all checks passed")
```

```cpp
#include <cassert>
#include <deque>
#include <iostream>
#include <stdexcept>
#include <vector>

class RingBuffer {
public:
    explicit RingBuffer(std::size_t capacity) : data_(capacity) {}
    void enqueue(int v) {
        if (count_ == data_.size()) throw std::overflow_error("full");
        data_[(head_ + count_) % data_.size()] = v;
        ++count_;
    }
    int dequeue() {
        if (count_ == 0) throw std::underflow_error("empty");
        int v = data_[head_];
        head_ = (head_ + 1) % data_.size();
        --count_;
        return v;
    }
    std::size_t size() const { return count_; }
    std::vector<int> toVector() const {
        std::vector<int> out;
        for (std::size_t i = 0; i < count_; ++i) out.push_back(data_[(head_ + i) % data_.size()]);
        return out;
    }

private:
    std::vector<int> data_;
    std::size_t head_ = 0;
    std::size_t count_ = 0;
};

int main() {
    RingBuffer rb(4);
    for (int v : {1, 2, 3}) rb.enqueue(v);
    assert(rb.dequeue() == 1);
    rb.enqueue(4);
    rb.enqueue(5);  // wraps into the freed slot
    assert((rb.toVector() == std::vector<int>{2, 3, 4, 5}));
    bool full = false;
    try {
        rb.enqueue(6);
    } catch (const std::overflow_error&) {
        full = true;
    }
    assert(full);

    std::deque<int> d;
    d.push_back(1);
    d.push_back(2);
    d.push_front(0);
    assert(d.back() == 2 && d.front() == 0);
    d.pop_back();
    d.pop_front();
    assert(d.size() == 1 && d.front() == 1);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Enqueue and dequeue on a ring buffer are O(1), and so are push and pop at both ends of a deque. A fixed-capacity ring buffer uses O(C) space for capacity C and never shifts elements. Resizing a full ring buffer costs O(n) to copy the items in logical order, amortized O(1) with doubling. The sliding-window maximum with a deque runs in O(n) total time because each index is pushed and popped at most once, using O(k) extra space. Indexing into the middle of a linked-block deque is slower than in an array, whereas std::deque offers O(1) random access.

## Common Mistakes & Misconceptions
A classic bug is mixing up the empty and full states of a ring buffer when only head and tail indexes are kept: both look the same, so the queue reports "empty" when it is full or the reverse. Another is forgetting the modulo when advancing an index, which runs off the end of the array and raises an IndexError (or corrupts memory in C++). With backward moves, a negative index appears unless you add the capacity before taking the modulo. Students also use a plain list as a deque and call `insert(0, x)` or `pop(0)`, which are O(n). Finally, believing a circular queue can grow forever is wrong: unless it is resized, it has a fixed capacity and rejects enqueues when full.

## Builds On
This concept builds on Queue: the circular queue is a queue with a specific array layout designed to avoid the O(n) front-removal problem, and the deque extends the same first-in first-out ideas with both ends open. The enqueue and dequeue contract, underflow on an empty queue and use of head and tail positions all come directly from the queue concept.

## Leads To
Sliding window algorithms rely on the deque idea to keep a moving range efficiently, and monotonic stacks and queues are close relatives. Operating systems and networking code use ring buffers extensively, and breadth-first search can use a deque to support zero-one weighted variants.

## Check Yourself
**Q1.** How does a ring buffer compute the index for enqueue?
**A1.** It writes at (head + count) mod capacity.
**Q2.** Why is "head equals tail" ambiguous in a ring buffer?
**A2.** It can mean empty or full, so a count, a flag or a spare slot is needed to tell them apart.
**Q3.** Which deque operations does Python's collections.deque perform in O(1)?
**A3.** append, appendleft, pop and popleft.
