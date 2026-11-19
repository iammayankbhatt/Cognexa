---
id: recurrence_relations
name: "Recurrence Relations & Master Theorem"
cluster: complexity
reviewed: false
sources:
  - "CLRS, Chapter 4 (Divide-and-Conquer), Sections 4.3 to 4.5 (substitution method, recursion tree, Master Theorem)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 2.2 (proposition on mergesort)"
---

## Overview
A recursive algorithm calls itself on smaller inputs, so its running time is described in terms of its own running time on those inputs. Such a description is a recurrence relation, for example T(n) = 2T(n/2) + n for merge sort. Solving the recurrence gives a closed form like Theta(n log n). Three tools do this: unrolling the recurrence by hand, drawing a recursion tree, and the Master Theorem, which gives the answer directly for the common divide-and-conquer shape.

## Intuition
Think of a manager who splits a pile of n forms into two equal piles, hands one pile to each of two assistants who repeat the same trick, and then spends n minutes merging the results. The total time depends on how many levels of splitting happen and how much merging work happens at each level. There are log n levels, and every level has about n minutes of merging in total, so the overall cost is n log n. Drawing that tree of work is the essence of a recursion tree.

## How It Works
A divide-and-conquer recurrence has the form T(n) = a T(n/b) + f(n). The algorithm makes a recursive calls, each on an input of size n divided by b, and does f(n) extra work to split and combine. The base case, such as T(1) = constant, stops the recursion.

To unroll T(n) = 2T(n/2) + n, expand it: T(n) = 2(2T(n/4) + n/2) + n = 4T(n/4) + 2n, and again 8T(n/8) + 3n, and after k expansions 2^k T(n/2^k) + kn. The expansion ends when n/2^k reaches 1, which happens at k = log2 n, giving n T(1) + n log2 n, which is Theta(n log n).

The recursion tree view makes the same point visually. The root costs f(n). Its a children each cost f(n/b), and so on. Level i has a^i nodes each of size n/b^i, so its total cost is a^i f(n/b^i). Add up the levels.

The Master Theorem compares f(n) with n to the power log_b a, which measures the total work done at the leaves. Case 1: if f(n) grows polynomially slower than n^(log_b a), the leaves dominate and T(n) is Theta(n^(log_b a)). Case 2: if f(n) matches it, every level contributes equally and T(n) is Theta(n^(log_b a) log n). Case 3: if f(n) grows polynomially faster (and satisfies a regularity condition), the root dominates and T(n) is Theta(f(n)).

Examples: binary search is T(n) = T(n/2) + 1, so a = 1, b = 2, log_b a = 0, f(n) = 1 matches n to the power 0, and Case 2 gives Theta(log n). Merge sort is a = 2, b = 2, f(n) = n matches n, Case 2 gives Theta(n log n). Strassen-style recursion a = 7, b = 2 with linear combining gives Theta(n to the power log2 7), about n to the power 2.81. A recurrence like T(n) = T(n - 1) + 1, which shrinks by subtraction rather than division, is not covered by the Master Theorem and unrolls to Theta(n).

## Worked Example
Solve T(n) = 4T(n/2) + n.

Here a = 4, b = 2 and f(n) = n. Compute n to the power log_2 4, which is n squared. Since f(n) = n grows polynomially slower than n squared, Case 1 applies and T(n) = Theta(n squared).

Check with a recursion tree: level i has 4^i nodes with size n/2^i, costing n/2^i each, so the level total is 2^i times n. This doubles with every level, so the deepest level (about log2 n levels down) dominates and costs about n squared. Good, both methods agree.

Now merge sort's T(n) = 2T(n/2) + n with T(1) = 0: unrolling gives exactly n log2 n when n is a power of two, which we can check numerically for n = 8: T(8) = 2T(4) + 8 = 2(2T(2) + 4) + 8 = 2(2(2 times 0 + 2) + 4) + 8 = 2(8) + 8 = 24 = 8 times 3.

## Code
The programs compute the recurrences directly and compare them with the closed forms.

```python
import math


def merge_sort_cost(n):
    """T(n) = 2 T(n/2) + n with T(1) = 0 (n a power of two)."""
    if n == 1:
        return 0
    return 2 * merge_sort_cost(n // 2) + n


def binary_search_cost(n):
    """T(n) = T(n/2) + 1 with T(1) = 0."""
    if n == 1:
        return 0
    return binary_search_cost(n // 2) + 1


def four_way_cost(n):
    """T(n) = 4 T(n/2) + n with T(1) = 1."""
    if n == 1:
        return 1
    return 4 * four_way_cost(n // 2) + n


for k in range(1, 11):
    n = 2 ** k
    assert merge_sort_cost(n) == n * k                 # exactly n log2 n
    assert binary_search_cost(n) == k                  # exactly log2 n

# T(n) = 4T(n/2) + n is Theta(n^2): the ratio T(n) / n^2 stays bounded.
ratios = [four_way_cost(2 ** k) / (4 ** k) for k in range(1, 15)]
assert max(ratios) < 2.0 and min(ratios) > 1.0
assert merge_sort_cost(8) == 24 == 8 * int(math.log2(8))
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>

long long mergeSortCost(long long n) {  // T(n) = 2T(n/2) + n, T(1) = 0
    if (n == 1) return 0;
    return 2 * mergeSortCost(n / 2) + n;
}

int binarySearchCost(long long n) {  // T(n) = T(n/2) + 1, T(1) = 0
    if (n == 1) return 0;
    return binarySearchCost(n / 2) + 1;
}

long long fourWayCost(long long n) {  // T(n) = 4T(n/2) + n, T(1) = 1
    if (n == 1) return 1;
    return 4 * fourWayCost(n / 2) + n;
}

int main() {
    long long n = 1;
    for (int k = 1; k <= 10; ++k) {
        n *= 2;
        assert(mergeSortCost(n) == n * k);
        assert(binarySearchCost(n) == k);
    }
    assert(mergeSortCost(8) == 24);
    // fourWayCost(2^k) equals 2 * 4^k - 2^k, which is Theta(n^2).
    assert(fourWayCost(8) == 2 * 64 - 8);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
The results of the standard recurrences are worth knowing by heart: T(n) = T(n/2) + 1 is Theta(log n) (binary search), T(n) = 2T(n/2) + n is Theta(n log n) (merge sort), T(n) = 2T(n/2) + 1 is Theta(n) (tree traversal), T(n) = T(n - 1) + 1 is Theta(n) (simple recursion), T(n) = T(n - 1) + n is Theta(n squared), and T(n) = 2T(n - 1) + 1 is Theta(2 to the power n) (naive subset recursion or towers of Hanoi). Solving a recurrence by unrolling takes O(1) space on paper, and checking it numerically as above takes O(n) time. The depth of recursion, which drives stack space, is log n when the input is divided and n when it shrinks by a constant.

## Common Mistakes & Misconceptions
A common symptom is deriving the wrong total, for example claiming merge sort is O(n) because "each level is linear", forgetting that there are log n levels. Students also apply the Master Theorem to recurrences it does not cover, such as T(n) = T(n - 1) + 1 or ones where the subproblem sizes are unequal, or they compare f(n) with n instead of with n to the power log_b a. Mixing up the three cases is frequent: the larger of the two functions wins, and when they match you gain a log factor. Another mistake is ignoring the base case, which fixes the constant, though not the growth. Finally, people forget that floors and ceilings do not change the Theta result, and spend effort on them.

## Builds On
This concept builds on Recursion, because a recurrence is simply the cost function of a recursive algorithm: the recursive calls become terms T(n/b) and the base case becomes the starting value. It also builds on Asymptotic Notation: the answers are given as Theta bounds, and solving a recurrence relies on dropping constants and lower-order terms exactly as defined there.

## Leads To
Divide and conquer uses recurrences to analyse algorithms that split a problem into parts. Merge sort and quicksort are analysed with the recurrences above, and the comparison-sort lower bound and the segment tree both rest on logarithmic depth results. Dynamic programming later removes the repeated work that makes some recurrences exponential.

## Check Yourself
**Q1.** What is the solution of T(n) = T(n/2) + 1?
**A1.** Theta(log n); the problem halves log n times with constant work each time.
**Q2.** Apply the Master Theorem to T(n) = 2T(n/2) + n.
**A2.** a = 2, b = 2, f(n) = n matches n to the power log_2 2 = n, so Case 2 gives Theta(n log n).
**Q3.** Why is T(n) = T(n - 1) + 1 not solved by the Master Theorem?
**A3.** The input shrinks by subtraction, not by division by a constant b, so it must be unrolled instead; the result is Theta(n).
