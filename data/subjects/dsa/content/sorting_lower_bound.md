---
id: sorting_lower_bound
name: "Comparison Sorting Lower Bound"
cluster: sorting
reviewed: false
sources:
  - "CLRS, Section 8.1 (Lower bounds for sorting)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.2 (Proposition I: sorting lower bound)"
---

## Overview
Merge sort, heap sort and quick sort all take about n log n comparisons. Is there a cleverer comparison-based algorithm that does better? The comparison sorting lower bound says no: any algorithm that sorts n items using only pairwise comparisons must make at least about n log2 n comparisons in the worst case. The proof is a counting argument based on a decision tree, and it shows that merge sort and heap sort are asymptotically optimal among comparison sorts.

## Intuition
Think of the game "twenty questions". If there are N possibilities and each question has only a yes or no answer, you need at least log2 N questions to be sure of the answer. Sorting is the same game: the unknown is which of the n! possible orderings of the input is the right one, and each comparison is a yes or no question. To tell n! orderings apart you need at least log2(n!) questions, and log2(n!) is about n log2 n.

## How It Works
Model any comparison sort on inputs of size n as a binary decision tree. Each internal node is a comparison of two elements, "is a_i less than a_j?"; its two children correspond to the yes and no answers. Each leaf is a final ordering the algorithm outputs. Running the algorithm on one input follows one root-to-leaf path, and the length of that path is the number of comparisons made.

To be correct, the algorithm must be able to output every possible ordering of the n elements, since any permutation could be the sorted order of some input. There are n! distinct permutations, so the tree must have at least n! leaves. A binary tree of height h has at most 2 to the power h leaves, hence 2 to the power h is at least n!, so h is at least log2(n!). The height h is the worst-case number of comparisons.

Now bound log2(n!). Since n! is at least (n/2) to the power (n/2) (the largest n/2 factors are each at least n/2), log2(n!) is at least (n/2) log2(n/2), which is Omega(n log n). Stirling's approximation gives the sharper log2(n!) = n log2 n minus about 1.44 n. Therefore every comparison sort needs Omega(n log n) comparisons in the worst case, and merge sort's O(n log n) matches this, making it optimal. The same argument shows that the average number of comparisons is also Omega(n log n).

Limits of the result matter. It applies only to algorithms that gain information solely by comparing elements. Counting sort, radix sort and bucket sort use the key values directly and escape the bound, at the cost of assumptions about the keys. It also says nothing about the best case: insertion sort takes O(n) on sorted input because the decision tree has short paths to some leaves. And for small n it gives a concrete minimum: sorting 5 items needs at least ceiling(log2 120) = 7 comparisons.

The same tree technique proves lower bounds for other comparison problems, such as the number of comparisons needed to find the maximum (n - 1) or to search a sorted array (about log2 n).

## Worked Example
How many comparisons are needed to sort 4 items in the worst case?

There are 4! = 24 possible orderings, so a decision tree needs at least 24 leaves. A tree of height 4 has at most 16 leaves, which is too few; height 5 allows 32 leaves, which is enough. So any comparison sort needs at least ceiling(log2 24) = 5 comparisons for 4 items in the worst case. For 5 items: 5! = 120 and log2 120 is about 6.9, so at least 7 comparisons. For 10 items: 10! = 3,628,800 and log2 of it is about 21.8, so at least 22 comparisons; compare with a quadratic sort needing up to 45.

Check the growth: for n = 1,000,000 the bound is roughly n log2 n minus 1.44n, about 18.5 million comparisons, while a simple quadratic sort needs on the order of 500 billion.

## Code
```python
import math


def min_comparisons(n):
    """Information-theoretic minimum worst-case comparisons to sort n items."""
    return math.ceil(math.log2(math.factorial(n)))


def tree_leaves_needed(n):
    return math.factorial(n)


def max_leaves(height):
    return 2 ** height


assert tree_leaves_needed(4) == 24
assert max_leaves(4) < 24 <= max_leaves(5)                 # height 4 is too short, height 5 suffices
assert [min_comparisons(n) for n in range(1, 8)] == [0, 1, 3, 5, 7, 10, 13]

# The bound grows like n log2 n (Stirling: log2(n!) is about n log2 n - 1.44 n).
n = 1000
exact = math.log2(math.factorial(n))
estimate = n * math.log2(n) - 1.4427 * n
assert abs(exact - estimate) < 10

# Merge sort stays within a small factor of the lower bound on random data.
import random


def merge_sort_comparisons(values):
    count = 0

    def sort(a):
        nonlocal count
        if len(a) <= 1:
            return a
        mid = len(a) // 2
        left, right = sort(a[:mid]), sort(a[mid:])
        out, i, j = [], 0, 0
        while i < len(left) and j < len(right):
            count += 1
            if left[i] <= right[j]:
                out.append(left[i])
                i += 1
            else:
                out.append(right[j])
                j += 1
        return out + left[i:] + right[j:]

    sort(values)
    return count


random.seed(12)
data = random.sample(range(10000), 1000)
used = merge_sort_comparisons(data)
assert min_comparisons(1000) <= used <= 1.1 * min_comparisons(1000)
print("all checks passed")
```

```cpp
#include <cassert>
#include <cmath>
#include <iostream>

double log2Factorial(int n) {
    double total = 0.0;
    for (int k = 2; k <= n; ++k) total += std::log2(static_cast<double>(k));
    return total;
}

int minComparisons(int n) { return static_cast<int>(std::ceil(log2Factorial(n) - 1e-9)); }

int main() {
    assert(minComparisons(1) == 0 && minComparisons(2) == 1 && minComparisons(3) == 3);
    assert(minComparisons(4) == 5 && minComparisons(5) == 7);
    assert(minComparisons(10) == 22);

    // log2(n!) is close to n log2 n - 1.4427 n for large n.
    int n = 1000;
    double estimate = n * std::log2(static_cast<double>(n)) - 1.4427 * n;
    assert(std::fabs(log2Factorial(n) - estimate) < 10.0);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
The lower bound is Omega(n log n) comparisons in the worst case (and on average) for any comparison-based sorting algorithm. Precisely, at least ceiling(log2(n!)) comparisons are needed, which is about n log2 n minus 1.44 n. Merge sort uses at most n log2 n minus n + 1 comparisons, within a few percent of that minimum, and heap sort and quick sort (on average) are within small constant factors, so all are asymptotically optimal. The proof itself takes O(1) space on paper; computing log2(n!) numerically takes O(n) time. Beating the bound requires leaving the comparison model, for example with counting sort in O(n + k) time.

## Common Mistakes & Misconceptions
The most common misunderstanding is believing the bound applies to all sorting algorithms; it only restricts comparison-based sorts, and counting, radix and bucket sorts run in linear time under assumptions. Students also read it as "no sort can ever be faster than n log n on any input", forgetting that it is a worst-case (and average-case) statement: insertion sort is O(n) on sorted input and the decision tree simply has some short paths. Others confuse the number of leaves (n!) with the number of comparisons (the tree's height, log2 of the leaf count). Another error is claiming the tree has n leaves, because the leaves correspond to permutations, not elements. Finally, some forget that the argument needs the algorithm to be correct for every input, which is why every permutation must appear as a leaf.

## Builds On
This concept builds on Elementary Sorts, because it is the question of whether anything beats their quadratic cost and how far one can go in general, with sorted-input behaviour of insertion sort illustrating why the result concerns the worst case. It builds on Asymptotic Notation, since the result is an Omega statement requiring the definition of a lower bound, and on Tree Terminology & Properties for the notions of leaves, height and the relation between height and the maximum number of leaves in a binary tree.

## Leads To
The same decision-tree method proves lower bounds for searching and for selecting the maximum, and it justifies choosing merge sort or heap sort when a worst-case guarantee is needed. It motivates non-comparison methods, such as counting and radix sort, which sidestep the bound by using key structure.

## Check Yourself
**Q1.** Why must a decision tree for sorting n items have at least n! leaves?
**A1.** Each possible input ordering must lead to a distinct correct output, and there are n! orderings.
**Q2.** Why does a tree with n! leaves need height at least log2(n!)?
**A2.** A binary tree of height h has at most 2^h leaves, so 2^h must be at least n!.
**Q3.** Does the bound apply to counting sort?
**A3.** No. It only applies to algorithms that learn about order through comparisons.
