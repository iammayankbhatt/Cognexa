---
id: divide_and_conquer
name: "Divide & Conquer"
cluster: sorting
reviewed: false
sources:
  - "CLRS, Section 2.3 (Designing algorithms) and Chapter 4 (Divide-and-Conquer)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.2 (Mergesort)"
---

## Overview
Divide and conquer is a problem-solving strategy with three steps. Divide the problem into smaller subproblems of the same kind, conquer each subproblem by solving it recursively (directly, once it is small enough), and combine the answers into a solution for the original problem. When the subproblems are independent and the dividing and combining are cheap, the strategy often turns a slow quadratic method into an O(n log n) one, as in merge sort, or an O(log n) one, as in binary search.

## Intuition
Counting the votes in a huge election by hand is hopeless for one person, but easy if you split the ballots into piles, give each pile to a different volunteer who may split it further, and then add up the sub-totals. Each volunteer faces the same task on a smaller pile, and the final combine step is just addition. The work is divided evenly, and the number of splitting levels is small because the piles shrink geometrically.

## How It Works
A divide-and-conquer algorithm is a recursive function with a base case for small inputs. The recursive case splits the input, typically in halves, calls itself on each part, and combines the results. Its running time follows a recurrence of the form T(n) = a T(n/b) + f(n): a subproblems, each of size n/b, plus f(n) work to divide and combine. The Master Theorem from the recurrence relations concept gives the solution; for example splitting into two halves with linear combine work gives T(n) = 2T(n/2) + n, which is Theta(n log n).

Examples show the range. Merge sort divides the array in half, sorts both halves, and combines by merging. Quick sort divides by partitioning around a pivot and has no combine step. Binary search divides to a single half (a = 1) and discards the other, with constant combine work, giving O(log n). Fast exponentiation computes x to the power n by computing x to the power n/2 once and squaring it, which needs only O(log n) multiplications instead of n. The maximum-subarray problem and closest pair of points also divide and then combine across the split. Strassen's algorithm multiplies matrices with seven recursive multiplications instead of eight.

Key points to check when designing one: the subproblems should be independent (if they overlap and repeat, dynamic programming is better, as with Fibonacci); the base case must stop the recursion; the split should be reasonably balanced, since an unbalanced split such as 1 versus n - 1 turns T(n) = 2T(n/2) + n into T(n) = T(n - 1) + n, which is quadratic; and the combine step must be correct, because it carries the real difficulty.

Divide and conquer parallelises well because independent subproblems can run on different processors. In practice, algorithms switch to a simple method, such as insertion sort, below a small size threshold, since the recursion overhead outweighs the benefit on tiny inputs.

## Worked Example
Compute 2 to the power 10 by divide and conquer. power(2, 10) needs power(2, 5), squared. power(2, 5) is odd, so it needs power(2, 2), squared, times 2. power(2, 2) needs power(2, 1) squared. power(2, 1) needs power(2, 0), squared, times 2. power(2, 0) is the base case, 1. Unwinding: power(2, 1) = 1 * 1 * 2 = 2, power(2, 2) = 4, power(2, 5) = 4 * 4 * 2 = 32, power(2, 10) = 32 * 32 = 1024. Only 4 recursive calls were needed instead of 10 multiplications, and for an exponent of one million about 20 calls suffice.

Find the maximum of [4, 9, 2, 7] by divide and conquer: split into [4, 9] and [2, 7]; their maxima are 9 and 7; the combine step takes the larger, 9. The recurrence is T(n) = 2T(n/2) + 1, which is Theta(n): no faster than a simple loop, a reminder that dividing does not always help.

## Code
```python
def power(x, n):
    if n == 0:
        return 1                               # base case
    half = power(x, n // 2)                    # solve one half-size subproblem once
    return half * half if n % 2 == 0 else half * half * x


calls = 0


def power_counted(x, n):
    global calls
    calls += 1
    if n == 0:
        return 1
    half = power_counted(x, n // 2)
    return half * half if n % 2 == 0 else half * half * x


def max_dc(values, lo, hi):
    if lo == hi:
        return values[lo]                      # base case: one element
    mid = (lo + hi) // 2
    return max(max_dc(values, lo, mid), max_dc(values, mid + 1, hi))   # combine


def count_inversions(values):
    """Merge-sort based inversion count: divide, conquer both halves, combine across the split."""
    if len(values) <= 1:
        return values, 0
    mid = len(values) // 2
    left, a = count_inversions(values[:mid])
    right, b = count_inversions(values[mid:])
    merged, cross, i, j = [], 0, 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            cross += len(left) - i             # every remaining left item exceeds right[j]
            j += 1
    merged += left[i:] + right[j:]
    return merged, a + b + cross


assert power(2, 10) == 1024 and power(3, 5) == 243 and power(5, 0) == 1
power_counted(2, 1000000)
assert calls == 21                              # about log2(10^6) + 1 calls, not a million
assert max_dc([4, 9, 2, 7], 0, 3) == 9
assert count_inversions([2, 4, 1, 3, 5])[1] == 3
assert count_inversions([5, 4, 3, 2, 1])[1] == 10
assert count_inversions([1, 2, 3])[1] == 0

import random

random.seed(7)
for _ in range(100):
    arr = [random.randint(0, 9) for _ in range(random.randint(0, 12))]
    brute = sum(1 for i in range(len(arr)) for j in range(i + 1, len(arr)) if arr[i] > arr[j])
    assert count_inversions(arr)[1] == brute
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

long long power(long long x, int n) {
    if (n == 0) return 1;
    long long half = power(x, n / 2);
    return n % 2 == 0 ? half * half : half * half * x;
}

int maxDC(const std::vector<int>& v, int lo, int hi) {
    if (lo == hi) return v[lo];
    int mid = (lo + hi) / 2;
    return std::max(maxDC(v, lo, mid), maxDC(v, mid + 1, hi));
}

long long countInversions(std::vector<int>& v, std::vector<int>& tmp, int lo, int hi) {
    if (hi - lo <= 1) return 0;
    int mid = (lo + hi) / 2;
    long long inv = countInversions(v, tmp, lo, mid) + countInversions(v, tmp, mid, hi);
    int i = lo, j = mid, k = lo;
    while (i < mid && j < hi) {
        if (v[i] <= v[j]) tmp[k++] = v[i++];
        else {
            tmp[k++] = v[j++];
            inv += mid - i;  // all remaining left items are greater than v[j]
        }
    }
    while (i < mid) tmp[k++] = v[i++];
    while (j < hi) tmp[k++] = v[j++];
    for (int t = lo; t < hi; ++t) v[t] = tmp[t];
    return inv;
}

int main() {
    assert(power(2, 10) == 1024 && power(3, 5) == 243 && power(5, 0) == 1);
    assert(maxDC({4, 9, 2, 7}, 0, 3) == 9);

    std::vector<int> v = {2, 4, 1, 3, 5};
    std::vector<int> tmp(v.size());
    assert(countInversions(v, tmp, 0, static_cast<int>(v.size())) == 3);

    std::vector<int> rev = {5, 4, 3, 2, 1};
    std::vector<int> tmp2(rev.size());
    assert(countInversions(rev, tmp2, 0, 5) == 10);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
The cost is described by T(n) = a T(n/b) + f(n). Fast exponentiation is T(n) = T(n/2) + O(1), so O(log n). Finding the maximum by splitting is T(n) = 2T(n/2) + O(1), so O(n). Merge sort and inversion counting are T(n) = 2T(n/2) + O(n), so O(n log n). The recursion depth is log n when the input is split evenly, so the call stack uses O(log n) space, plus whatever the combine step allocates; merge sort's temporary array makes its total space O(n). An uneven split can raise the depth to n and the time to O(n squared), as with quick sort and a bad pivot.

## Common Mistakes & Misconceptions
A typical symptom is a recursive solution that is correct but slow because it recomputes the same subproblems, such as Fibonacci split into two overlapping calls; divide and conquer assumes independent subproblems. Students forget the base case, getting RecursionError, or mishandle empty and single-element inputs. Off-by-one errors in the split (`mid` versus `mid + 1`) cause infinite recursion when a half equals the whole problem. Others believe dividing always helps: finding the maximum this way is still linear. Another mistake is a lopsided split that silently produces quadratic behaviour, and doing the combine step with a method that costs more than expected, for example slicing lists in Python, which copies elements at every level.

## Builds On
This concept builds on Recursion, since every divide-and-conquer algorithm is a recursive function with a base case and smaller self-calls, and the call stack behaviour is identical. It builds on Recurrence Relations & Master Theorem, which supply the tool for turning the structure "a subproblems of size n/b plus f(n) work" into a running-time bound.

## Leads To
Merge Sort and Quick Sort are the canonical sorting examples of the strategy. The Segment Tree stores answers for halves of a range, which is divide and conquer applied to a data structure, and dynamic programming addresses the case where subproblems overlap instead of being independent.

## Check Yourself
**Q1.** What are the three steps of divide and conquer?
**A1.** Divide into smaller subproblems, conquer them recursively, and combine their answers.
**Q2.** Why is fast exponentiation O(log n)?
**A2.** It halves the exponent each call and does constant work per call, so there are about log2 n calls.
**Q3.** Why is divide and conquer a poor fit for Fibonacci?
**A3.** The subproblems overlap and are recomputed many times; dynamic programming suits that case.
