---
id: quick_sort
name: "Quick Sort"
cluster: sorting
reviewed: false
sources:
  - "CLRS, Chapter 7 (Quicksort)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.3 (Quicksort)"
---

## Overview
Quick sort sorts by choosing a pivot element, partitioning the array so that everything smaller than the pivot is on its left and everything larger is on its right, and then sorting the two sides recursively. After partitioning the pivot is already in its final position. Quick sort sorts in place, usually beats other O(n log n) sorts in practice because of its tight inner loop and cache-friendly access, and has an O(n log n) average time. Its weakness is a quadratic worst case when pivots are chosen badly.

## Intuition
Imagine sorting a class by height. Pick a student as the pivot and ask everyone shorter to stand on the left and everyone taller on the right. The pivot is now exactly where they belong. Then repeat the process independently for each side, each time choosing a new pivot. If the pivots land near the middle each time the groups halve quickly. If you keep choosing the shortest person as pivot, one side is empty and the other has nearly everyone, so progress is slow.

## How It Works
The algorithm picks a pivot, partitions, and recurses on the two sides. Partitioning is the work. The Lomuto scheme uses the last element as pivot and a boundary index i for the "smaller than pivot" region: scan j from the start; whenever `a[j] < pivot`, swap it into position i and increase i; finally swap the pivot into position i. The Hoare scheme uses two indexes moving toward each other from both ends, swapping out-of-place pairs, which does fewer swaps. Both run in O(n) per partition and use O(1) extra space.

The choice of pivot decides performance. If each partition splits the range roughly evenly, there are about log2 n levels of O(n) work, giving O(n log n). If the pivot is always the smallest or largest element, which happens for already sorted input when you pick the first or last element, the sizes shrink by only one each time: T(n) = T(n - 1) + n, which is O(n squared) with recursion depth n that can overflow the call stack. Remedies: pick a random pivot, or the median of the first, middle and last elements, so that no fixed input is reliably bad. With a random pivot the expected running time is O(n log n) for every input.

Duplicates need care. If many elements equal the pivot, the basic scheme can degrade; the three-way partition (smaller, equal, larger) handles them efficiently. To bound the stack, recurse into the smaller side and loop on the larger, which keeps the depth at O(log n).

Quick sort is not stable, because partitioning swaps elements across long distances. It is in place apart from the recursion stack. Quickselect, a related algorithm, uses the same partition to find the kth smallest element in expected O(n) time by recursing into only one side.

## Worked Example
Partition [3, 8, 2, 5, 1, 4] with the last element, 4, as pivot using the Lomuto scheme.

i = 0. j = 0: 3 < 4, swap with itself, i = 1. j = 1: 8 is not smaller. j = 2: 2 < 4, swap a[1] and a[2]: [3, 2, 8, 5, 1, 4], i = 2. j = 3: 5 is not smaller. j = 4: 1 < 4, swap a[2] and a[4]: [3, 2, 1, 5, 8, 4], i = 3. Finally swap the pivot into position 3: [3, 2, 1, 4, 8, 5]. Everything left of index 3 is smaller than 4 and everything to the right is larger. Recurse on [3, 2, 1] and [8, 5] to finish.

Worst case: [1, 2, 3, 4, 5] with the last element as pivot. Pivot 5 ends in place with all others on the left, leaving a subproblem of size 4, then 3, and so on: n(n-1)/2 comparisons.

## Code
```python
import random


def partition(a, lo, hi):
    """Lomuto partition of a[lo..hi] around a[hi]; returns the pivot's final index."""
    pivot = a[hi]
    i = lo
    for j in range(lo, hi):
        if a[j] < pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i], a[hi] = a[hi], a[i]
    return i


def quick_sort(a, lo=0, hi=None, rng=random):
    if hi is None:
        hi = len(a) - 1
    while lo < hi:
        r = rng.randint(lo, hi)                # random pivot defeats adversarial inputs
        a[r], a[hi] = a[hi], a[r]
        p = partition(a, lo, hi)
        if p - lo < hi - p:                    # recurse into the smaller side, loop on the larger
            quick_sort(a, lo, p - 1, rng)
            lo = p + 1
        else:
            quick_sort(a, p + 1, hi, rng)
            hi = p - 1


def quick_select(a, k):
    """k-th smallest (0-based) in expected O(n) time."""
    a = list(a)
    lo, hi = 0, len(a) - 1
    while True:
        r = random.randint(lo, hi)
        a[r], a[hi] = a[hi], a[r]
        p = partition(a, lo, hi)
        if p == k:
            return a[p]
        if p < k:
            lo = p + 1
        else:
            hi = p - 1


data = [3, 8, 2, 5, 1, 4]
idx = partition(data, 0, len(data) - 1)
assert data == [3, 2, 1, 4, 8, 5] and idx == 3

for arr in ([], [1], [2, 1], list(range(50)), list(range(50, 0, -1)), [5] * 20):
    copy = list(arr)
    quick_sort(copy)
    assert copy == sorted(arr)                  # sorted, reversed and all-equal inputs work

random.seed(9)
for _ in range(200):
    arr = [random.randint(-20, 20) for _ in range(random.randint(0, 40))]
    copy = list(arr)
    quick_sort(copy)
    assert copy == sorted(arr)

assert quick_select([7, 10, 4, 3, 20, 15], 2) == 7
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <vector>

int partitionRange(std::vector<int>& a, int lo, int hi) {
    int pivot = a[hi];
    int i = lo;
    for (int j = lo; j < hi; ++j) {
        if (a[j] < pivot) std::swap(a[i++], a[j]);
    }
    std::swap(a[i], a[hi]);
    return i;
}

void quickSort(std::vector<int>& a, int lo, int hi) {
    while (lo < hi) {
        int r = lo + std::rand() % (hi - lo + 1);  // random pivot
        std::swap(a[r], a[hi]);
        int p = partitionRange(a, lo, hi);
        if (p - lo < hi - p) {
            quickSort(a, lo, p - 1);
            lo = p + 1;
        } else {
            quickSort(a, p + 1, hi);
            hi = p - 1;
        }
    }
}

int main() {
    std::vector<int> data = {3, 8, 2, 5, 1, 4};
    int idx = partitionRange(data, 0, static_cast<int>(data.size()) - 1);
    assert(idx == 3 && (data == std::vector<int>{3, 2, 1, 4, 8, 5}));

    std::vector<int> sortedInput;
    for (int i = 0; i < 1000; ++i) sortedInput.push_back(i);
    std::vector<int> expected = sortedInput;
    quickSort(sortedInput, 0, static_cast<int>(sortedInput.size()) - 1);
    assert(sortedInput == expected);  // already-sorted input is fine with random pivots

    std::vector<int> mixed = {5, 3, 5, 1, 9, 1, 0};
    quickSort(mixed, 0, static_cast<int>(mixed.size()) - 1);
    assert((mixed == std::vector<int>{0, 1, 1, 3, 5, 5, 9}));

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Best and average case: O(n log n) time, when partitions are reasonably balanced; with a random pivot the expected time is O(n log n) for every input. Worst case: O(n squared), when each pivot is the minimum or maximum, as for sorted input with a naive first or last pivot. Space: O(1) extra for the partitioning plus the recursion stack, O(log n) on average and O(log n) guaranteed if you always recurse into the smaller side. Quick sort is not stable. Quickselect finds the kth smallest in expected O(n) time. In practice quick sort often beats merge sort on arrays because it does fewer memory writes and has good cache behaviour.

## Common Mistakes & Misconceptions
The headline symptom is RecursionError or a stack overflow on sorted or all-equal input, from always picking the first or last element as pivot and recursing n levels deep, combined with the quadratic running time. Students forget that the pivot is in its final place after partitioning and recurse on it again, or recurse on `[lo, p]` instead of `[lo, p - 1]`, causing infinite recursion. Off-by-one errors in the partition boundaries are frequent. Many assume quick sort is always O(n log n); the worst case is quadratic unless pivots are randomised. Another misconception is that it is stable: swapping across distances reorders equal elements. People also forget duplicates, where the simple scheme performs poorly on all-equal data unless three-way partitioning is used.

## Builds On
This concept builds on Divide & Conquer: partitioning is the divide step and the combine step is empty, because after both sides are sorted the whole array is already in order. It builds on Elementary Sorts, since the partition loop is a single selection-like scan and small subarrays are often finished with insertion sort, and since understanding stability and in-place operation from the elementary sorts shows what quick sort gives up and gains.

## Leads To
Quickselect uses the same partition to find medians and percentiles in linear expected time. Introsort, the sort behind C++'s std::sort, starts with quick sort and switches to heap sort when recursion gets too deep, giving a guaranteed O(n log n) bound. The partition idea also appears in the two-way and three-way splitting used in many selection and grouping problems.

## Check Yourself
**Q1.** What is true of the array after one partition around a pivot?
**A1.** The pivot is in its final position, with smaller elements to its left and larger ones to its right.
**Q2.** When does quick sort take O(n squared) time?
**A2.** When pivots are consistently the minimum or maximum, such as the last element of already sorted input.
**Q3.** Why is a random pivot helpful?
**A3.** No fixed input can reliably force bad splits, so the expected running time is O(n log n) for every input.
