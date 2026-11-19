---
id: greedy
name: "Greedy Algorithms"
cluster: paradigms
reviewed: false
sources:
  - "CLRS, Chapter 16 (Greedy Algorithms), Sections 16.1 and 16.2"
  - "Kleinberg and Tardos, Algorithm Design, Chapter 4 (Greedy Algorithms)"
---

## Overview
A greedy algorithm builds a solution step by step, at each step taking the choice that looks best right now, and never reconsidering it. When it works, it is usually simple and fast, often just a sort followed by one pass. The catch is that a locally best choice does not always lead to a globally best solution, so every greedy algorithm needs a proof that its rule is safe for the problem at hand. Classic successes include activity selection (interval scheduling), fractional knapsack, Huffman coding, Dijkstra's shortest paths and minimum spanning trees. Classic failures include 0/1 knapsack and coin change with arbitrary coin values, which need dynamic programming.

## Intuition
Imagine a cashier giving change with the fewest coins using Indian or US coins: always hand over the largest coin that does not exceed the remaining amount. For those coin systems this works perfectly. But if the only coins were 1, 3 and 4 and you owed 6, the greedy cashier would give 4 + 1 + 1 (three coins) while 3 + 3 (two coins) is better. Greedy is like always taking the biggest bite available: excellent when the problem's structure rewards it, misleading when an early big bite blocks a better combination later.

## How It Works
Recipe. (1) Decide a rule for the next choice, usually "pick the item that is best according to some key". (2) Often sort the items by that key. (3) Scan once, adding each item if it is still compatible with what has been chosen. (4) Prove the rule is correct.

Two properties that make greedy correct. Greedy-choice property: there is an optimal solution that includes the greedy first choice, so committing to it loses nothing. Optimal substructure: after making the greedy choice, what remains is a smaller instance of the same problem, whose optimal solution combined with the choice is optimal overall.

Proof technique, exchange argument. Take any optimal solution that differs from the greedy one. Swap one of its choices for the greedy choice and show the solution does not get worse. Repeating the swap turns the optimal solution into the greedy one without losing value, so greedy is optimal.

Activity selection. Given intervals with start and finish times, choose the maximum number of non-overlapping intervals. Rule: sort by finish time and repeatedly take the interval that finishes earliest among those starting after the last chosen one ends. Finishing earliest leaves the most room for the rest. Sorting by start time or by shortest length does not work in general.

Fractional knapsack. Items can be split. Sort by value per unit weight and take as much as possible of the best ratio first. This is optimal for the fractional version, but for 0/1 knapsack (items cannot be split) the same rule can fail badly.

When greedy fails. If a choice affects which later choices are possible in complicated ways, there may be no safe local rule. Then use dynamic programming (which considers all options for each subproblem) or backtracking. A quick test: try to construct a small counterexample before trusting a greedy rule.

## Worked Example
Activities (start, finish): A (1, 4), B (3, 5), C (0, 6), D (5, 7), E (3, 9), F (5, 9), G (6, 10), H (8, 11), I (8, 12), J (2, 14), K (12, 16). Sort by finish time; the order is A, B, C, D, E, F, G, H, I, J, K.

```
time  0    2    4    6    8    10   12   14   16
A      |---|                               chosen
D           ....|--|                       chosen
H                   ...|---|               chosen
K                            ....|----|    chosen
```

Take A (ends at 4). B starts at 3, overlapping, so skip it; C starts at 0, skip. D starts at 5 after 4, so take it (ends at 7). E and F start before 7, skip; G starts at 6, skip. H starts at 8, take it (ends at 11). I starts at 8, before 11, skip; J skip. K starts at 12, take it. Four activities: A, D, H, K, which is the maximum possible. Choosing the shortest interval first or the earliest start first can give fewer.

## Code
```python
def activity_selection(intervals):
    chosen, last_end = [], float("-inf")
    for start, end in sorted(intervals, key=lambda iv: iv[1]):   # earliest finish first
        if start >= last_end:
            chosen.append((start, end))
            last_end = end
    return chosen


def fractional_knapsack(items, capacity):
    total = 0.0
    for value, weight in sorted(items, key=lambda it: it[0] / it[1], reverse=True):
        take = min(weight, capacity)
        total += value * take / weight
        capacity -= take
        if capacity == 0:
            break
    return total


def greedy_coins(coins, amount):
    used = []
    for c in sorted(coins, reverse=True):
        while amount >= c:
            amount -= c
            used.append(c)
    return used if amount == 0 else None


def optimal_coins(coins, amount):                         # dynamic programming reference
    best = [0] + [float("inf")] * amount
    for a in range(1, amount + 1):
        best[a] = min((best[a - c] + 1 for c in coins if c <= a), default=float("inf"))
    return best[amount]


acts = [(1, 4), (3, 5), (0, 6), (5, 7), (3, 9), (5, 9), (6, 10), (8, 11), (8, 12), (2, 14), (12, 16)]
assert activity_selection(acts) == [(1, 4), (5, 7), (8, 11), (12, 16)]
assert abs(fractional_knapsack([(60, 10), (100, 20), (120, 30)], 50) - 240.0) < 1e-9
assert greedy_coins([1, 2, 5, 10], 18) == [10, 5, 2, 1]
assert len(greedy_coins([1, 2, 5, 10], 18)) == optimal_coins([1, 2, 5, 10], 18)   # canonical coins: greedy is optimal
assert greedy_coins([1, 3, 4], 6) == [4, 1, 1] and optimal_coins([1, 3, 4], 6) == 2  # greedy fails here

import itertools
import random

random.seed(6)
for _ in range(200):                                      # brute-force check of activity selection
    ivs = []
    for _ in range(random.randint(0, 7)):
        s = random.randint(0, 10)
        ivs.append((s, s + random.randint(1, 5)))
    best = 0
    for r in range(len(ivs) + 1):
        for combo in itertools.combinations(ivs, r):
            srt = sorted(combo, key=lambda iv: iv[1])
            if all(srt[i][1] <= srt[i + 1][0] for i in range(len(srt) - 1)):
                best = max(best, r)
    assert len(activity_selection(ivs)) == best
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <limits>
#include <utility>
#include <vector>

std::vector<std::pair<int, int>> activitySelection(std::vector<std::pair<int, int>> iv) {
    std::sort(iv.begin(), iv.end(), [](const std::pair<int, int>& a, const std::pair<int, int>& b) {
        return a.second < b.second;                  // earliest finish first
    });
    std::vector<std::pair<int, int>> chosen;
    int lastEnd = std::numeric_limits<int>::min();
    for (const auto& p : iv) {
        if (p.first >= lastEnd) {
            chosen.push_back(p);
            lastEnd = p.second;
        }
    }
    return chosen;
}

int main() {
    std::vector<std::pair<int, int>> acts = {{1, 4}, {3, 5}, {0, 6}, {5, 7}, {3, 9}, {5, 9},
                                             {6, 10}, {8, 11}, {8, 12}, {2, 14}, {12, 16}};
    auto chosen = activitySelection(acts);
    assert(chosen.size() == 4);
    assert(chosen[0] == std::make_pair(1, 4) && chosen[3] == std::make_pair(12, 16));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Most greedy algorithms are dominated by an initial sort, O(n log n), followed by a linear scan, so activity selection and fractional knapsack are O(n log n) time and O(n) or O(1) extra space. Greedy algorithms that repeatedly need the current best item use a priority queue, giving O(n log n) or O((V + E) log V) as in Huffman coding and Dijkstra. Greedy coin change is O(number of coins used) but only correct for canonical coin systems. The low cost is the attraction; the risk is correctness, not speed.

## Common Mistakes & Misconceptions
The biggest mistake is assuming a greedy rule is correct because it works on a few examples; always look for a counterexample or a proof. In activity selection, sorting by start time or by duration instead of by finish time gives fewer activities on some inputs. Students apply the fractional knapsack ratio rule to 0/1 knapsack and get suboptimal answers, for example capacity 50 with items (60, 10), (100, 20), (120, 30): greedy by ratio takes the first two for 160, while the best is 220. Coin change greedy fails for coin sets such as {1, 3, 4}. Using strict instead of non-strict comparison (start > last_end) rejects intervals that touch at an endpoint, which changes the answer depending on whether touching is allowed. Another misconception is that greedy and dynamic programming are interchangeable; greedy commits to one choice, while DP compares all choices.

## Builds On
This concept builds on Elementary Sorts (bubble, selection, insertion; stability). Almost every greedy algorithm starts by ordering the items by the greedy key (finish time, value per weight, edge weight), so understanding sorting, its cost and stability (how ties keep their order, which can decide which of two equal items is chosen) is the first step. Selection sort is itself greedy: it repeatedly picks the smallest remaining element.

## Leads To
Dijkstra's Shortest Path greedily settles the nearest unvisited vertex, and Minimum Spanning Tree algorithms (Kruskal and Prim) greedily add the cheapest safe edge; both are proved correct with exchange or cut arguments. Greedy ideas also give Huffman coding for compression, scheduling to minimise lateness, and approximation algorithms for hard problems, and comparing greedy failures with dynamic programming shows when exhaustive comparison is needed.

## Check Yourself
**Q1.** What makes a greedy algorithm correct for a problem?
**A1.** The greedy-choice property together with optimal substructure, usually shown by an exchange argument.
**Q2.** Which rule solves activity selection optimally?
**A2.** Repeatedly pick the compatible activity with the earliest finish time.
**Q3.** Give a coin set where greedy change-making fails.
**A3.** Coins {1, 3, 4} for amount 6: greedy gives 4 + 1 + 1, but 3 + 3 uses fewer coins.
