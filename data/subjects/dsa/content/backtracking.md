---
id: backtracking
name: "Backtracking"
cluster: paradigms
reviewed: false
sources:
  - "Skiena, The Algorithm Design Manual, 2nd ed., Section 7.1 (Backtracking)"
  - "Kleinberg and Tardos, Algorithm Design, Chapter 8 introduction (search and intractability)"
---

## Overview
Backtracking is a systematic way to search through all candidate solutions of a problem by building a solution one choice at a time and abandoning (backtracking from) a partial solution as soon as it cannot possibly lead to a valid answer. It is a depth-first search over a tree of choices, implemented naturally with recursion: choose an option, recurse to make the remaining choices, then undo the option and try the next one. Backtracking solves constraint problems such as N-Queens, Sudoku, generating all subsets, permutations or combinations, finding paths in a maze, and the subset-sum problem. Its worst case is exponential, but pruning dead branches early often makes it fast enough in practice.

## Intuition
Think of finding your way through a maze by hand. At each junction you pick a corridor. If it leads to a dead end, you walk back to the last junction and try a different corridor. You never re-explore a corridor you already ruled out from that junction, and you stop exploring a direction as soon as you can see it is a dead end. Backtracking does the same thing with decisions: make a choice, see whether you can keep going, and if not, undo the choice and try the next one.

## How It Works
The template. A recursive function receives the current partial solution. If the partial solution is complete, record it (or return success). Otherwise, for each possible next choice: if the choice is consistent with the constraints, apply it, recurse, and then undo it. The "undo" step is what restores the state so the next choice starts from the same situation.

The state-space tree. Each node of the implicit tree is a partial solution, each edge is one choice, and the leaves are complete candidates. Plain brute force would visit every leaf. Backtracking walks this tree depth-first and cuts off (prunes) any subtree whose root already violates a constraint, so it never visits the leaves below it.

Pruning. The power of backtracking comes from checking constraints early. In N-Queens, a queen is placed only in a column and diagonal that are not attacked, so impossible boards are never extended. In subset-sum with positive numbers, if the running sum already exceeds the target, the branch is cut. Sorting the choices or trying the most constrained choice first can prune even more.

Generating combinatorial objects. All subsets: for each element decide "include" or "exclude", giving 2^n leaves. All permutations: at each position try every unused element, giving n! leaves. Combinations of size k: include elements in increasing order and stop when k are chosen.

State and undo. The state can be passed as arguments (copying, simple but slower) or kept in shared structures that are modified and restored (faster). A common bug is forgetting to undo, which leaks one branch's choices into another.

Relationship to other ideas. Backtracking is depth-first search on an implicit graph. When the same subproblems recur, memoizing them turns backtracking into dynamic programming. Branch and bound adds a cost bound to prune optimisation problems.

## Worked Example
Place 4 queens on a 4 by 4 board so that no two attack each other, one queen per row. Row 0: try column 0. Row 1: columns 0 and 1 are attacked (same column and diagonal), so try column 2. Row 2: every column is attacked (0 by column, 1 by diagonal from row 1, 2 by column, 3 by diagonal from row 1), so backtrack. Row 1: try column 3. Row 2: column 1 is safe. Row 3: every column is attacked, so backtrack to row 2, which has no other safe column, then to row 1, which has no more columns, then to row 0. Row 0: try column 1. Row 1: column 3 is safe. Row 2: column 0 is safe. Row 3: column 2 is safe. Solution found.

```
. Q . .
. . . Q
Q . . .
. . Q .
```

Continuing the search finds exactly one more solution, its mirror image (columns 2, 0, 3, 1), so 4-Queens has 2 solutions. A brute force over all 4^4 = 256 placements would examine many more boards.

## Code
```python
def n_queens(n):
    cols, diag, anti = set(), set(), set()
    placement, solutions = [], []

    def place(row):
        if row == n:
            solutions.append(list(placement))
            return
        for c in range(n):
            if c in cols or (row - c) in diag or (row + c) in anti:
                continue                                    # prune: attacked square
            cols.add(c)
            diag.add(row - c)
            anti.add(row + c)
            placement.append(c)
            place(row + 1)
            placement.pop()                                 # undo the choice
            cols.remove(c)
            diag.remove(row - c)
            anti.remove(row + c)

    place(0)
    return solutions


def subsets(items):
    out, current = [], []

    def go(i):
        if i == len(items):
            out.append(list(current))
            return
        current.append(items[i])                             # include items[i]
        go(i + 1)
        current.pop()                                        # undo
        go(i + 1)                                            # exclude items[i]

    go(0)
    return out


def subset_sum(nums, target):
    nums = sorted(nums)
    result = []

    def go(start, remaining, chosen):
        if remaining == 0:
            result.append(list(chosen))
            return
        for i in range(start, len(nums)):
            if nums[i] > remaining:
                break                                        # prune: sorted, so later items are bigger
            if i > start and nums[i] == nums[i - 1]:
                continue                                     # skip duplicate choices
            chosen.append(nums[i])
            go(i + 1, remaining - nums[i], chosen)
            chosen.pop()

    go(0, target, [])
    return result


assert n_queens(4) == [[1, 3, 0, 2], [2, 0, 3, 1]]
assert len(n_queens(6)) == 4 and len(n_queens(8)) == 92
assert subsets([1, 2, 3]) == [[1, 2, 3], [1, 2], [1, 3], [1], [2, 3], [2], [3], []]
assert subset_sum([10, 1, 2, 7, 6, 1, 5], 8) == [[1, 1, 6], [1, 2, 5], [1, 7], [2, 6]]
assert subset_sum([3, 5], 1) == []
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

class NQueens {
public:
    explicit NQueens(int n) : n_(n), cols_(n, false), diag_(2 * n, false), anti_(2 * n, false) {}

    int count() {
        solutions_ = 0;
        place(0);
        return solutions_;
    }

private:
    int n_, solutions_ = 0;
    std::vector<bool> cols_, diag_, anti_;

    void place(int row) {
        if (row == n_) {
            ++solutions_;
            return;
        }
        for (int c = 0; c < n_; ++c) {
            int d = row - c + n_, a = row + c;
            if (cols_[c] || diag_[d] || anti_[a]) continue;   // prune
            cols_[c] = diag_[d] = anti_[a] = true;
            place(row + 1);
            cols_[c] = diag_[d] = anti_[a] = false;           // undo
        }
    }
};

int main() {
    assert(NQueens(4).count() == 2);
    assert(NQueens(8).count() == 92);
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
The worst-case running time is the size of the state-space tree: O(2^n) for subsets, O(n!) for permutations and up to O(n^n) for placing n items with n options each, times the work per node. Pruning reduces the nodes actually visited, sometimes dramatically (8-Queens explores about two thousand nodes rather than millions of boards), but it does not change the exponential worst case in general. The extra space is O(depth) for the recursion stack and the current partial solution, plus whatever is needed to store the solutions found. Generating all solutions is inherently as large as the output, for example 2^n subsets.

## Common Mistakes & Misconceptions
The most common bug is forgetting to undo a choice after the recursive call, so later branches see stale state; a typical symptom is that the first solution is right and later ones are wrong or missing. Appending the shared list itself instead of a copy (result.append(current) instead of result.append(list(current))) makes every stored solution end up identical, usually empty. Missing base cases cause IndexError or infinite recursion. Students prune with a condition that is not actually safe, for example cutting when the sum exceeds the target even though negative numbers are allowed, and lose valid answers. Generating duplicates when the input has repeated values requires skipping equal choices at the same level. Another misconception is that backtracking is efficient in general; it is still exponential, and memoization or dynamic programming is needed when subproblems repeat.

## Builds On
This concept builds on Recursion. Each level of the search is one recursive call that makes one choice and delegates the rest of the problem to a smaller call, the base case is a complete solution, and the call stack automatically remembers the partial solution so that returning from a call is exactly the "go back" step. Understanding how local variables and shared state behave across recursive calls is essential to undoing choices correctly.

## Leads To
Backtracking is the natural algorithm for many NP-complete problems, which leads to P, NP & NP-Completeness and the question of why no fast algorithm is known for them. It is also the basis of branch and bound, constraint solvers for Sudoku and scheduling, SAT solvers, regular-expression matching engines and game-tree search, and memoized backtracking is one route into dynamic programming.

## Check Yourself
**Q1.** What are the three steps applied to each choice in backtracking?
**A1.** Apply the choice, recurse to solve the rest, then undo the choice.
**Q2.** What does pruning do?
**A2.** It abandons a partial solution as soon as it cannot lead to a valid answer, so its whole subtree is skipped.
**Q3.** How many solutions does 4-Queens have?
**A3.** Two, which are mirror images of each other.
