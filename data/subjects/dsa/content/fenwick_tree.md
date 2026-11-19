---
id: fenwick_tree
name: "Fenwick Tree (BIT)"
cluster: trees
reviewed: false
sources:
  - "Fenwick, P. M. (1994), A new data structure for cumulative frequency tables, Software: Practice and Experience"
  - "Competitive Programmer's Handbook (Laaksonen), Section 9.2 (Binary indexed trees)"
---

## Overview
A Fenwick tree, also called a binary indexed tree (BIT), is a compact array that supports two operations on a sequence of numbers in O(log n) time each: add a value to one position (point update) and compute the sum of the first i elements (prefix sum). From prefix sums one gets any range sum as prefix(r) - prefix(l - 1). It uses just one array of n + 1 numbers and a few lines of code, with no explicit tree pointers, because the tree structure is hidden in the binary representation of the indexes. It is the lightweight alternative to a segment tree when only sums (or other invertible operations) are needed.

## Intuition
Imagine keeping a ledger of daily sales, but instead of a running total for every day, which would be expensive to fix when an early day is corrected, you keep subtotals over blocks of different sizes: a block of 1 day, a block of 2 days, a block of 4 days, and so on, each aligned in a binary pattern. To get the total for the first 7 days you add three block totals (days 5 to 7 broken as block of 4 + block of 2 + block of 1). To correct one day you fix only the few blocks that contain it. The binary indexed tree is this system of power-of-two blocks.

## How It Works
Key idea. Use 1-based indexes. Let lowbit(i) = i & -i be the value of the lowest set bit of i, for example lowbit(6) = 2 because 6 is 110 in binary. The entry tree[i] stores the sum of the lowbit(i) elements ending at position i, that is the range (i - lowbit(i), i]. So tree[4] covers positions 1 to 4, tree[6] covers positions 5 to 6, and tree[7] covers position 7 alone.

Prefix query. To get the sum of the first i elements, start at i, add tree[i], then move to i - lowbit(i) (clearing the lowest set bit), and repeat until i reaches 0. Each step removes one set bit, so there are at most log2(n) + 1 steps. For i = 7 (binary 111) the indexes visited are 7, 6, 4.

Point update. To add delta at position i, add it to tree[i], then move to i + lowbit(i) and repeat while i is at most n. This visits exactly the entries whose ranges contain position i. Each step moves to a strictly larger lowbit, so there are at most about log2 n steps. For n = 8 and i = 3 the indexes visited are 3, 4, 8.

Range sum. sum(l..r) = prefix(r) - prefix(l - 1). This needs the operation to be invertible (subtraction), which is why a Fenwick tree works for sums and counts but not directly for minimum or maximum.

Build in O(n). Instead of n updates, copy the array into tree, then for each i from 1 to n, add tree[i] into its parent tree[i + lowbit(i)] if that index is at most n.

Setting a value. To set a[i] to v, add the difference v - a[i] with a point update, so keep a copy of the original array if you need absolute assignment.

## Worked Example
Let a = [3, 2, -1, 6, 5, 4, -3, 3] with positions 1 to 8. The tree array is tree[1] = 3, tree[2] = 5 (positions 1 to 2), tree[3] = -1, tree[4] = 10 (positions 1 to 4), tree[5] = 5, tree[6] = 9 (positions 5 to 6), tree[7] = -3, tree[8] = 19 (positions 1 to 8).

Prefix(7): 7 = 111, add tree[7] = -3, then 6 = 110, add tree[6] = 9, then 4 = 100, add tree[4] = 10, then 0 stops. Total = 16, which equals 3 + 2 - 1 + 6 + 5 + 4 - 3. The range sum of positions 3 to 6 is prefix(6) - prefix(2) = (9 + 10) - 5 = 14, which equals -1 + 6 + 5 + 4. Now add 2 at position 3: update tree[3], then index 4 (3 + 1) and index 8 (4 + 4), then 16 is beyond n, so stop. Three entries changed, and prefix(7) is now 18.

## Code
```python
class Fenwick:
    def __init__(self, n):
        self.n = n
        self.tree = [0] * (n + 1)              # index 0 is unused

    @classmethod
    def from_list(cls, values):                # O(n) build
        f = cls(len(values))
        for i, v in enumerate(values, 1):
            f.tree[i] += v
            j = i + (i & -i)
            if j <= f.n:
                f.tree[j] += f.tree[i]
        return f

    def add(self, i, delta):                   # position i is 1-based
        while i <= self.n:
            self.tree[i] += delta
            i += i & -i

    def prefix(self, i):
        total = 0
        while i > 0:
            total += self.tree[i]
            i -= i & -i
        return total

    def range_sum(self, l, r):
        return self.prefix(r) - self.prefix(l - 1)


a = [3, 2, -1, 6, 5, 4, -3, 3]
f = Fenwick.from_list(a)
assert f.tree[1:] == [3, 5, -1, 10, 5, 9, -3, 19]
assert f.prefix(7) == 16 and f.range_sum(3, 6) == 14
f.add(3, 2)
assert f.prefix(7) == 18 and f.range_sum(3, 6) == 16

import random

random.seed(11)
arr = [random.randint(-20, 20) for _ in range(64)]
g = Fenwick.from_list(arr)
for _ in range(500):
    if random.random() < 0.5:
        i, d = random.randint(1, 64), random.randint(-9, 9)
        arr[i - 1] += d
        g.add(i, d)
    else:
        l = random.randint(1, 64)
        r = random.randint(l, 64)
        assert g.range_sum(l, r) == sum(arr[l - 1 : r])
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

class Fenwick {
public:
    explicit Fenwick(int n) : n_(n), tree_(n + 1, 0) {}

    void add(int i, long long delta) {          // 1-based position
        for (; i <= n_; i += i & -i) tree_[i] += delta;
    }

    long long prefix(int i) const {
        long long total = 0;
        for (; i > 0; i -= i & -i) total += tree_[i];
        return total;
    }

    long long rangeSum(int l, int r) const { return prefix(r) - prefix(l - 1); }

private:
    int n_;
    std::vector<long long> tree_;
};

int main() {
    std::vector<int> a = {3, 2, -1, 6, 5, 4, -3, 3};
    Fenwick f(8);
    for (int i = 0; i < 8; ++i) f.add(i + 1, a[i]);
    assert(f.prefix(7) == 16 && f.rangeSum(3, 6) == 14);
    f.add(3, 2);
    assert(f.prefix(7) == 18 && f.rangeSum(3, 6) == 16);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Both add and prefix take O(log n) time, because each step clears or sets one bit of the index and there are about log2 n bits. A range sum takes two prefix queries, so O(log n). Building from an array takes O(n) with the parent-propagation method, or O(n log n) with n separate updates. Space is O(n), a single array with no pointers, which makes the structure much smaller and faster in practice than a segment tree. The limits are that it needs an invertible operation for range queries and cannot directly do range minimum, and range updates need a second tree.

## Common Mistakes & Misconceptions
The most common bug is using zero-based indexes: with index 0, i & -i is 0, so the update loop never moves and runs forever. Programs must shift to 1-based positions. Students also confuse the update direction (add lowbit to go up) and the query direction (subtract lowbit to go down), swapping them gives wrong sums. A symptom of a wrong range query is an off-by-one result, usually from computing prefix(r) - prefix(l) instead of prefix(r) - prefix(l - 1). Many believe a Fenwick tree stores prefix sums directly; tree[i] stores only the sum of the block ending at i. Others try to use it for range maximum, which fails because maximum has no inverse and the structure assumes sums can be subtracted. Forgetting that add is a delta, not an assignment, is also frequent.

## Builds On
This concept builds on Prefix Sums. A Fenwick tree answers exactly the same query (the sum of the first i elements) but allows the data to change: where a prefix array needs O(n) to rebuild after one edit, the Fenwick tree stores partial block sums so an edit touches only O(log n) entries. It also builds on Bit Manipulation, because the whole structure is driven by lowbit(i) = i & -i, the isolation of the lowest set bit, and by reading an index in binary to decide which blocks to add.

## Leads To
The Fenwick tree is used to count inversions in an array, to maintain frequency tables and cumulative distributions, to do order-statistics queries (find the k-th smallest by descending the bits), and to answer two-dimensional range sums with a 2D version. It is a close relative of the Segment Tree, which supports more operations at the cost of more memory and code.

## Check Yourself
**Q1.** What is i & -i for i = 12?
**A1.** 4, because 12 is 1100 in binary and the lowest set bit is worth 4.
**Q2.** How do you compute the sum of positions l to r with a Fenwick tree?
**A2.** prefix(r) - prefix(l - 1).
**Q3.** Why must the indexes be 1-based?
**A3.** Because lowbit(0) is 0, so the loops would never advance from index 0.
