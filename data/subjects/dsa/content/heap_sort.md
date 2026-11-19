---
id: heap_sort
name: "Heap Sort"
cluster: sorting
reviewed: false
sources:
  - "CLRS, Chapter 6 (Heapsort), Sections 6.2 to 6.4"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.4 (Heapsort)"
---

## Overview
Heap sort sorts an array in place in O(n log n) time in every case. It treats the array as a binary max-heap, a tree stored in the array where every parent is at least as large as its children, so the maximum sits at index 0. It builds that heap, then repeatedly swaps the maximum to the end of the array, shrinks the heap by one and restores the heap property. It combines the guaranteed running time of merge sort with the in-place behaviour of quick sort, at the price of not being stable and being slower in practice than a good quick sort.

## Intuition
Picture a tournament bracket where the winner of every match is the larger number. The overall champion is at the top. Heap sort repeatedly removes the champion, puts them at the end of the finishing order, and then replays only the matches along one path to crown the next champion. Each replay touches only about log n matches, and there are n champions to crown, so the whole job takes n log n steps.

## How It Works
A binary heap is stored in an array with index arithmetic instead of pointers. The children of the node at index i are at 2i + 1 and 2i + 2, and its parent is at (i - 1) // 2. In a max-heap every node is at least as large as its children. The binary heap concept covers the structure in detail; heap sort only needs two operations.

Sift-down (heapify) restores the heap property at index i, assuming both its subtrees are already heaps: compare the node with its larger child and, if the child is bigger, swap them and continue downward from the child's position. It takes O(log n) time because it follows one root-to-leaf path.

Step one, building the heap: apply sift-down to every non-leaf node starting at the last parent, index n // 2 - 1, and moving back to index 0. Counting carefully shows that most nodes are near the leaves and have little to sift, so building takes O(n) total, not O(n log n).

Step two, the sorting phase: for end from n - 1 down to 1, swap the root (the current maximum) with the element at position end, so the maximum lands in its final place at the end; reduce the heap size to end, and sift the new root down to restore the heap. After n - 1 rounds the array is sorted in ascending order. Each round costs O(log n), so the sorting phase is O(n log n).

Because the sifts follow one path and heap_sort uses no recursion beyond a simple loop, it needs O(1) extra space. It is not stable: swapping the root with the last element moves equal keys past each other. It has poorer cache behaviour than quick sort because it jumps between parents and children far apart in memory, which is why quick sort usually wins in practice. Heap sort's guarantee is useful as a fallback: introsort switches to heap sort when quick sort recursion gets too deep.

## Worked Example
Sort [4, 10, 3, 5, 1].

Build the max-heap: n = 5, last parent index 1. Sift-down at index 1 (value 10): its children are 5 and 1, and 10 is larger, so nothing moves. Sift-down at index 0 (value 4): children are 10 and 3, the larger is 10, so swap: [10, 4, 3, 5, 1]. Continue at index 1 (value 4): children are 5 and 1, so swap with 5: [10, 5, 3, 4, 1]. The heap is built.

Sort phase: swap root 10 with the last item 1: [1, 5, 3, 4, 10], heap size 4; sift 1 down: swap with 5 to [5, 1, 3, 4, 10], then with 4: [5, 4, 3, 1, 10]. Swap root 5 with index 3: [1, 4, 3, 5, 10], heap size 3; sift down: [4, 1, 3, 5, 10]. Swap root 4 with index 2: [3, 1, 4, 5, 10]; sift down: [3, 1, 4, 5, 10] is unchanged since 3 is bigger than 1. Swap root 3 with index 1: [1, 3, 4, 5, 10]. Sorted.

## Code
```python
def sift_down(a, i, size):
    while True:
        left, right, largest = 2 * i + 1, 2 * i + 2, i
        if left < size and a[left] > a[largest]:
            largest = left
        if right < size and a[right] > a[largest]:
            largest = right
        if largest == i:
            return
        a[i], a[largest] = a[largest], a[i]      # move the smaller parent down
        i = largest


def build_max_heap(a):
    for i in range(len(a) // 2 - 1, -1, -1):     # last parent down to the root
        sift_down(a, i, len(a))


def heap_sort(a):
    a = list(a)
    build_max_heap(a)
    for end in range(len(a) - 1, 0, -1):
        a[0], a[end] = a[end], a[0]              # the maximum goes to its final place
        sift_down(a, 0, end)                     # restore the heap on the shrunken prefix
    return a


def is_max_heap(a):
    return all(a[(i - 1) // 2] >= a[i] for i in range(1, len(a)))


h = [4, 10, 3, 5, 1]
build_max_heap(h)
assert h == [10, 5, 3, 4, 1] and is_max_heap(h)
assert heap_sort([4, 10, 3, 5, 1]) == [1, 3, 4, 5, 10]
assert heap_sort([]) == [] and heap_sort([2]) == [2] and heap_sort([2, 1]) == [1, 2]
assert heap_sort([3, 3, 1, 2, 2]) == [1, 2, 2, 3, 3]

import random

random.seed(10)
for _ in range(200):
    arr = [random.randint(-30, 30) for _ in range(random.randint(0, 40))]
    assert heap_sort(arr) == sorted(arr)
    copy = list(arr)
    build_max_heap(copy)
    assert is_max_heap(copy)
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

void siftDown(std::vector<int>& a, std::size_t i, std::size_t size) {
    while (true) {
        std::size_t left = 2 * i + 1, right = 2 * i + 2, largest = i;
        if (left < size && a[left] > a[largest]) largest = left;
        if (right < size && a[right] > a[largest]) largest = right;
        if (largest == i) return;
        std::swap(a[i], a[largest]);
        i = largest;
    }
}

void heapSort(std::vector<int>& a) {
    for (std::size_t i = a.size() / 2; i-- > 0;) siftDown(a, i, a.size());  // build the heap
    for (std::size_t end = a.size(); end-- > 1;) {
        std::swap(a[0], a[end]);  // maximum to its final place
        siftDown(a, 0, end);
    }
}

int main() {
    std::vector<int> a = {4, 10, 3, 5, 1};
    heapSort(a);
    assert((a == std::vector<int>{1, 3, 4, 5, 10}));

    std::vector<int> b = {3, 3, 1, 2, 2};
    heapSort(b);
    assert((b == std::vector<int>{1, 2, 2, 3, 3}));

    std::vector<int> empty;
    heapSort(empty);
    assert(empty.empty());

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Building the heap takes O(n) time. The sorting phase does n - 1 extractions, each a sift-down of O(log n), so heap sort is Theta(n log n) in the best, average and worst case. Extra space is O(1): it sorts in place with only a few index variables. It is not stable. Compared with quick sort it has a better worst case but, because of scattered memory access, is typically about two to three times slower on large arrays; compared with merge sort it saves the O(n) buffer but gives up stability.

## Common Mistakes & Misconceptions
A frequent symptom is a result that is almost but not quite sorted, caused by sifting down over the whole array instead of only the shrunken heap, so already placed maxima get disturbed; the `size` parameter must be reduced each round. Off-by-one errors in the index formulas (children at 2i + 1 and 2i + 2 for zero-based arrays, not 2i and 2i + 1) produce wrong or out-of-range results. Students start the build phase from index 0 instead of the last parent, or believe that building a heap costs O(n log n) when a careful count gives O(n). They also assume heap sort is stable or that it is the fastest in practice. Using a min-heap and expecting ascending output in place needs the opposite scheme: a max-heap yields ascending order when extracted to the end.

## Builds On
This concept builds on Binary Heap, because the sort operates on the array representation of a max-heap and relies on its heap property, index arithmetic and sift-down operation; without that structure there is nothing to extract the maximum from efficiently. It builds on Elementary Sorts, since selection sort is the quadratic version of the same idea, repeatedly selecting the largest remaining element, and the heap makes each selection O(log n) instead of O(n).

## Leads To
Introsort combines quick sort with heap sort as a guaranteed fallback. Priority queues use the same sift operations, and partial heap sort finds the top k elements in O(n log k) time, a pattern used in selection problems.

## Check Yourself
**Q1.** Where is the maximum of a max-heap stored?
**A1.** At index 0, the root.
**Q2.** How long does building a heap from n items take?
**A2.** O(n), because most nodes are near the leaves and need little sifting.
**Q3.** Is heap sort stable, and does it use extra memory?
**A3.** It is not stable and it uses O(1) extra memory (in place).
