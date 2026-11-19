---
id: elementary_sorts
name: "Elementary Sorts (bubble, selection, insertion; stability)"
cluster: sorting
reviewed: false
sources:
  - "CLRS, Section 2.1 (Insertion sort) and Problem 2-2 (Correctness of bubblesort)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.1 (Elementary Sorts)"
---

## Overview
The elementary sorts, bubble sort, selection sort and insertion sort, are the simplest ways to put a collection in order. Each uses nested loops and runs in quadratic time, which makes them too slow for large inputs, but they are easy to understand and to code, they need almost no extra memory, and insertion sort is genuinely good on small or nearly sorted data. They also introduce two ideas that matter for every sorting algorithm: stability and in-place sorting.

## Intuition
Sorting a hand of playing cards shows the three methods. Insertion sort is what most people do instinctively: pick up cards one at a time and slide each into its correct place among the cards already held. Selection sort scans the whole hand to find the smallest card, puts it first, then finds the next smallest, and so on. Bubble sort repeatedly walks along the row swapping any two neighbours that are in the wrong order, so the largest cards bubble to the end.

## How It Works
Bubble sort makes repeated passes. In each pass it compares adjacent pairs and swaps them if the left is larger. After pass k the k largest items are in their final places at the end, so later passes can stop earlier. An early-exit flag that stops when a full pass makes no swaps makes it O(n) on sorted input.

Selection sort keeps a sorted prefix. For each position i it finds the index of the smallest element in the unsorted part and swaps it into position i. It always does about n squared over two comparisons, whatever the input, but only n minus 1 swaps at most, which is useful when writes are expensive.

Insertion sort also keeps a sorted prefix. It takes the next element and shifts larger elements of the prefix one step right until the right gap appears, then drops the element into it. On an already sorted array no shifting happens and it takes O(n); on reverse-sorted input it takes O(n squared). It is adaptive, and in practice it is the fastest of the three. Real libraries use it for small subarrays inside faster sorts.

A sort is stable if equal elements keep their original relative order. Stability matters when sorting records by one field after another, such as sorting people by city and then by age while keeping the city order for equal ages. Insertion sort and bubble sort (with strict comparison) are stable; the usual swap-based selection sort is not, because a long-distance swap can jump an element over an equal one. A sort is in place if it needs only O(1) extra memory, which all three are.

The number of inversions (pairs out of order) governs the cost: each adjacent swap removes at most one inversion, so insertion and bubble sort need work proportional to the number of inversions plus n. A reverse-sorted array of n items has n(n-1)/2 inversions, the worst case.

## Worked Example
Insertion sort on [5, 2, 4, 1].

Start with sorted prefix [5]. Take 2: shift 5 right, insert 2: [2, 5, 4, 1]. Take 4: shift 5 right, insert 4 after 2: [2, 4, 5, 1]. Take 1: shift 5, 4 and 2 right, insert at front: [1, 2, 4, 5]. The number of shifts was 1 + 1 + 3 = 5, the number of inversions in the input.

Stability: sort the records (2, "a"), (1, "b"), (2, "c") by number. A stable sort gives (1, b), (2, a), (2, c), keeping a before c. Selection sort on three items could swap (2, a) to the end and produce (1, b), (2, c), (2, a), losing the original order of the equal keys.

## Code
```python
def bubble_sort(a):
    a = list(a)
    for end in range(len(a) - 1, 0, -1):
        swapped = False
        for j in range(end):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:                    # no swaps: already sorted
            break
    return a


def selection_sort(a):
    a = list(a)
    for i in range(len(a) - 1):
        smallest = min(range(i, len(a)), key=lambda k: a[k])
        a[i], a[smallest] = a[smallest], a[i]
    return a


def insertion_sort(a, key=lambda x: x):
    a = list(a)
    shifts = 0
    for i in range(1, len(a)):
        item = a[i]
        j = i - 1
        while j >= 0 and key(a[j]) > key(item):   # strict >: equal items are not passed (stable)
            a[j + 1] = a[j]
            j -= 1
            shifts += 1
        a[j + 1] = item
    return a if key is not None else a


def insertion_shifts(a):
    a, shifts = list(a), 0
    for i in range(1, len(a)):
        item, j = a[i], i - 1
        while j >= 0 and a[j] > item:
            a[j + 1] = a[j]
            j -= 1
            shifts += 1
        a[j + 1] = item
    return shifts


data = [5, 2, 4, 1]
assert bubble_sort(data) == selection_sort(data) == insertion_sort(data) == [1, 2, 4, 5]
assert insertion_shifts([5, 2, 4, 1]) == 5                     # equals the number of inversions
assert insertion_shifts([1, 2, 3, 4]) == 0                     # already sorted: linear time
assert insertion_shifts([4, 3, 2, 1]) == 6                     # reversed: n(n-1)/2
assert bubble_sort([]) == [] and insertion_sort([7]) == [7]

records = [(2, "a"), (1, "b"), (2, "c")]
assert insertion_sort(records, key=lambda r: r[0]) == [(1, "b"), (2, "a"), (2, "c")]   # stable

import random

random.seed(6)
for _ in range(200):
    arr = [random.randint(0, 20) for _ in range(random.randint(0, 15))]
    assert bubble_sort(arr) == selection_sort(arr) == insertion_sort(arr) == sorted(arr)
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <utility>
#include <vector>

void bubbleSort(std::vector<int>& a) {
    for (std::size_t end = a.size(); end > 1; --end) {
        bool swapped = false;
        for (std::size_t j = 0; j + 1 < end; ++j) {
            if (a[j] > a[j + 1]) {
                std::swap(a[j], a[j + 1]);
                swapped = true;
            }
        }
        if (!swapped) break;
    }
}

void selectionSort(std::vector<int>& a) {
    for (std::size_t i = 0; i + 1 < a.size(); ++i) {
        std::size_t smallest = i;
        for (std::size_t j = i + 1; j < a.size(); ++j)
            if (a[j] < a[smallest]) smallest = j;
        std::swap(a[i], a[smallest]);
    }
}

void insertionSort(std::vector<int>& a) {
    for (std::size_t i = 1; i < a.size(); ++i) {
        int item = a[i];
        std::size_t j = i;
        while (j > 0 && a[j - 1] > item) {
            a[j] = a[j - 1];
            --j;
        }
        a[j] = item;
    }
}

int main() {
    std::vector<int> base = {5, 2, 4, 1, 9, 0, 2};
    std::vector<int> expected = base;
    std::sort(expected.begin(), expected.end());

    std::vector<int> a = base, b = base, c = base;
    bubbleSort(a);
    selectionSort(b);
    insertionSort(c);
    assert(a == expected && b == expected && c == expected);

    std::vector<int> empty;
    insertionSort(empty);
    assert(empty.empty());

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Bubble sort is O(n squared) in the average and worst case and O(n) in the best case with an early-exit flag; it uses O(1) extra space and is stable. Selection sort is Theta(n squared) in every case, uses at most n - 1 swaps and O(1) extra space, and the common version is not stable. Insertion sort is O(n squared) in the worst and average case, O(n) in the best case (already sorted), O(n + inversions) in general, uses O(1) extra space and is stable. For n = 100,000 an O(n squared) sort performs on the order of ten billion operations, which is why these methods are reserved for small inputs, while O(n log n) sorts handle millions of items comfortably.

## Common Mistakes & Misconceptions
A typical symptom is a program that sorts small test lists instantly but takes minutes on large inputs, caused by using a quadratic sort. Students swap the wrong index range in bubble sort, running past the end and causing IndexError, or forget the shrinking inner bound. In insertion sort, using `>=` instead of `>` when shifting breaks stability, and starting from index 0 instead of 1 does unnecessary work. Another misconception is that a sorted result proves the algorithm is correct; you need the invariant that the prefix is sorted. People believe selection sort is adaptive, but it does the same comparisons on sorted input. Finally, sorting a list of records on one key and expecting earlier orderings to be preserved only works with a stable sort.

## Builds On
This concept builds on Arrays: all three sorts rearrange elements in place within an array using index loops, swaps and shifts, and their costs come from how many elements move. It builds on Time Complexity & Big-O because analysing them means counting comparisons and swaps in nested loops, which gives the quadratic growth that motivates faster algorithms.

## Leads To
Merge Sort and Quick Sort sort in O(n log n) time using divide and conquer, and Heap Sort does so with a binary heap. Counting, radix and bucket sorts avoid comparisons altogether, and the comparison sorting lower bound shows why O(n log n) cannot be beaten by comparison-based methods. Greedy algorithms often start by sorting their input with one of these faster methods.

## Check Yourself
**Q1.** Which elementary sort is fastest on an already sorted array?
**A1.** Insertion sort (and bubble sort with an early exit), both O(n); selection sort still takes O(n squared).
**Q2.** What does it mean for a sort to be stable?
**A2.** Equal elements keep their original relative order.
**Q3.** How many inversions does a reverse-sorted array of n items have?
**A3.** n(n - 1) / 2.
