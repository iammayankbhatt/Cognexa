---
id: merge_sort
name: "Merge Sort"
cluster: sorting
reviewed: false
sources:
  - "CLRS, Section 2.3.1 (The divide-and-conquer approach: merge sort)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.2 (Mergesort)"
---

## Overview
Merge sort sorts a list by splitting it into two halves, sorting each half recursively, and merging the two sorted halves into one sorted list. The merge step is the heart of the algorithm: given two sorted sequences, it produces their sorted union in a single linear pass. Merge sort always runs in O(n log n) time, is stable, and handles any input order equally well, at the cost of O(n) extra memory for the merge buffer.

## Intuition
Imagine sorting a huge pile of exam papers by name. You split the pile in two, give each half to a friend who sorts it however they like, and then merge: you hold the two sorted piles side by side and repeatedly take whichever top paper comes first alphabetically. Merging is easy and fast because both piles are already sorted, so you only ever compare the two papers on top. Your friends do the same, splitting further, until a pile has a single paper, which is trivially sorted.

## How It Works
The recursive structure has three parts. Base case: a list with zero or one element is already sorted. Divide: split the list at the middle index. Conquer: sort the left and right halves recursively. Combine: merge the two sorted halves.

Merging uses two indexes, one into each sorted half. Compare the front items; append the smaller to the output and advance that index. When one half runs out, append the rest of the other. To keep the sort stable, when the two front items are equal take the one from the left half first, which preserves the original order of equal elements.

The recursion tree has about log2 n levels, because the size halves at each level. At every level the merges together touch each element once, so each level costs O(n). The total is O(n log n), matching the recurrence T(n) = 2T(n/2) + n. This is true in the best, average and worst case, unlike quick sort, so merge sort has predictable performance.

The merge needs a temporary buffer to write into, which makes space O(n) for the array version. A common implementation allocates one auxiliary array once and reuses it at every level to avoid repeated allocation. Merge sort on linked lists needs no extra buffer, since merging just relinks nodes, which makes it a favourite for sorting lists. Its sequential access pattern also makes it ideal for external sorting of data too big for memory: sort chunks, write them out, then merge the sorted runs from disk.

A bottom-up version avoids recursion: merge runs of length 1 into runs of length 2, then 4, then 8, and so on. For small subarrays, implementations often switch to insertion sort, because the overhead of recursion outweighs its benefit on tiny inputs.

## Worked Example
Sort [38, 27, 43, 3].

Divide: [38, 27] and [43, 3]. Divide again: [38], [27], [43], [3]. Merge [38] and [27]: compare 38 and 27, take 27, then 38: [27, 38]. Merge [43] and [3]: [3, 43]. Now merge [27, 38] and [3, 43]: compare 27 and 3, take 3; compare 27 and 43, take 27; compare 38 and 43, take 38; the left half is empty so append 43. The result is [3, 27, 38, 43]. The merge steps together made at most one pass over all elements at each of 2 levels, and n = 4 gives log2 4 = 2 levels.

## Code
```python
def merge(left, right):
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:                 # <= takes the left item on ties: stable
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out


def merge_sort(values):
    if len(values) <= 1:
        return list(values)                     # base case
    mid = len(values) // 2
    return merge(merge_sort(values[:mid]), merge_sort(values[mid:]))


def merge_sort_by(records, key):
    if len(records) <= 1:
        return list(records)
    mid = len(records) // 2
    left, right = merge_sort_by(records[:mid], key), merge_sort_by(records[mid:], key)
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    return out + left[i:] + right[j:]


assert merge([1, 4, 6], [2, 3, 7]) == [1, 2, 3, 4, 6, 7]
assert merge([], [1]) == [1] and merge([], []) == []
assert merge_sort([38, 27, 43, 3]) == [3, 27, 38, 43]
assert merge_sort([]) == [] and merge_sort([5]) == [5]
assert merge_sort([3, 3, 1, 2, 2]) == [1, 2, 2, 3, 3]

records = [(2, "a"), (1, "b"), (2, "c"), (1, "d")]
assert merge_sort_by(records, key=lambda r: r[0]) == [(1, "b"), (1, "d"), (2, "a"), (2, "c")]  # stable

import random

random.seed(8)
for _ in range(200):
    arr = [random.randint(-50, 50) for _ in range(random.randint(0, 40))]
    assert merge_sort(arr) == sorted(arr)
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

void mergeRange(std::vector<int>& a, std::vector<int>& tmp, int lo, int mid, int hi) {
    int i = lo, j = mid, k = lo;
    while (i < mid && j < hi) {
        if (a[i] <= a[j]) tmp[k++] = a[i++];  // <= keeps equal items in order (stable)
        else tmp[k++] = a[j++];
    }
    while (i < mid) tmp[k++] = a[i++];
    while (j < hi) tmp[k++] = a[j++];
    for (int t = lo; t < hi; ++t) a[t] = tmp[t];
}

void mergeSortRange(std::vector<int>& a, std::vector<int>& tmp, int lo, int hi) {
    if (hi - lo <= 1) return;  // base case
    int mid = lo + (hi - lo) / 2;
    mergeSortRange(a, tmp, lo, mid);
    mergeSortRange(a, tmp, mid, hi);
    mergeRange(a, tmp, lo, mid, hi);
}

void mergeSort(std::vector<int>& a) {
    std::vector<int> tmp(a.size());  // one buffer reused by every merge
    mergeSortRange(a, tmp, 0, static_cast<int>(a.size()));
}

int main() {
    std::vector<int> a = {38, 27, 43, 3};
    mergeSort(a);
    assert((a == std::vector<int>{3, 27, 38, 43}));

    std::vector<int> b = {3, 3, 1, 2, 2};
    mergeSort(b);
    assert((b == std::vector<int>{1, 2, 2, 3, 3}));

    std::vector<int> empty;
    mergeSort(empty);
    assert(empty.empty());

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Merge sort takes Theta(n log n) time in the best, average and worst cases, because the halving structure does not depend on the input order. The extra space is O(n) for the merge buffer for arrays, plus O(log n) for the recursion stack; for linked lists the merge needs only O(1) extra space apart from the recursion. It is stable. Counting comparisons, merge sort makes between about (n log n) / 2 and n log n minus n, close to the information-theoretic minimum. Compared with quick sort, it has a better worst case but needs the extra memory and typically a bit more copying, so quick sort is often faster on arrays in practice.

## Common Mistakes & Misconceptions
A frequent symptom is RecursionError or an infinite loop from a bad split, such as using `mid = len // 2 + 1` so that one half equals the whole input when the length is 2, or forgetting the base case for length 0 or 1. Another is breaking stability by using `<` instead of `<=` in the merge comparison. Students slice lists in the recursion (`values[:mid]`), which copies elements and adds O(n) per call, though the total stays O(n log n); in C++ passing vectors by value does the same. Forgetting to append the leftover items of the unfinished half drops elements. People also misjudge its memory use: it is not in place, so sorting a huge array may need a second array of the same size. Finally, some think merge sort is always faster than quick sort, which depends on the data and the machine.

## Builds On
This concept builds on Divide & Conquer: merge sort is the canonical instance, with the split, the two recursive calls and the combine step each corresponding to a part of that pattern. It builds on Elementary Sorts, because insertion sort is often used for tiny subarrays and because the merged halves obey the same sortedness and stability ideas, a stable merge being what keeps the whole sort stable.

## Leads To
Counting inversions extends the merge step to count out-of-order pairs, and external sorting merges sorted runs from disk. The comparison sorting lower bound explains why the O(n log n) of merge sort is optimal for comparison-based sorting, and Python's built-in sort, Timsort, is a hybrid of merge sort and insertion sort.

## Check Yourself
**Q1.** What does the merge step do?
**A1.** It combines two sorted sequences into one sorted sequence in a single linear pass.
**Q2.** What is merge sort's time complexity in the best and worst case?
**A2.** Theta(n log n) in both.
**Q3.** Why does `<=` in the comparison make merge sort stable?
**A3.** Ties take the item from the left half first, preserving the original order of equal items.
