---
id: dp_classic
name: "Classic DP (knapsack, LCS, LIS, edit distance)"
cluster: paradigms
reviewed: false
sources:
  - "CLRS, Chapter 15 (Dynamic Programming), Section 15.4 (Longest common subsequence) and Problem 15-5 (Edit distance)"
  - "Kleinberg and Tardos, Algorithm Design, Sections 6.4 (Subset sums and knapsacks) and 6.6 (Sequence alignment)"
---

## Overview
Four problems appear in almost every course and interview because together they show the main shapes a dynamic programming state can take. The 0/1 knapsack problem chooses items to maximise value under a weight limit, with a state of (items considered, capacity left). The longest common subsequence (LCS) finds the longest sequence that appears in order in two strings, with a state of (prefix of one string, prefix of the other). The longest increasing subsequence (LIS) finds the longest strictly increasing subsequence of one array, with a state "best ending at index i". Edit distance counts the minimum number of insertions, deletions and substitutions to turn one string into another, used in spell checkers and DNA alignment. Each is solved with a recurrence and a table, and each turns an exponential search into polynomial time.

## Intuition
All four problems are about making a sequence of yes/no or match/skip decisions, where trying every combination would take exponential time. DP notices that the future only depends on a small summary of the past: for knapsack, how much capacity is left; for two strings, how far you have read in each. So instead of remembering every path that led to a situation, you remember only the best answer for each situation, like a traveller who only needs to know the cheapest way to reach each town, not every route they could have taken.

## How It Works
0/1 knapsack. Let best[i][w] be the maximum value using the first i items with capacity w. For item i with weight wt and value v: best[i][w] = best[i - 1][w] (skip it), or if wt <= w, max of that and best[i - 1][w - wt] + v (take it). Answer best[n][W]. With a 1D array, loop w downward so each item is used at most once.

Longest common subsequence. Let L[i][j] be the LCS length of the first i characters of a and the first j characters of b. If a[i - 1] == b[j - 1], then L[i][j] = L[i - 1][j - 1] + 1 (extend a common character); otherwise L[i][j] = max(L[i - 1][j], L[i][j - 1]) (drop a character from one string). Base cases L[0][j] = L[i][0] = 0. Backtracking through the table recovers the subsequence.

Longest increasing subsequence. Let end[i] be the length of the longest increasing subsequence ending exactly at index i: end[i] = 1 + max(end[j] for j < i with a[j] < a[i]), or 1 if none. The answer is the maximum of all end[i]. A faster O(n log n) method keeps tails[k], the smallest possible last value of an increasing subsequence of length k + 1, and uses binary search to place each element.

Edit distance (Levenshtein). Let D[i][j] be the distance between the first i characters of a and the first j of b. Base cases D[i][0] = i and D[0][j] = j. If a[i - 1] == b[j - 1], D[i][j] = D[i - 1][j - 1]; otherwise D[i][j] = 1 + min(D[i - 1][j] (delete), D[i][j - 1] (insert), D[i - 1][j - 1] (substitute)).

Pattern. In each case: define a state by prefixes or remaining resources, write the choice at the last element, fill the table in increasing order of i and j, and read the answer from the final cell.

## Worked Example
Edit distance from "cat" to "cut". Rows are prefixes of "cat" ("", c, ca, cat), columns are prefixes of "cut" ("", c, cu, cut).

```
        ""  c  u  t
   ""    0  1  2  3
   c     1  0  1  2
   a     2  1  1  2
   t     3  2  2  1
```

Row "c": D[1][1] = 0 because c matches c. Row "a": D[2][2] compares a with u (different), so 1 + min(D[1][2] = 1, D[2][1] = 1, D[1][1] = 0) = 1. Row "t": D[3][3] compares t with t, which match, so it copies D[2][2] = 1. The answer is 1, one substitution (a to u). For LCS of "ABCBDAB" and "BDCABA" the same kind of table gives length 4, for example "BCBA". For knapsack with capacity 50 and items (value, weight) (60, 10), (100, 20), (120, 30), the table shows the best value is 220, taking the second and third items.

## Code
```python
from bisect import bisect_left


def knapsack(items, capacity):                    # items: list of (value, weight)
    best = [0] * (capacity + 1)
    for value, weight in items:
        for w in range(capacity, weight - 1, -1):  # downward: each item used at most once
            best[w] = max(best[w], best[w - weight] + value)
    return best[capacity]


def lcs(a, b):
    L = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                L[i][j] = L[i - 1][j - 1] + 1
            else:
                L[i][j] = max(L[i - 1][j], L[i][j - 1])
    out, i, j = [], len(a), len(b)                 # walk back to recover one LCS
    while i and j:
        if a[i - 1] == b[j - 1]:
            out.append(a[i - 1])
            i, j = i - 1, j - 1
        elif L[i - 1][j] >= L[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return L[-1][-1], "".join(reversed(out))


def lis_quadratic(a):
    end = [1] * len(a)
    for i in range(len(a)):
        for j in range(i):
            if a[j] < a[i]:
                end[i] = max(end[i], end[j] + 1)
    return max(end, default=0)


def lis_fast(a):
    tails = []                                      # tails[k]: smallest tail of a length-(k+1) run
    for x in a:
        k = bisect_left(tails, x)
        if k == len(tails):
            tails.append(x)
        else:
            tails[k] = x
    return len(tails)


def edit_distance(a, b):
    D = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        D[i][0] = i
    for j in range(len(b) + 1):
        D[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                D[i][j] = D[i - 1][j - 1]
            else:
                D[i][j] = 1 + min(D[i - 1][j], D[i][j - 1], D[i - 1][j - 1])
    return D[-1][-1]


assert knapsack([(60, 10), (100, 20), (120, 30)], 50) == 220
length, seq = lcs("ABCBDAB", "BDCABA")
assert length == 4 and len(seq) == 4
assert lis_quadratic([10, 9, 2, 5, 3, 7, 101, 18]) == 4 == lis_fast([10, 9, 2, 5, 3, 7, 101, 18])
assert edit_distance("cat", "cut") == 1 and edit_distance("kitten", "sitting") == 3
assert edit_distance("", "abc") == 3

import itertools
import random

random.seed(12)
for _ in range(100):                                # brute-force checks on small inputs
    arr = [random.randint(0, 9) for _ in range(random.randint(0, 8))]
    brute = max((len(c) for r in range(len(arr) + 1) for c in itertools.combinations(arr, r)
                 if all(c[i] < c[i + 1] for i in range(len(c) - 1))), default=0)
    assert lis_quadratic(arr) == lis_fast(arr) == brute
    items = [(random.randint(1, 20), random.randint(1, 10)) for _ in range(random.randint(0, 6))]
    cap = random.randint(0, 25)
    brute_k = max(sum(v for v, _ in c) for r in range(len(items) + 1)
                  for c in itertools.combinations(items, r) if sum(w for _, w in c) <= cap)
    assert knapsack(items, cap) == brute_k
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

int lcsLength(const std::string& a, const std::string& b) {
    std::vector<std::vector<int>> L(a.size() + 1, std::vector<int>(b.size() + 1, 0));
    for (std::size_t i = 1; i <= a.size(); ++i)
        for (std::size_t j = 1; j <= b.size(); ++j)
            L[i][j] = a[i - 1] == b[j - 1] ? L[i - 1][j - 1] + 1 : std::max(L[i - 1][j], L[i][j - 1]);
    return L[a.size()][b.size()];
}

int editDistance(const std::string& a, const std::string& b) {
    std::vector<std::vector<int>> D(a.size() + 1, std::vector<int>(b.size() + 1, 0));
    for (std::size_t i = 0; i <= a.size(); ++i) D[i][0] = static_cast<int>(i);
    for (std::size_t j = 0; j <= b.size(); ++j) D[0][j] = static_cast<int>(j);
    for (std::size_t i = 1; i <= a.size(); ++i)
        for (std::size_t j = 1; j <= b.size(); ++j)
            D[i][j] = a[i - 1] == b[j - 1]
                          ? D[i - 1][j - 1]
                          : 1 + std::min({D[i - 1][j], D[i][j - 1], D[i - 1][j - 1]});
    return D[a.size()][b.size()];
}

int knapsack(const std::vector<std::pair<int, int>>& items, int cap) {
    std::vector<int> best(cap + 1, 0);
    for (const auto& it : items)
        for (int w = cap; w >= it.second; --w) best[w] = std::max(best[w], best[w - it.second] + it.first);
    return best[cap];
}

int main() {
    assert(lcsLength("ABCBDAB", "BDCABA") == 4);
    assert(editDistance("kitten", "sitting") == 3);
    assert(knapsack({{60, 10}, {100, 20}, {120, 30}}, 50) == 220);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
0/1 knapsack takes O(nW) time and O(W) space with the one-dimensional table, where W is the capacity. This is pseudo-polynomial: it is polynomial in the numeric value W, not in the number of bits needed to write W, which is why knapsack is still NP-hard. LCS and edit distance take O(mn) time for strings of length m and n, and O(mn) space for the full table (needed to reconstruct the answer) or O(min(m, n)) for the length only. LIS takes O(n squared) with the simple DP and O(n log n) with the tails-and-binary-search method.

## Common Mistakes & Misconceptions
In 0/1 knapsack with a 1D array, looping capacity upward lets one item be taken many times (that solves the unbounded knapsack instead), giving answers that are too large. Off-by-one errors between table indexes and string indexes are common: L[i][j] refers to a[i - 1] and b[j - 1], and mixing them causes IndexError or wrong lengths. Students confuse a subsequence (characters in order, possibly with gaps) with a substring (contiguous), and LCS with longest common substring, which uses a different recurrence. In LIS, forgetting whether "increasing" is strict or non-strict changes the answer, and the tails array in the fast method is not itself an increasing subsequence of the input. In edit distance, wrong base cases (zeros instead of i and j) make transforming to or from an empty string cost nothing. Another misconception is that knapsack's O(nW) means it is polynomial.

## Builds On
This concept builds on Dynamic Programming (memoization & tabulation). Every one of these problems follows the same steps from there: define a state that summarises the past (remaining capacity, string prefixes, the index where a subsequence ends), write a recurrence that chooses between a few options at the last element, set base cases, fill a table in dependency order and optionally reconstruct the choices. The memo-versus-table trade-offs, the "states times work per state" cost rule and space optimisation by keeping only the previous row all carry over directly.

## Leads To
These problems are templates for many applications: diff tools and version control use LCS, spell checkers and DNA sequence alignment (Needleman-Wunsch, Smith-Waterman) use edit distance, resource allocation and budgeting use knapsack, and patience sorting and scheduling use LIS. They also lead to the idea of pseudo-polynomial time and NP-hardness, and to more advanced DP such as interval DP, bitmask DP and DP on trees.

## Check Yourself
**Q1.** What is the LCS recurrence when the last characters match?
**A1.** L[i][j] = L[i - 1][j - 1] + 1.
**Q2.** Why must the capacity loop go downward in a 1D 0/1 knapsack?
**A2.** So that each item is counted at most once; going upward reuses the same item.
**Q3.** What is the edit distance between "kitten" and "sitting"?
**A3.** 3 (two substitutions and one insertion).
