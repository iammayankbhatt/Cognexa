---
id: binary_search
name: "Binary Search"
cluster: searching_hashing
reviewed: false
sources:
  - "CLRS, Exercise 2.3-5 (Binary search) and Section 2.3"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (Binary search)"
---

## Overview
Binary search finds a target in a sorted array by repeatedly comparing it with the middle element and discarding the half that cannot contain it. Because each step halves the search range, it needs only about log2 n comparisons, so a billion items take around 30 steps instead of a billion. The price is a precondition: the data must be sorted and must allow constant-time access by index.

## Intuition
This is the number-guessing game. I think of a number from 1 to 1000 and you guess 500. I say "higher", so you now know the answer lies in 501 to 1000 and guess 750. Each guess cuts the possibilities in half, so you can find any number in at most ten guesses. A dictionary lookup works the same way: you open it near the middle and decide which half to continue in.

## How It Works
Keep two indexes, low and high, that bound the part of the array that might still contain the target. While low is at most high, compute mid, compare the target with array[mid], and then: if equal, return mid; if the target is smaller, set high to mid - 1; if it is larger, set low to mid + 1. If the loop ends with low greater than high, the range is empty and the target is not present.

The loop invariant is that if the target is in the array, it lies within positions low to high. Each iteration keeps that true while shrinking the range, and the range must shrink because mid is excluded from the next range, which guarantees termination.

Details cause most bugs. The usual mid is `low + (high - low) // 2`; writing `(low + high) // 2` can overflow in fixed-width integer languages. Using `high = mid` or `low = mid` without the plus or minus one can loop forever. A variant using a half-open range [low, high) is common as well; whichever you choose, apply it consistently.

Binary search extends beyond exact matches. The lower bound returns the first position where the element is not less than the target (Python's `bisect_left`), which finds the insertion point and the first occurrence among duplicates. The upper bound returns the first position greater than the target (`bisect_right`). Binary search on the answer applies the same idea to any monotone yes/no question, such as "what is the smallest capacity that lets this job finish in time?", by halving a range of candidate answers rather than array indexes.

Preconditions to remember: the array must be sorted in the order assumed by the comparison, and the search is valid only with random access. On a linked list, reaching the middle costs O(n), which destroys the benefit.

## Worked Example
Search for 23 in [2, 5, 8, 12, 16, 23, 38, 56, 72, 91] (indexes 0 to 9).

low = 0, high = 9: mid = 4, value 16 is less than 23, so low = 5. low = 5, high = 9: mid = 7, value 56 is greater than 23, so high = 6. low = 5, high = 6: mid = 5, value 23 matches, so return 5. It took three comparisons for ten elements.

Search for 10. low = 0, high = 9: mid 4, value 16 greater, high = 3. low = 0, high = 3: mid 1, value 5 smaller, low = 2. low = 2, high = 3: mid 2, value 8 smaller, low = 3. low = 3, high = 3: mid 3, value 12 greater, high = 2. Now low is 3 and high is 2, the range is empty, and 10 is absent. The final low, 3, is the position where 10 could be inserted.

## Code
```python
def binary_search(values, target):
    low, high = 0, len(values) - 1
    while low <= high:
        mid = low + (high - low) // 2       # avoids overflow in fixed-width languages
        if values[mid] == target:
            return mid
        if values[mid] < target:
            low = mid + 1                   # discard the left half including mid
        else:
            high = mid - 1                  # discard the right half including mid
    return -1


def lower_bound(values, target):
    """First index whose value is >= target (the insertion point)."""
    low, high = 0, len(values)
    while low < high:
        mid = low + (high - low) // 2
        if values[mid] < target:
            low = mid + 1
        else:
            high = mid
    return low


def smallest_capacity(weights, days):
    """Binary search on the answer: least ship capacity to deliver all weights in order in `days`."""
    def feasible(cap):
        used, current = 1, 0
        for w in weights:
            if current + w > cap:
                used += 1
                current = 0
            current += w
        return used <= days

    low, high = max(weights), sum(weights)
    while low < high:
        mid = (low + high) // 2
        if feasible(mid):
            high = mid
        else:
            low = mid + 1
    return low


data = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
assert binary_search(data, 23) == 5
assert binary_search(data, 10) == -1
assert binary_search(data, 2) == 0 and binary_search(data, 91) == 9
assert binary_search([], 1) == -1 and binary_search([7], 7) == 0
assert lower_bound(data, 10) == 3 and lower_bound(data, 1) == 0 and lower_bound(data, 100) == 10
assert lower_bound([1, 2, 2, 2, 3], 2) == 1               # first of the duplicates
assert smallest_capacity([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5) == 15

import bisect

assert lower_bound(data, 38) == bisect.bisect_left(data, 38)
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

int binarySearch(const std::vector<int>& v, int target) {
    int low = 0, high = static_cast<int>(v.size()) - 1;
    while (low <= high) {
        int mid = low + (high - low) / 2;  // avoids overflow of low + high
        if (v[mid] == target) return mid;
        if (v[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}

int lowerBound(const std::vector<int>& v, int target) {
    int low = 0, high = static_cast<int>(v.size());
    while (low < high) {
        int mid = low + (high - low) / 2;
        if (v[mid] < target) low = mid + 1;
        else high = mid;
    }
    return low;
}

int main() {
    std::vector<int> data = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};
    assert(binarySearch(data, 23) == 5);
    assert(binarySearch(data, 10) == -1);
    assert(binarySearch({}, 1) == -1);
    assert(lowerBound(data, 10) == 3 && lowerBound(data, 100) == 10);
    std::vector<int> dups = {1, 2, 2, 2, 3};
    assert(lowerBound(dups, 2) == 1);
    assert(lowerBound(data, 38) == std::lower_bound(data.begin(), data.end(), 38) - data.begin());

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Time is O(log n) in the worst and average case, because the range halves every step, and O(1) in the best case when the first middle element matches. Space is O(1) for the iterative version and O(log n) for a recursive one because of the call stack. For comparison, linear search is O(n): at n = one million, binary search needs about 20 comparisons versus up to a million. Sorting first costs O(n log n), so for a single search on unsorted data a linear scan is cheaper, while many searches amortise the sort.

## Common Mistakes & Misconceptions
The famous symptom is an infinite loop, caused by updates such as `low = mid` or `high = mid` in the closed-range version, which fail to shrink the range when low and high are adjacent. Off-by-one errors in the loop condition (`<` versus `<=`) cause missed matches at the boundaries or an out-of-range read. In fixed-width languages `(low + high) / 2` can overflow for huge arrays. Applying binary search to unsorted data returns wrong answers without any error, which is the nastiest failure. Students also forget duplicates: plain binary search returns any matching index, not necessarily the first, so use a lower bound when order matters. Finally, believing binary search works on a linked list ignores the O(n) cost of reaching the middle.

## Builds On
This concept builds on Arrays: it relies on constant-time access to any index, so that jumping to the middle is a single step, and on the zero-based index range. It builds on Time Complexity & Big-O: the argument that the work is logarithmic uses the halving count introduced there, and the comparison with linear search is a growth-class comparison.

## Leads To
Binary Search Trees store data in a tree shaped like the sequence of binary-search decisions, so insertion and deletion stay fast. Binary search on the answer solves optimisation problems by halving a range of candidates, and balanced tree and database index structures all follow the same halving logic.

## Check Yourself
**Q1.** What must be true of the array before binary search can be used?
**A1.** It must be sorted (consistently with the comparison) and allow constant-time access by index.
**Q2.** About how many comparisons does binary search need for 1,000,000 items?
**A2.** About 20, since log2 of one million is about 20.
**Q3.** Why must mid be excluded from the next range?
**A3.** Setting low = mid + 1 or high = mid - 1 guarantees the range shrinks every iteration, so the loop terminates.
