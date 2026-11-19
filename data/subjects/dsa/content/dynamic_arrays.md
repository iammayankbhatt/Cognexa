---
id: dynamic_arrays
name: "Dynamic Arrays"
cluster: linear
reviewed: false
sources:
  - "CLRS, Section 16.4 (Dynamic tables)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.3 (Resizing arrays)"
---

## Overview
A dynamic array is an array that grows (and optionally shrinks) automatically. You append items without declaring a size in advance, yet indexing stays constant time. Python's list, Java's ArrayList and C++'s std::vector are all dynamic arrays. They hide a simple trick: keep a plain array with some spare capacity, and when it fills up, allocate a bigger array and copy everything over.

## Intuition
Imagine a bookshelf that is always bought one size too big. You fill it up, and when the last slot is taken you buy a shelf twice as long, move every book across once, and carry on. Moving all the books is a hassle, but you do it rarely, and each move buys you a lot of free space. Most of the time, adding a book is just putting it in the next empty slot.

## How It Works
A dynamic array stores three things: a pointer to a block of memory, its size (how many items are in use) and its capacity (how many slots the block has). Appending writes the item at position size and increments size. If size equals capacity, the array first allocates a new block with a larger capacity, copies the existing items, frees the old block and then appends.

The growth rule matters. Growing by a constant factor, commonly 2 (Python uses roughly 1.125, C++ implementations often use 1.5 or 2), keeps the amortized cost of append at O(1). Growing by a fixed number of slots each time would copy everything every few appends and make n appends cost O(n squared).

Reading or writing by index is O(1) because the elements are contiguous. Inserting or removing in the middle costs O(n) because later elements shift. Removing from the end is O(1). Some implementations shrink the array when it becomes mostly empty, usually when it falls to a quarter full, so that alternating appends and removals near a boundary do not cause repeated resizes.

Because a resize allocates a new block, any pointer or reference into the old block becomes invalid. This is why a C++ iterator into a vector can dangle after push_back, and why Python programmers should not rely on the position of memory.

## Worked Example
Append 1, 2, 3, 4, 5 to an empty array that starts with capacity 1 and doubles.

Append 1: capacity 1, size 1. Append 2: full, allocate capacity 2, copy one item, size 2. Append 3: full, allocate capacity 4, copy two items, size 3. Append 4: room, size 4. Append 5: full, allocate capacity 8, copy four items, size 5. After five appends the array holds [1, 2, 3, 4, 5] with capacity 8, and a total of 1 + 2 + 4 = 7 items were copied.

Index 3 is read at once as the fourth item, 4. Removing the last item just decreases size to 4. Inserting 9 at index 1 shifts 2, 3, 4, 5 one step to the right first, so it costs O(n).

## Code
```python
class DynamicArray:
    def __init__(self):
        self.capacity = 1
        self.size = 0
        self.data = [None] * self.capacity
        self.copies = 0                       # counts element copies caused by resizing

    def append(self, value):
        if self.size == self.capacity:
            self._grow()
        self.data[self.size] = value
        self.size += 1

    def _grow(self):
        self.capacity *= 2
        new_data = [None] * self.capacity
        for i in range(self.size):
            new_data[i] = self.data[i]
            self.copies += 1
        self.data = new_data

    def get(self, index):
        if not 0 <= index < self.size:
            raise IndexError("index out of range")
        return self.data[index]

    def pop(self):
        if self.size == 0:
            raise IndexError("pop from empty array")
        self.size -= 1
        value = self.data[self.size]
        self.data[self.size] = None
        return value

    def insert(self, index, value):
        self.append(None)                     # make room (may resize)
        for i in range(self.size - 1, index, -1):
            self.data[i] = self.data[i - 1]   # shift right
        self.data[index] = value


arr = DynamicArray()
for v in [1, 2, 3, 4, 5]:
    arr.append(v)
assert arr.size == 5 and arr.capacity == 8 and arr.copies == 7
assert arr.get(3) == 4
assert arr.pop() == 5 and arr.size == 4
arr.insert(1, 9)
assert [arr.get(i) for i in range(arr.size)] == [1, 9, 2, 3, 4]

big = DynamicArray()
for v in range(10000):
    big.append(v)
assert big.copies < 2 * 10000                 # amortized O(1) appends
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

class DynamicArray {
public:
    void append(int value) {
        if (size_ == capacity_) grow();
        data_[size_++] = value;
    }
    int get(std::size_t i) const {
        assert(i < size_);
        return data_[i];
    }
    int pop() {
        assert(size_ > 0);
        return data_[--size_];
    }
    std::size_t size() const { return size_; }
    std::size_t capacity() const { return capacity_; }
    long long copies() const { return copies_; }

private:
    void grow() {
        std::size_t newCapacity = capacity_ * 2;
        std::vector<int> bigger(newCapacity);
        for (std::size_t i = 0; i < size_; ++i) {
            bigger[i] = data_[i];
            ++copies_;
        }
        data_ = std::move(bigger);
        capacity_ = newCapacity;
    }

    std::vector<int> data_ = std::vector<int>(1);
    std::size_t size_ = 0;
    std::size_t capacity_ = 1;
    long long copies_ = 0;
};

int main() {
    DynamicArray arr;
    for (int v = 1; v <= 5; ++v) arr.append(v);
    assert(arr.size() == 5 && arr.capacity() == 8 && arr.copies() == 7);
    assert(arr.get(3) == 4);
    assert(arr.pop() == 5 && arr.size() == 4);

    DynamicArray big;
    for (int v = 0; v < 10000; ++v) big.append(v);
    assert(big.copies() < 2 * 10000);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Indexing and setting are O(1). Appending is O(1) amortized and O(n) in the worst case when a resize happens. Removing the last item is O(1). Inserting or deleting at an arbitrary index is O(n) because of shifting. Searching an unsorted dynamic array is O(n). The memory used is O(n), between one and two times the number of stored items for a doubling strategy, because unused capacity is kept in reserve.

## Common Mistakes & Misconceptions
Students are often surprised that `list.append` is described as O(1) while an occasional append is slow: the cost is amortized, not constant every time. Another mistake is inserting at the front of a Python list in a loop (`list.insert(0, x)`), which is O(n) each time and makes the loop quadratic. In C++, keeping a pointer or iterator to a vector element and then calling push_back can leave a dangling reference after reallocation, giving crashes or garbage. People also assume that a list's capacity equals its length; the unused slots are real memory. Finally, using `list * n` to create a list of lists makes n references to the same inner list, a pointer aliasing bug rather than a dynamic array issue.

## Builds On
This concept builds on Arrays: a dynamic array is an array plus bookkeeping, and its constant-time indexing and contiguous layout come directly from there. It builds on Pointers & References because the growth step allocates a new block and redirects the array's internal pointer to it, which is also why old references can become invalid. It builds on Time Complexity & Big-O, since deciding whether doubling or fixed growth is acceptable requires comparing the total cost of n appends.

## Leads To
Amortized analysis proves the O(1) append bound formally and uses this structure as its standard example. Dynamic programming tables are usually dynamic arrays, stacks and queues are often built on them, and hash tables resize in exactly the same way.

## Check Yourself
**Q1.** What happens when you append to a full dynamic array?
**A1.** A larger block is allocated, the existing items are copied over, and then the new item is added.
**Q2.** Why is growing by a constant factor better than growing by a fixed number of slots?
**A2.** It makes resizes rare enough that the average cost per append stays constant.
**Q3.** What is the cost of inserting at the front of a dynamic array of n items?
**A3.** O(n), because every item must shift one place.
