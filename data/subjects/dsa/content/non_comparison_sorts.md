---
id: non_comparison_sorts
name: "Counting, Radix & Bucket Sort"
cluster: sorting
reviewed: false
sources:
  - "CLRS, Chapter 8 (Sorting in Linear Time), Sections 8.2 to 8.4"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 5.1 (String Sorts: key-indexed counting, LSD radix sort)"
---

## Overview
Comparison sorts decide the order by comparing pairs of elements, and no comparison sort can beat O(n log n) in the worst case. Counting sort, radix sort and bucket sort avoid comparisons altogether by using the values themselves as array indexes or digits. Under the right assumptions, such as integers in a small range, they sort in linear time. The assumptions matter: they trade generality for speed.

## Intuition
A teacher sorting exam papers with scores from 0 to 100 does not compare papers pairwise. She makes 101 piles labelled 0 to 100, drops each paper on the matching pile, and then stacks the piles in order. Each paper is touched once, so the work is proportional to the number of papers plus the number of piles. Radix sort is the library trick of sorting numbers digit by digit, using the same pile method for each digit.

## How It Works
Counting sort handles n integers in the range 0 to k. It counts how many times each value occurs in an array of k + 1 counters, turns the counts into starting positions with a running (prefix) sum, and places each element at its position. To keep the sort stable, the placement loop runs from the end of the input to the beginning, so equal keys keep their original order. A simpler version that rebuilds the output by writing each value count times works for plain integers but cannot carry attached records. Counting sort takes O(n + k) time and O(n + k) space, which is excellent when k is not much larger than n and terrible when k is huge, such as sorting a hundred numbers up to a billion.

Radix sort sorts numbers with d digits by performing a stable counting sort on each digit, starting from the least significant digit (LSD radix sort) and moving to the most significant. Stability is essential: it preserves the order established by earlier, less significant digits. With base b digits, the time is O(d times (n + b)). For 32-bit integers using 256 as the base, d = 4 passes, which is effectively linear.

Bucket sort assumes the input is spread roughly uniformly over a range, say real numbers in [0, 1). Create n buckets, put each value into the bucket covering its range, sort each small bucket (often with insertion sort), and concatenate the buckets. With uniform input each bucket holds about one item, so the expected time is O(n); with all values in one bucket it degrades to the cost of the inner sort.

Why these are not violating the lower bound: that bound applies to algorithms that learn about order only through comparisons. These algorithms use extra information, the range or digits of the keys, and also use memory proportional to the range. They are therefore not general-purpose: they do not work directly on arbitrary objects or floating-point numbers without extra care, and they need keys that can be mapped to small integers.

## Worked Example
Counting sort on [2, 5, 3, 0, 2, 3, 0, 3] with k = 5.

Count occurrences: value 0 appears 2 times, 1 appears 0, 2 appears 2, 3 appears 3, 4 appears 0, 5 appears 1, so counts = [2, 0, 2, 3, 0, 1]. Rebuild: two 0s, no 1s, two 2s, three 3s, no 4s, one 5, giving [0, 0, 2, 2, 3, 3, 3, 5]. The work was one pass over the input and one over the counts: n + k steps.

LSD radix sort on [170, 45, 75, 90, 802, 24, 2, 66]: first sort by the ones digit (0, 5, 5, 0, 2, 4, 2, 6): [170, 90, 802, 2, 24, 45, 75, 66]. Then by the tens digit: [802, 2, 24, 45, 66, 170, 75, 90]. Then by the hundreds digit: [2, 24, 45, 66, 75, 90, 170, 802]. Each pass is stable, so earlier ordering survives.

## Code
```python
def counting_sort_ints(values, k):
    counts = [0] * (k + 1)
    for v in values:
        counts[v] += 1
    out = []
    for v, c in enumerate(counts):
        out.extend([v] * c)
    return out


def counting_sort_by_key(records, key, k):
    """Stable counting sort of records whose key(record) is an integer in 0..k."""
    counts = [0] * (k + 1)
    for r in records:
        counts[key(r)] += 1
    for i in range(1, k + 1):
        counts[i] += counts[i - 1]                # counts[i] = number of items with key <= i
    out = [None] * len(records)
    for r in reversed(records):                   # walk backwards to keep equal keys in order
        counts[key(r)] -= 1
        out[counts[key(r)]] = r
    return out


def radix_sort(values, base=10):
    if not values:
        return []
    out = list(values)
    place = 1
    while max(out) // place > 0:
        out = counting_sort_by_key(out, lambda v: (v // place) % base, base - 1)
        place *= base
    return out


def bucket_sort(values):
    """For floats in [0, 1): one bucket per item, sort each small bucket."""
    n = len(values)
    buckets = [[] for _ in range(n)]
    for v in values:
        buckets[int(v * n)].append(v)
    result = []
    for b in buckets:
        result.extend(sorted(b))
    return result


assert counting_sort_ints([2, 5, 3, 0, 2, 3, 0, 3], 5) == [0, 0, 2, 2, 3, 3, 3, 5]
assert counting_sort_ints([], 3) == []

records = [(2, "a"), (1, "b"), (2, "c"), (1, "d")]
assert counting_sort_by_key(records, lambda r: r[0], 2) == [(1, "b"), (1, "d"), (2, "a"), (2, "c")]

assert radix_sort([170, 45, 75, 90, 802, 24, 2, 66]) == [2, 24, 45, 66, 75, 90, 170, 802]
assert radix_sort([]) == [] and radix_sort([0]) == [0]

assert bucket_sort([0.78, 0.17, 0.39, 0.26, 0.72, 0.94, 0.21]) == sorted(
    [0.78, 0.17, 0.39, 0.26, 0.72, 0.94, 0.21]
)

import random

random.seed(11)
for _ in range(100):
    arr = [random.randint(0, 999) for _ in range(random.randint(0, 40))]
    assert radix_sort(arr) == sorted(arr)
    assert counting_sort_ints(arr, 999) == sorted(arr)
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

std::vector<int> countingSort(const std::vector<int>& v, int k) {
    std::vector<int> counts(k + 1, 0);
    for (int x : v) ++counts[x];
    std::vector<int> out;
    for (int value = 0; value <= k; ++value) out.insert(out.end(), counts[value], value);
    return out;
}

void countingPass(std::vector<int>& a, int place) {
    std::vector<int> counts(10, 0), out(a.size());
    for (int x : a) ++counts[(x / place) % 10];
    for (int d = 1; d < 10; ++d) counts[d] += counts[d - 1];
    for (std::size_t i = a.size(); i-- > 0;) out[--counts[(a[i] / place) % 10]] = a[i];  // stable
    a = out;
}

std::vector<int> radixSort(std::vector<int> a) {
    if (a.empty()) return a;
    int largest = *std::max_element(a.begin(), a.end());
    for (int place = 1; largest / place > 0; place *= 10) countingPass(a, place);
    return a;
}

int main() {
    assert((countingSort({2, 5, 3, 0, 2, 3, 0, 3}, 5) == std::vector<int>{0, 0, 2, 2, 3, 3, 3, 5}));
    assert((radixSort({170, 45, 75, 90, 802, 24, 2, 66}) ==
            std::vector<int>{2, 24, 45, 66, 75, 90, 170, 802}));
    assert(radixSort({}).empty());

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Counting sort takes O(n + k) time and O(n + k) space for n items with keys in 0..k, and is stable when written with the backward placement loop. Radix sort with d digits in base b takes O(d times (n + b)) time and O(n + b) space; for fixed-width integers this is O(n). Bucket sort takes O(n) expected time for uniformly distributed input and O(n squared) in the worst case if everything lands in one bucket and the inner sort is quadratic. They beat O(n log n) only when their assumptions hold: a bounded integer range, a bounded number of digits, or uniform data. When k is much larger than n, such as sorting 100 numbers drawn from up to 10 to the power 9, counting sort wastes enormous memory and time.

## Common Mistakes & Misconceptions
A typical symptom is a MemoryError or very slow run from counting sort on a huge key range; the method needs k to be reasonable compared with n. Another is a radix sort that gives wrong results because the per-digit sort is not stable, or because digits are processed from the most significant side without further care. Students forget that counting sort on records needs the prefix-sum and backward-placement version to stay stable, not the simple rebuild. Negative numbers and floating-point values break the naive index mapping unless keys are shifted or converted. Some believe these sorts disprove the n log n lower bound; they do not, because they are not comparison-based. Finally, bucket sort is mistakenly assumed to be linear for all inputs, but skewed data collapses it.

## Builds On
This concept builds on Elementary Sorts: the notion of stability is essential for radix sort to work, the simple counting rebuild is related to the idea of using counts instead of swaps, and bucket sort commonly finishes each bucket with insertion sort. Understanding in-place versus extra-memory trade-offs from the elementary sorts also frames why these methods cost O(n + k) space.

## Leads To
The comparison sorting lower bound explains why this family can beat O(n log n) only by leaving the comparison model. Radix-style ideas appear in suffix array construction, string sorting and database indexing, and counting is the basis of histogram-based techniques.

## Check Yourself
**Q1.** What are the time and space of counting sort for n items with keys in 0..k?
**A1.** O(n + k) time and O(n + k) space.
**Q2.** Why must each digit pass in LSD radix sort be stable?
**A2.** Stability preserves the ordering established by the less significant digits so the final order is correct.
**Q3.** Why is it not a contradiction that counting sort beats n log n?
**A3.** The n log n lower bound applies only to comparison-based sorts; counting sort uses the key values directly.
