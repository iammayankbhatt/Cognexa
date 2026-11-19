---
id: dp_fundamentals
name: "Dynamic Programming (memoization & tabulation)"
cluster: paradigms
reviewed: false
sources:
  - "CLRS, Chapter 15 (Dynamic Programming), Sections 15.1 and 15.3"
  - "Kleinberg and Tardos, Algorithm Design, Chapter 6 (Dynamic Programming)"
---

## Overview
Dynamic programming (DP) solves a problem by breaking it into smaller subproblems, solving each subproblem only once, and storing its answer so it can be reused. It applies when a problem has optimal substructure (the answer can be built from answers to subproblems) and overlapping subproblems (the same subproblems come up again and again). There are two ways to implement it. Memoization (top-down) keeps the natural recursive solution and caches each result the first time it is computed. Tabulation (bottom-up) fills a table in an order where every subproblem's dependencies are already filled. Either way, an exponential recursion often becomes polynomial: naive Fibonacci takes about 1.6^n calls, while DP takes n steps.

## Intuition
Ask someone to add 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 and they count to 8. Write "+ 1" on the end and ask again: they instantly say 9, because they remembered the previous total instead of recounting. DP is that habit of remembering. A plain recursive solution keeps recomputing the same totals in different branches, and DP writes each one down the first time so every later request is a quick lookup.

## How It Works
Step 1, define the state. Decide what a subproblem is and what parameters identify it, for example "f(i) = the number of ways to climb i stairs" or "best(i, w) = the best value using the first i items with capacity w". A good state captures everything the future depends on and nothing more.

Step 2, write the recurrence. Express the answer for a state in terms of smaller states, such as f(i) = f(i - 1) + f(i - 2) for climbing one or two steps at a time. The recurrence must eventually reach base cases, such as f(0) = 1 and f(1) = 1.

Step 3a, memoization (top-down). Write the recursive function directly from the recurrence and add a cache (a dictionary, an array, or Python's functools.lru_cache). Before computing a state, check the cache; after computing it, store it. Only states that are actually needed are computed, but recursion depth can be large.

Step 3b, tabulation (bottom-up). Allocate an array (often a dynamic array sized to the number of states), fill in the base cases, then loop over states in an order such that every state's dependencies are already filled, for example i from 2 to n. There is no recursion, so no stack overflow, and loops are often faster.

Step 4, reconstruct the solution if needed. Store the choice made at each state (or recompute it by checking which option achieved the stored value) and walk back from the final state.

Space optimisation. If a state depends only on the previous few states, keep only those: Fibonacci needs just two variables, and many 2D tables need only the previous row.

DP versus divide and conquer. Merge sort splits into independent halves that never overlap, so caching would not help. DP is useful exactly when subproblems overlap. DP versus greedy: greedy commits to one choice per step, DP compares all choices for each subproblem and keeps the best.

## Worked Example
Count the ways to climb n = 5 stairs taking 1 or 2 steps at a time. The state f(i) is the number of ways to reach step i, with f(0) = 1 (stand still) and f(1) = 1. Recurrence: f(i) = f(i - 1) + f(i - 2), because the last move was either one step from i - 1 or two steps from i - 2.

```
i     0  1  2  3  4  5
f(i)  1  1  2  3  5  8
```

Tabulation fills the table left to right: f(2) = 1 + 1 = 2, f(3) = 2 + 1 = 3, f(4) = 3 + 2 = 5, f(5) = 5 + 3 = 8. The naive recursion for f(5) would compute f(3) twice, f(2) three times and f(1) five times; for n = 40 it makes hundreds of millions of calls, while the table needs 41 entries. The memoized version gives the same table but fills it in the order the recursion first finishes each state.

## Code
```python
from functools import lru_cache


calls = 0


def fib_naive(n):
    global calls
    calls += 1
    return n if n < 2 else fib_naive(n - 1) + fib_naive(n - 2)


def fib_memo(n, memo=None):
    memo = {} if memo is None else memo
    if n < 2:
        return n
    if n not in memo:                                   # compute each state once
        memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)
    return memo[n]


def fib_table(n):
    if n < 2:
        return n
    table = [0] * (n + 1)
    table[1] = 1
    for i in range(2, n + 1):                           # dependencies are already filled
        table[i] = table[i - 1] + table[i - 2]
    return table[n]


def fib_two_vars(n):                                    # O(1) space
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


@lru_cache(maxsize=None)
def grid_paths(r, c):                                   # moves right or down only
    if r == 0 or c == 0:
        return 1
    return grid_paths(r - 1, c) + grid_paths(r, c - 1)


def climb(n):
    f = [1, 1] + [0] * max(0, n - 1)
    for i in range(2, n + 1):
        f[i] = f[i - 1] + f[i - 2]
    return f[n]


assert fib_naive(20) == 6765 and calls == 21891          # exponential number of calls
assert fib_memo(20) == fib_table(20) == fib_two_vars(20) == 6765
assert fib_table(90) == 2880067194370816120              # instant with DP
assert [climb(i) for i in range(6)] == [1, 1, 2, 3, 5, 8]
assert grid_paths(2, 2) == 6 and grid_paths(10, 10) == 184756
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

long long fibMemo(int n, std::vector<long long>& memo) {
    if (n < 2) return n;
    if (memo[n] != -1) return memo[n];                 // already computed
    return memo[n] = fibMemo(n - 1, memo) + fibMemo(n - 2, memo);
}

long long fibTable(int n) {
    if (n < 2) return n;
    std::vector<long long> t(n + 1, 0);
    t[1] = 1;
    for (int i = 2; i <= n; ++i) t[i] = t[i - 1] + t[i - 2];
    return t[n];
}

int main() {
    std::vector<long long> memo(91, -1);
    assert(fibMemo(90, memo) == 2880067194370816120LL);
    assert(fibTable(90) == 2880067194370816120LL);
    assert(fibTable(20) == 6765);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
The running time of a DP is (number of distinct states) times (work per state). Fibonacci has n states with O(1) work, so O(n) time, compared with about O(1.618^n) for the naive recursion. A 2D table such as grid paths with r by c states is O(rc). Space is the size of the table, O(number of states), and can often be reduced to the last row or the last few values. Memoization adds recursion depth up to the longest chain of dependencies (n for Fibonacci), while tabulation uses loops and has no recursion overhead.

## Common Mistakes & Misconceptions
A typical symptom of missing memoization is a program that works for small inputs but hangs for n around 40 or more, because the same subproblems are recomputed exponentially often. With memoization, a deep chain such as fib_memo(5000) can crash with RecursionError: maximum recursion depth exceeded, which tabulation avoids. Using a mutable default argument as a cache (def f(n, memo={})) silently shares the cache between unrelated calls. In tabulation, filling the table in the wrong order reads values that have not been computed yet (still 0), producing answers that are too small. A state that leaves out needed information (for example knapsack state with only the item index and no remaining capacity) gives wrong answers. Students also think any recursion benefits from DP; without overlapping subproblems, as in merge sort, caching saves nothing.

## Builds On
This concept builds on Recursion. Memoization is the recursive solution with a cache added, so expressing a problem as a recurrence with base cases, and understanding the recursion tree that shows repeated calls, is the starting point for every DP. It also builds on Dynamic Arrays, since tabulation stores answers in an array (or array of arrays) indexed by state, allocated once to the right size or grown as needed, and constant-time indexing is what makes each lookup O(1).

## Leads To
Classic DP problems (knapsack, longest common subsequence, longest increasing subsequence, edit distance) apply these steps to two-dimensional states. Floyd-Warshall is a DP over allowed intermediate vertices, Bellman-Ford can be read as a DP over path lengths, and DP on DAGs uses topological order. Further topics include bitmask DP, interval DP and DP on trees.

## Check Yourself
**Q1.** What two properties must a problem have for DP to help?
**A1.** Optimal substructure and overlapping subproblems.
**Q2.** What is the difference between memoization and tabulation?
**A2.** Memoization caches results of a top-down recursion; tabulation fills a table bottom-up in dependency order.
**Q3.** How is the running time of a DP estimated?
**A3.** Number of distinct states multiplied by the work done per state.
