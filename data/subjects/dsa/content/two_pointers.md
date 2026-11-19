---
id: two_pointers
name: "Two Pointers"
cluster: searching_hashing
reviewed: false
sources:
  - "Competitive Programmer's Handbook (Laaksonen), Section 8.1 (Two pointers method)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.4 (3-sum and 2-sum on sorted arrays)"
---

## Overview
The two pointers technique solves array and string problems by moving two indexes through the data in a coordinated way, instead of using nested loops over every pair. Often one pointer starts at each end and they move toward each other; sometimes both start at the left and move in the same direction at different speeds. Because each pointer only moves forward (or only inward), the whole scan takes linear time, turning many O(n squared) brute-force ideas into O(n) solutions.

## Intuition
Imagine two people searching a long hallway of numbered doors for a pair of doors whose numbers add up to a target. One starts at the lowest door and one at the highest. If the sum is too small, the person at the low end must move up to a bigger number; if it is too big, the person at the high end must move down. Each step rules out a whole group of pairs at once, so they meet in the middle after at most n steps instead of checking every pair.

## How It Works
Opposite-direction pointers need ordered data. Put `left` at the first index and `right` at the last. Compute something from the two values, such as their sum, and decide which pointer to move using what the comparison tells you. For the pair-sum problem on a sorted array, if `values[left] + values[right]` is less than the target, no pair that uses `left` with any remaining right value can work (every remaining right value is no larger), so `left` moves up; if the sum is greater, `right` moves down. The loop stops when the pointers meet.

Same-direction pointers use a slow and a fast index. The classic example is removing duplicates from a sorted array in place: `fast` scans every element and `slow` marks where the next unique value should be written. When `values[fast]` differs from `values[slow]`, increase `slow` and copy the value there. The result is the unique elements packed at the front and the new length is `slow + 1`.

A related pattern uses the pointers as the boundaries of a region, as in finding the container that holds the most water between two vertical lines: start with the widest container and move the pointer at the shorter line inward, because only a taller line can improve the area.

Why it works: each move discards candidates that provably cannot be part of an answer, so correctness comes from an argument about what is safe to discard, not from trying everything. Always state that argument. The technique needs a monotone property: sorted order for pair sums, or the fact that moving a pointer in one direction only increases or only decreases the quantity you care about.

Edge cases to check: an empty array, a single element, pointers that cross, duplicates, and several valid answers (the algorithm returns one of them).

## Worked Example
Find two numbers in [1, 2, 4, 7, 11, 15] that add up to 15.

left = 0 (value 1), right = 5 (value 15): the sum 16 is too big, so right moves to 4. Now 1 + 11 = 12 is too small, so left moves to 1. Then 2 + 11 = 13 is too small, so left moves to 2. Now 4 + 11 = 15, which matches: the pair is at indexes 2 and 4. Only four sum checks were needed, rather than up to 15 for all pairs.

Remove duplicates from [1, 1, 2, 2, 2, 3]. slow = 0. fast = 1 sees 1, equal to values[0], skip. fast = 2 sees 2, which differs, so slow = 1 and values[1] = 2. fast = 3 and 4 see 2, skip. fast = 5 sees 3, so slow = 2 and values[2] = 3. The unique prefix is [1, 2, 3], length 3.

## Code
```python
def two_sum_sorted(values, target):
    left, right = 0, len(values) - 1
    while left < right:
        s = values[left] + values[right]
        if s == target:
            return left, right
        if s < target:
            left += 1             # need a bigger sum: move the low pointer up
        else:
            right -= 1            # need a smaller sum: move the high pointer down
    return None


def remove_duplicates(values):
    """In place on a sorted list; returns the new length."""
    if not values:
        return 0
    slow = 0
    for fast in range(1, len(values)):
        if values[fast] != values[slow]:
            slow += 1
            values[slow] = values[fast]
    return slow + 1


def max_water(heights):
    left, right, best = 0, len(heights) - 1, 0
    while left < right:
        best = max(best, min(heights[left], heights[right]) * (right - left))
        if heights[left] < heights[right]:
            left += 1             # the shorter side limits the area; only moving it can help
        else:
            right -= 1
    return best


assert two_sum_sorted([1, 2, 4, 7, 11, 15], 15) == (2, 4)
assert two_sum_sorted([1, 2, 3], 100) is None
assert two_sum_sorted([], 3) is None and two_sum_sorted([5], 5) is None

data = [1, 1, 2, 2, 2, 3]
n = remove_duplicates(data)
assert n == 3 and data[:n] == [1, 2, 3]
assert remove_duplicates([]) == 0

assert max_water([1, 8, 6, 2, 5, 4, 8, 3, 7]) == 49

# Cross-check against the O(n^2) brute force.
import random

random.seed(2)
for _ in range(200):
    arr = sorted(random.randint(0, 30) for _ in range(random.randint(0, 12)))
    target = random.randint(0, 60)
    brute = any(arr[i] + arr[j] == target for i in range(len(arr)) for j in range(i + 1, len(arr)))
    assert (two_sum_sorted(arr, target) is not None) == brute
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <utility>
#include <vector>

std::pair<int, int> twoSumSorted(const std::vector<int>& v, int target) {
    int left = 0, right = static_cast<int>(v.size()) - 1;
    while (left < right) {
        int s = v[left] + v[right];
        if (s == target) return {left, right};
        if (s < target) ++left;
        else --right;
    }
    return {-1, -1};
}

int removeDuplicates(std::vector<int>& v) {
    if (v.empty()) return 0;
    std::size_t slow = 0;
    for (std::size_t fast = 1; fast < v.size(); ++fast) {
        if (v[fast] != v[slow]) v[++slow] = v[fast];
    }
    return static_cast<int>(slow) + 1;
}

int maxWater(const std::vector<int>& h) {
    int left = 0, right = static_cast<int>(h.size()) - 1, best = 0;
    while (left < right) {
        best = std::max(best, std::min(h[left], h[right]) * (right - left));
        if (h[left] < h[right]) ++left;
        else --right;
    }
    return best;
}

int main() {
    assert((twoSumSorted({1, 2, 4, 7, 11, 15}, 15) == std::make_pair(2, 4)));
    assert((twoSumSorted({1, 2, 3}, 100) == std::make_pair(-1, -1)));

    std::vector<int> data = {1, 1, 2, 2, 2, 3};
    int n = removeDuplicates(data);
    assert(n == 3 && data[0] == 1 && data[1] == 2 && data[2] == 3);

    assert(maxWater({1, 8, 6, 2, 5, 4, 8, 3, 7}) == 49);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Each pointer moves at most n steps and never goes backward, so the scan is O(n) time, compared with O(n squared) for checking every pair. Space is O(1) because only two indexes are kept, and in-place variants such as duplicate removal modify the input instead of allocating a new array. If the input is not sorted and the method requires order, sorting first adds O(n log n), which still beats the quadratic brute force and dominates the total running time.

## Common Mistakes & Misconceptions
A common bug is using the opposite-direction technique on unsorted data, where moving a pointer no longer proves that candidates can be discarded, so correct pairs are missed with no error. Off-by-one mistakes in the loop condition (`left <= right` instead of `left < right`) let a pointer pair with itself, for example reporting index 3 and 3 as a valid pair. Students move both pointers at once, or the wrong one, because they never justified the discard rule. In the duplicates problem, forgetting to return `slow + 1` (the length, not the last index) or reading past the new length gives wrong results. Another frequent mistake is mutating the list in place and then trusting values beyond the returned length, which still hold stale data.

## Builds On
This concept builds on Arrays: both pointers are indexes into an array, and the technique depends on constant-time access to values at arbitrary positions and on in-place writes without shifting. The idea of sorted order and the valid index range from arrays is what lets the pointers stop safely when they meet.

## Leads To
Sliding window extends the idea with two pointers that bound a moving window over a sequence. Quick sort uses opposite-direction pointers in its partition step, and merging two sorted lists, the 3-sum problem and cycle detection in linked lists all rely on two coordinated indexes.

## Check Yourself
**Q1.** In pair-sum on a sorted array, which pointer moves when the sum is too small?
**A1.** The left pointer moves up, because a larger value is needed.
**Q2.** Why is the whole scan O(n)?
**A2.** Each pointer only moves in one direction and never revisits an index, so there are at most n moves in total.
**Q3.** Why does the opposite-direction method need sorted input?
**A3.** Sortedness is what proves that moving a pointer discards only pairs that cannot work.
