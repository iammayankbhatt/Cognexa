---
id: prefix_sums
name: "Prefix Sums"
cluster: searching_hashing
reviewed: false
sources:
  - "Competitive Programmer's Handbook (Laaksonen), Section 9.1 (Sum queries)"
  - "CLRS, Chapter 24 exercises on cumulative sums; Sedgewick and Wayne, Algorithms 4th ed., Section 1.4"
---

## Overview
A prefix sum array stores, at each position, the total of all elements up to that point. Once built in one pass, it answers "what is the sum of the elements from index l to index r?" in constant time by subtracting two stored values, instead of adding the elements each time. Whenever a problem asks for many range sums over data that does not change, prefix sums turn a quadratic amount of work into a linear amount.

## Intuition
Picture the odometer of a car. At each town you note the odometer reading. To know how far you drove between town 3 and town 7, you do not add up every little segment; you subtract the reading at town 3 from the reading at town 7. The odometer readings are prefix sums of the segment lengths, and the difference of two readings is the sum over the range between them.

## How It Works
Given an array `a` of n values, define `prefix[0] = 0` and `prefix[i] = a[0] + a[1] + ... + a[i-1]`, so `prefix` has n + 1 entries. Building it takes one pass: `prefix[i+1] = prefix[i] + a[i]`. The leading zero is the trick that removes special cases: the sum of the elements with indexes l through r inclusive is `prefix[r + 1] - prefix[l]`, and for l = 0 it still works because prefix[0] is zero.

Why it works: prefix[r + 1] contains everything from the start through r, and prefix[l] contains everything before l. Subtracting leaves exactly the elements from l to r.

The idea generalises. In two dimensions, let `P[i][j]` be the sum of the rectangle from the top-left corner to just before row i and column j. The sum of any sub-rectangle is found by inclusion-exclusion: `P[r2+1][c2+1] - P[r1][c2+1] - P[r2+1][c1] + P[r1][c1]`. Differences work too: the "difference array" is the inverse operation, letting you add a value to a whole range in constant time and then recover the final array with a prefix sum.

A famous application counts subarrays whose sum equals k. Subarray sum from l to r equals k exactly when `prefix[r+1] - prefix[l] = k`, so while scanning keep a hash map counting how many times each prefix value has occurred, and for each new prefix p add the count of earlier prefixes equal to p - k. This works even with negative numbers, unlike the sliding window.

The limitation is that the array should not change between queries: updating one element would force rewriting all later prefix sums, costing O(n). When values change frequently, a Fenwick tree or a segment tree supports both updates and range queries in O(log n).

## Worked Example
For a = [3, 1, 4, 1, 5], build prefix = [0, 3, 4, 8, 9, 14].

Sum of elements at indexes 1 through 3 (1 + 4 + 1): prefix[4] - prefix[1] = 9 - 3 = 6. Sum of the whole array: prefix[5] - prefix[0] = 14. Sum of a single element at index 2: prefix[3] - prefix[2] = 8 - 4 = 4. With 1,000 queries over an array of one million items, the naive method does up to a billion additions, while the prefix array costs one million to build and then one subtraction per query.

Count subarrays with sum 5 in [1, 2, 3, 0, 2]: the prefixes are 0, 1, 3, 6, 6, 8. At each new prefix, count earlier prefixes equal to prefix - 5: for 6 we look for 1 (one earlier), for the second 6 again 1, for 8 we look for 3 (one). That gives three subarrays: [2, 3], [2, 3, 0] and [3, 0, 2].

## Code
```python
def build_prefix(values):
    prefix = [0]
    for v in values:
        prefix.append(prefix[-1] + v)
    return prefix


def range_sum(prefix, left, right):
    """Sum of values[left..right] inclusive."""
    return prefix[right + 1] - prefix[left]


def count_subarrays_with_sum(values, k):
    seen = {0: 1}                         # the empty prefix
    total = count = 0
    for v in values:
        total += v
        count += seen.get(total - k, 0)
        seen[total] = seen.get(total, 0) + 1
    return count


def build_prefix_2d(grid):
    rows, cols = len(grid), len(grid[0])
    p = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(rows):
        for j in range(cols):
            p[i + 1][j + 1] = grid[i][j] + p[i][j + 1] + p[i + 1][j] - p[i][j]
    return p


def rect_sum(p, r1, c1, r2, c2):
    return p[r2 + 1][c2 + 1] - p[r1][c2 + 1] - p[r2 + 1][c1] + p[r1][c1]


a = [3, 1, 4, 1, 5]
prefix = build_prefix(a)
assert prefix == [0, 3, 4, 8, 9, 14]
assert range_sum(prefix, 1, 3) == 6
assert range_sum(prefix, 0, 4) == 14
assert range_sum(prefix, 2, 2) == 4

assert count_subarrays_with_sum([1, 2, 3, 0, 2], 5) == 3
assert count_subarrays_with_sum([1, -1, 0], 0) == 3        # works with negative numbers
assert count_subarrays_with_sum([], 0) == 0

grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
p = build_prefix_2d(grid)
assert rect_sum(p, 0, 0, 2, 2) == 45
assert rect_sum(p, 1, 1, 2, 2) == 5 + 6 + 8 + 9

import random

random.seed(4)
for _ in range(200):
    arr = [random.randint(-5, 9) for _ in range(random.randint(1, 15))]
    pre = build_prefix(arr)
    l = random.randrange(len(arr))
    r = random.randrange(l, len(arr))
    assert range_sum(pre, l, r) == sum(arr[l:r + 1])
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <unordered_map>
#include <vector>

std::vector<long long> buildPrefix(const std::vector<int>& v) {
    std::vector<long long> prefix(v.size() + 1, 0);
    for (std::size_t i = 0; i < v.size(); ++i) prefix[i + 1] = prefix[i] + v[i];
    return prefix;
}

long long rangeSum(const std::vector<long long>& prefix, int left, int right) {
    return prefix[right + 1] - prefix[left];  // inclusive range
}

int countSubarraysWithSum(const std::vector<int>& v, int k) {
    std::unordered_map<long long, int> seen;
    seen[0] = 1;
    long long total = 0;
    int count = 0;
    for (int x : v) {
        total += x;
        auto it = seen.find(total - k);
        if (it != seen.end()) count += it->second;
        ++seen[total];
    }
    return count;
}

int main() {
    std::vector<int> a = {3, 1, 4, 1, 5};
    std::vector<long long> prefix = buildPrefix(a);
    assert((prefix == std::vector<long long>{0, 3, 4, 8, 9, 14}));
    assert(rangeSum(prefix, 1, 3) == 6);
    assert(rangeSum(prefix, 0, 4) == 14);
    assert(countSubarraysWithSum({1, 2, 3, 0, 2}, 5) == 3);
    assert(countSubarraysWithSum({1, -1, 0}, 0) == 3);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Building a prefix array takes O(n) time and O(n) space. Each range-sum query then takes O(1). Answering q queries costs O(n + q), versus O(n times q) when each query sums its range from scratch. A two-dimensional prefix table of an r by c grid takes O(r times c) to build and answers rectangle sums in O(1). Counting subarrays with a given sum using a hash map runs in O(n) expected time and O(n) space. The structure is static: changing one element requires O(n) rebuilding work, which is why dynamic data uses Fenwick or segment trees.

## Common Mistakes & Misconceptions
The usual symptom is an off-by-one error in the answer, caused by writing `prefix[r] - prefix[l]` instead of `prefix[r + 1] - prefix[l]` for an inclusive range, or by building the array without the leading zero so that queries starting at index 0 need a special case. Students also forget that the prefix array has n + 1 entries, producing an IndexError for the last query. Integer overflow appears when summing large values in fixed-width types; use 64-bit integers. In the subarray-count problem, forgetting to seed the map with the empty prefix `{0: 1}` misses subarrays starting at index 0. People also assume prefix sums handle updates; after the array changes, the stored sums are stale. Using a sliding window for subarray sums with negative numbers fails where the prefix-sum plus hash map method succeeds.

## Builds On
This concept builds on Arrays: a prefix sum array is built by scanning an array once with a loop and is itself an array whose constant-time indexing makes each query a pair of lookups. The zero-based index conventions and the careful handling of inclusive ranges and the valid index range come straight from the arrays concept.

## Leads To
The segment tree and the Fenwick tree extend prefix sums to data that changes, supporting both updates and range queries in logarithmic time. Difference arrays, two-dimensional range sums and many counting problems on arrays and strings use the same subtraction trick.

## Check Yourself
**Q1.** How do you compute the sum of a[l..r] (inclusive) from a prefix array with a leading zero?
**A1.** prefix[r + 1] - prefix[l].
**Q2.** What is the cost of building the prefix array and of one range query?
**A2.** O(n) to build and O(1) per query.
**Q3.** Why is the map seeded with the empty prefix when counting subarrays with sum k?
**A3.** So that subarrays starting at index 0 are counted; their matching earlier prefix is the empty prefix with value 0.
