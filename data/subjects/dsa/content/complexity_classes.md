---
id: complexity_classes
name: "P, NP & NP-Completeness"
cluster: paradigms
reviewed: false
sources:
  - "CLRS, Chapter 34 (NP-Completeness), Sections 34.1 to 34.3"
  - "Kleinberg and Tardos, Algorithm Design, Chapter 8 (NP and Computational Intractability)"
---

## Overview
Complexity classes group decision problems (questions with a yes or no answer) by how much time they need. P is the class of problems that can be solved in polynomial time, O(n^k) for some constant k, such as sorting, shortest paths and minimum spanning trees. NP is the class of problems whose yes answers can be verified in polynomial time given a suitable certificate (a proposed solution), such as "is there a subset of these numbers summing to T?" or "does this graph have a route visiting every city with total length at most L?". Every problem in P is also in NP. An NP-complete problem is one in NP to which every NP problem can be reduced in polynomial time, so a fast algorithm for any NP-complete problem would give fast algorithms for all of NP. Whether P equals NP is the most famous open question in computer science; most researchers believe P is not equal to NP. Recognising an NP-complete problem tells you to stop searching for an exact fast algorithm and to use approximation, heuristics, or exponential search with pruning instead.

## Intuition
Solving a Sudoku from scratch can take a long time, but checking a completed grid takes a minute: look at every row, column and box. NP captures exactly the problems that are easy to check. P captures those that are easy to solve. The P versus NP question asks whether every problem that is easy to check is also easy to solve. NP-complete problems are the hardest ones in NP, the "universal" puzzles: if you found a quick way to solve one, you could translate every other easy-to-check puzzle into it and solve them all quickly.

## How It Works
Decision versus optimisation. Complexity classes are defined for yes/no questions. The optimisation problem "find the shortest tour" corresponds to the decision problem "is there a tour of length at most L?". A fast algorithm for one usually gives a fast algorithm for the other.

Polynomial time. An algorithm is efficient in this theory if its worst-case running time is bounded by a polynomial in the input size, using asymptotic notation. O(n log n) and O(n^3) are polynomial; O(2^n) and O(n!) are not. The input size is the number of bits, which is why knapsack's O(nW) is not polynomial: W can be exponential in the number of bits used to write it.

Verification and certificates. A problem is in NP if there is a polynomial-time verifier that, given an instance and a certificate, accepts exactly when the certificate proves the answer is yes. For subset sum the certificate is the chosen subset; the verifier adds it up in O(n). Finding the certificate might require trying exponentially many candidates, which is what backtracking does.

Reductions. A polynomial-time reduction from problem A to problem B transforms any instance of A into an instance of B with the same answer. If A reduces to B, then B is at least as hard as A: a fast algorithm for B gives one for A. Reductions are how hardness is spread from one problem to another.

NP-hard and NP-complete. A problem is NP-hard if every NP problem reduces to it, and NP-complete if it is NP-hard and also in NP. The Cook-Levin theorem showed that Boolean satisfiability (SAT) is NP-complete; thousands of problems were then proved NP-complete by reducing a known NP-complete problem to them: 3-SAT, vertex cover, independent set, clique, Hamiltonian cycle, travelling salesman (decision), subset sum, graph colouring and 0/1 knapsack (decision).

To prove a new problem X is NP-complete: show X is in NP (give a verifier), then reduce a known NP-complete problem to X.

Coping in practice. Use exponential algorithms with good pruning (backtracking, branch and bound) for small inputs, dynamic programming when numbers are small (pseudo-polynomial), approximation algorithms with guarantees (a 2-approximation for vertex cover), heuristics and SAT solvers, or restrict to special cases that are in P (2-SAT, trees, bipartite graphs).

## Worked Example
Subset sum: numbers [3, 34, 4, 12, 5, 2] and target 9. Verification: given the certificate {4, 5}, check that both are in the list and that 4 + 5 = 9. This takes time linear in the size of the certificate, so subset sum is in NP. Solving: without a certificate, a straightforward backtracking search examines subsets one by one, up to 2^6 = 64 for six numbers and about 10^18 for sixty numbers.

A reduction: a set S of vertices is an independent set (no edge inside S) exactly when the remaining vertices V minus S form a vertex cover (every edge has an endpoint outside S). So "is there an independent set of size at least k?" becomes "is there a vertex cover of size at most |V| - k?".

```
   0 --- 1
   |     |
   3 --- 2
```

In this 4-cycle, {0, 2} is an independent set of size 2, and its complement {1, 3} is a vertex cover of size 2: each of the four edges touches 1 or 3. The transformation is trivial to compute, so the two problems are equally hard.

## Code
```python
from itertools import combinations


def verify_subset_sum(numbers, target, certificate):
    """Polynomial-time verifier: is the certificate a sub-multiset of numbers that sums to target?"""
    pool = list(numbers)
    for x in certificate:
        if x not in pool:
            return False
        pool.remove(x)
    return sum(certificate) == target


def solve_subset_sum(numbers, target):
    """Exponential search over all 2^n subsets (no known polynomial algorithm)."""
    for r in range(len(numbers) + 1):
        for combo in combinations(numbers, r):
            if sum(combo) == target:
                return list(combo)
    return None


def is_independent_set(edges, s):
    return all(not (u in s and v in s) for u, v in edges)


def is_vertex_cover(edges, c):
    return all(u in c or v in c for u, v in edges)


def max_independent_set(n, edges):
    for k in range(n, -1, -1):
        for s in combinations(range(n), k):
            if is_independent_set(edges, set(s)):
                return set(s)


nums = [3, 34, 4, 12, 5, 2]
assert verify_subset_sum(nums, 9, [4, 5])
assert not verify_subset_sum(nums, 9, [4, 4, 1])
assert verify_subset_sum(nums, 9, solve_subset_sum(nums, 9))
assert solve_subset_sum(nums, 30) is None

cycle = [(0, 1), (1, 2), (2, 3), (3, 0)]
assert is_independent_set(cycle, {0, 2}) and is_vertex_cover(cycle, {1, 3})

import random

random.seed(14)
for _ in range(100):                             # the reduction: S independent <=> V \ S is a cover
    n = random.randint(1, 7)
    edges = [(u, v) for u in range(n) for v in range(u + 1, n) if random.random() < 0.4]
    for k in range(n + 1):
        for s in combinations(range(n), k):
            rest = set(range(n)) - set(s)
            assert is_independent_set(edges, set(s)) == is_vertex_cover(edges, rest)
    best = max_independent_set(n, edges)
    assert is_vertex_cover(edges, set(range(n)) - best)
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

// Polynomial-time verifier for subset sum: the chosen indexes must be distinct and sum to target.
bool verify(const std::vector<int>& nums, int target, std::vector<int> chosen) {
    std::sort(chosen.begin(), chosen.end());
    if (std::adjacent_find(chosen.begin(), chosen.end()) != chosen.end()) return false;
    long long sum = 0;
    for (int i : chosen) {
        if (i < 0 || i >= static_cast<int>(nums.size())) return false;
        sum += nums[i];
    }
    return sum == target;
}

// Exponential solver: tries all 2^n subsets as bitmasks.
bool solve(const std::vector<int>& nums, int target) {
    int n = static_cast<int>(nums.size());
    for (int mask = 0; mask < (1 << n); ++mask) {
        long long sum = 0;
        for (int i = 0; i < n; ++i)
            if (mask & (1 << i)) sum += nums[i];
        if (sum == target) return true;
    }
    return false;
}

int main() {
    std::vector<int> nums = {3, 34, 4, 12, 5, 2};
    assert(verify(nums, 9, {2, 4}));        // indexes of 4 and 5
    assert(!verify(nums, 9, {2, 2}));
    assert(solve(nums, 9) && !solve(nums, 30));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Problems in P have algorithms with worst-case time O(n^k) for some constant k. For NP-complete problems, the best known exact algorithms take exponential time, for example O(2^n * n) for subset sum by enumeration, O(2^(n/2)) by meet in the middle, or O(n^2 2^n) for travelling salesman by dynamic programming over subsets; no polynomial algorithm is known and none exists if P is not equal to NP. Verifying a certificate for an NP problem takes polynomial time, often linear. Reductions used in proofs must themselves run in polynomial time, otherwise they would hide the hardness. Pseudo-polynomial algorithms such as O(nW) for knapsack are fast only when the numbers are small.

## Common Mistakes & Misconceptions
The most widespread misconception is that NP means "not polynomial"; it stands for nondeterministic polynomial time and includes all of P. Students reverse the direction of reductions: to show a new problem X is hard you reduce a known hard problem to X, not X to the known problem. Another error is thinking NP-complete problems can never be solved; small or structured instances are solved routinely, and good heuristics handle large practical ones. People call knapsack's O(nW) algorithm polynomial, forgetting that input size is measured in bits. NP-hard and NP-complete are often confused: NP-hard problems need not be in NP (the halting problem is NP-hard but undecidable). Finally, an exponential worst case does not mean every input is slow, and a problem being in NP does not mean it is hard, since sorting is in NP too.

## Builds On
This concept builds on Asymptotic Notation, because the whole classification depends on separating polynomial bounds such as O(n^3) from exponential ones such as O(2^n), and on measuring growth as a function of input size. It builds on Backtracking, which is the natural exact algorithm for NP problems: it searches the exponential space of candidate certificates and prunes where it can, which makes concrete why finding a solution can be so much harder than checking one.

## Leads To
Understanding NP-completeness leads to approximation algorithms (guaranteed near-optimal answers, such as a 2-approximation for vertex cover or Christofides' algorithm for metric travelling salesman), parameterised and exponential-time algorithms, SAT and integer-programming solvers, randomised and heuristic search, and to cryptography, which relies on problems believed to be hard. It also frames the limits of computation more broadly, including undecidable problems such as the halting problem.

## Check Yourself
**Q1.** What does it mean for a problem to be in NP?
**A1.** A yes answer can be verified in polynomial time given a suitable certificate.
**Q2.** What would a polynomial-time algorithm for an NP-complete problem imply?
**A2.** That every problem in NP can be solved in polynomial time, so P = NP.
**Q3.** To prove a new problem X is NP-hard, which direction should the reduction go?
**A3.** From a known NP-complete problem to X.
