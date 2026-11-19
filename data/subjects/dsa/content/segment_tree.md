---
id: segment_tree
name: "Segment Tree"
cluster: trees
reviewed: false
sources:
  - "CLRS, Section 14.3 (Interval trees, augmenting data structures)"
  - "Competitive Programmer's Handbook (Laaksonen), Chapter 9 (Range queries), Section 9.3 (Segment trees)"
---

## Overview
A segment tree is a binary tree built over an array that stores a summary of each segment of the array, such as its sum, minimum or maximum. The root summarises the whole array, its two children summarise the left and right halves, and so on down to leaves that hold single elements. With this structure, both a range query ("what is the sum of a[l..r]?") and a point update ("set a[i] to v") take O(log n) time. This beats prefix sums, which answer range queries in O(1) but need O(n) to rebuild after one change, and beats a plain array, which updates in O(1) but needs O(n) to answer a range query.

## Intuition
Picture a sports tournament organised as a bracket. Each match records a summary of its two sub-brackets, for example the total points scored. To find the total points of a stretch of consecutive teams you do not add each team; you pick a few whole sub-brackets that exactly cover the stretch and add their stored totals. If one team's score changes, only the matches on the path from that team up to the final need updating. A segment tree is this bracket, with each internal node storing the combined value of its range.

## How It Works
Structure. Node 1 covers the range [0, n - 1]. A node covering [l, r] with l < r has a left child covering [l, mid] and a right child covering [mid + 1, r], where mid = (l + r) // 2. A node with l = r is a leaf and stores a[l]. In the usual array layout, node i has children 2i and 2i + 1, and an array of size 4n is enough to store the tree. Every internal node's value is the combine of its children's values (sum, min, max, gcd, any associative operation).

Build. A recursive postorder construction: build the left and right children, then compute the node's value from them. This is a divide-and-conquer pass that visits each of the about 2n nodes once, so it takes O(n).

Point update. To change a[i], walk down from the root to the leaf for index i, set it, and recompute the combine value on the way back up. Only one node per level changes, so the cost is the height, O(log n).

Range query. For a query [ql, qr], visit a node covering [l, r]. If its range is completely inside the query, return its stored value. If it is completely outside, return the identity (0 for sum, infinity for min). Otherwise it partly overlaps, so recurse into both children and combine the answers. At most two nodes per level are partially overlapping, so the query visits O(log n) nodes.

Lazy propagation. For range updates ("add v to every element in [l, r]") a lazy tag is stored on a node meaning "my children still need this pending change", and it is pushed down only when needed. This keeps range updates at O(log n).

## Worked Example
Array a = [2, 1, 5, 3]. The root covers [0, 3] with sum 11. Its children cover [0, 1] with sum 3 and [2, 3] with sum 8. The leaves hold 2, 1, 5, 3.

```
          [0,3]=11
         /        \
    [0,1]=3      [2,3]=8
    /    \       /    \
 [0,0]=2 [1,1]=1 [2,2]=5 [3,3]=3
```

Query the sum of a[1..2]. At the root [0, 3] the range partly overlaps, so recurse. The left child [0, 1] partly overlaps, so recurse: leaf [0, 0] is outside (0), leaf [1, 1] is inside (1). The right child [2, 3] partly overlaps: leaf [2, 2] is inside (5), leaf [3, 3] is outside (0). The total is 1 + 5 = 6. Update a[2] = 10: change leaf [2, 2] to 10, then node [2, 3] becomes 13 and the root becomes 16, touching three nodes. A repeated query of a[1..2] now returns 11.

## Code
```python
class SegmentTree:
    def __init__(self, data):
        self.n = len(data)
        self.tree = [0] * (4 * self.n)
        if self.n:
            self._build(1, 0, self.n - 1, data)

    def _build(self, node, l, r, data):
        if l == r:
            self.tree[node] = data[l]
            return
        mid = (l + r) // 2
        self._build(2 * node, l, mid, data)
        self._build(2 * node + 1, mid + 1, r, data)
        self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1]

    def update(self, index, value, node=1, l=0, r=None):
        r = self.n - 1 if r is None else r
        if l == r:
            self.tree[node] = value
            return
        mid = (l + r) // 2
        if index <= mid:
            self.update(index, value, 2 * node, l, mid)
        else:
            self.update(index, value, 2 * node + 1, mid + 1, r)
        self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1]

    def query(self, ql, qr, node=1, l=0, r=None):
        r = self.n - 1 if r is None else r
        if qr < l or r < ql:                    # completely outside
            return 0
        if ql <= l and r <= qr:                 # completely inside
            return self.tree[node]
        mid = (l + r) // 2
        return self.query(ql, qr, 2 * node, l, mid) + self.query(ql, qr, 2 * node + 1, mid + 1, r)


st = SegmentTree([2, 1, 5, 3])
assert st.query(0, 3) == 11 and st.query(1, 2) == 6
st.update(2, 10)
assert st.query(1, 2) == 11 and st.query(0, 3) == 16

import random

random.seed(7)
arr = [random.randint(-50, 50) for _ in range(100)]
tree = SegmentTree(arr)
for _ in range(500):
    if random.random() < 0.4:
        i, v = random.randrange(100), random.randint(-50, 50)
        arr[i] = v
        tree.update(i, v)
    else:
        a, b = sorted((random.randrange(100), random.randrange(100)))
        assert tree.query(a, b) == sum(arr[a : b + 1])
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

class SegmentTree {
public:
    explicit SegmentTree(const std::vector<int>& data) : n(data.size()), tree(4 * data.size(), 0) {
        if (n) build(1, 0, n - 1, data);
    }

    void update(std::size_t index, int value) { update(1, 0, n - 1, index, value); }
    long long query(std::size_t ql, std::size_t qr) const { return query(1, 0, n - 1, ql, qr); }

private:
    std::size_t n;
    std::vector<long long> tree;

    void build(std::size_t node, std::size_t l, std::size_t r, const std::vector<int>& data) {
        if (l == r) {
            tree[node] = data[l];
            return;
        }
        std::size_t mid = (l + r) / 2;
        build(2 * node, l, mid, data);
        build(2 * node + 1, mid + 1, r, data);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }

    void update(std::size_t node, std::size_t l, std::size_t r, std::size_t index, int value) {
        if (l == r) {
            tree[node] = value;
            return;
        }
        std::size_t mid = (l + r) / 2;
        if (index <= mid) update(2 * node, l, mid, index, value);
        else update(2 * node + 1, mid + 1, r, index, value);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }

    long long query(std::size_t node, std::size_t l, std::size_t r, std::size_t ql, std::size_t qr) const {
        if (qr < l || r < ql) return 0;
        if (ql <= l && r <= qr) return tree[node];
        std::size_t mid = (l + r) / 2;
        return query(2 * node, l, mid, ql, qr) + query(2 * node + 1, mid + 1, r, ql, qr);
    }
};

int main() {
    SegmentTree st({2, 1, 5, 3});
    assert(st.query(0, 3) == 11 && st.query(1, 2) == 6);
    st.update(2, 10);
    assert(st.query(1, 2) == 11 && st.query(0, 3) == 16);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Building takes O(n) time. Both point update and range query take O(log n) time, because they visit at most about 4 log n nodes. Memory is O(n): a recursive layout needs an array of 4n entries to be safe, about 2n nodes are actually used. With lazy propagation range updates are also O(log n). Compared with prefix sums (O(n) build, O(1) query, O(n) update), the segment tree balances the two operations when both queries and updates are frequent. The Fenwick tree achieves the same bounds for sums with less memory and simpler code, but supports fewer operations.

## Common Mistakes & Misconceptions
A common bug is allocating only 2n slots for a recursive tree, which causes an IndexError when n is not a power of two; 4n is the safe size. Off-by-one errors in the midpoint split (using [l, mid) with a closed-interval query, or recursing on mid instead of mid + 1) lead to wrong sums or infinite recursion. Returning 0 as the identity is right for sums but wrong for minimum, where the identity is infinity. Students forget to recompute the parent after an update, so queries return stale values. Another mistake is treating partial overlap as full overlap, which makes the query read a node whose range is larger than requested. Some assume a segment tree is only for sums, but any associative combine works, including min, max, gcd and matrix products.

## Builds On
This concept builds on Tree Traversals (pre/in/post-order): the build is a postorder traversal (children first, then the parent's value), and queries and updates are guided depth-first walks down the tree. It builds on Prefix Sums, which solve the static range-sum problem and show why precomputed summaries help; the segment tree keeps the same idea of stored summaries but makes them cheap to update. It builds on Divide & Conquer, since each node splits its range into two halves, solves each half, and combines the results, exactly the recurrence T(n) = 2T(n / 2) + O(1) that gives O(n) build time.

## Leads To
Lazy propagation extends the structure to range updates and is common in competitive programming and database systems that maintain interval statistics. Related structures include the Fenwick tree (a lighter structure for prefix sums), the sparse table (static range minimum queries) and interval trees. Segment trees also appear in computational geometry, where they track which segments cover a point, and in problems needing the k-th element or counting inversions.

## Check Yourself
**Q1.** What does each node of a segment tree store?
**A1.** A summary (such as the sum or minimum) of the range of the array it covers.
**Q2.** What is the time for a range query on a segment tree of n elements?
**A2.** O(log n).
**Q3.** What changes in the tree when one array element is updated?
**A3.** Only the nodes on the path from that element's leaf up to the root, which is O(log n) nodes.
