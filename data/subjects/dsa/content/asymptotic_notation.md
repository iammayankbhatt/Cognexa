---
id: asymptotic_notation
name: "Asymptotic Notation (O, Θ, Ω; best/avg/worst)"
cluster: complexity
reviewed: false
sources:
  - "CLRS, Section 3.2 (Asymptotic notation)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.4 (Order-of-growth classifications)"
---

## Overview
Asymptotic notation gives precise meaning to the informal idea that an algorithm "grows like n squared". Big-O gives an upper bound on growth, Omega gives a lower bound, and Theta says the growth is pinned down from both sides. These bounds describe behaviour for large inputs and ignore constant factors. Alongside them, we distinguish three scenarios for the same algorithm: the best case, the average case and the worst case, which are different functions of n. Mixing up bounds with cases is one of the most common sources of confusion.

## Intuition
Suppose you tell a friend how long your commute takes. "Never more than an hour" is an upper bound, like Big-O. "At least twenty minutes, even with no traffic" is a lower bound, like Omega. "Between 25 and 35 minutes on a typical day" is a tight description, like Theta. Separately, you can talk about the best day (empty roads), the average day and the worst day (an accident). The bound type and the scenario are two independent choices.

## How It Works
Formally, f(n) is O(g(n)) if there are positive constants c and n0 such that f(n) is at most c times g(n) for every n at least n0. In words: beyond some starting point, f stays under a constant multiple of g. For example 3n squared + 5n is O(n squared): choose c = 4 and n0 = 5, because 3n squared + 5n is at most 4n squared whenever 5n is at most n squared, which holds for n at least 5.

f(n) is Omega(g(n)) if f(n) is at least c times g(n) for all large n, so g is a lower bound. f(n) is Theta(g(n)) if it is both O(g(n)) and Omega(g(n)): g bounds f from above and below up to constants. A Theta statement is the most informative, and 3n squared + 5n is Theta(n squared).

Bounds describe functions, while cases describe inputs. For linear search on n items: the best case finds the target at index 0 with 1 comparison, the worst case needs n comparisons, and averaging over positions gives about n/2. We can say the worst-case running time is Theta(n), the best case is Theta(1), and the algorithm as a whole is O(n) and Omega(1). Saying "the best case is O(1)" and "the algorithm is O(n)" are both valid and do not contradict each other.

Some rules help. Constants disappear, so Theta(5n) is Theta(n). Sums keep the larger term, so O(n) + O(n squared) is O(n squared). Products multiply, so O(n) times O(log n) is O(n log n). Logarithm bases differ only by a constant factor, so Theta(log2 n) equals Theta(log10 n). Polynomials are dominated by their highest power and exponentials beat polynomials. Little-o and little-omega are strict versions but are rarely needed.

## Worked Example
Show that 2n squared + 10n is Theta(n squared).

Upper bound: for n at least 10, 10n is at most n squared, so 2n squared + 10n is at most 3n squared. So it is O(n squared) with c = 3 and n0 = 10.

Lower bound: 2n squared + 10n is at least 2n squared for all n at least 1, so it is Omega(n squared) with c = 2 and n0 = 1.

Both hold, so 2n squared + 10n is Theta(n squared). Now insertion sort: on an already sorted array it does about n comparisons, so its best case is Theta(n); on a reverse-sorted array it does about n squared over two, so its worst case is Theta(n squared). The algorithm is therefore O(n squared) overall and Omega(n).

## Code
The code searches for witnesses (c and n0) and measures best and worst cases of linear search.

```python
def f(n):
    return 3 * n * n + 5 * n


# O(n^2): f(n) <= 4 n^2 for all n >= 5, so c = 4 and n0 = 5 are witnesses.
assert all(f(n) <= 4 * n * n for n in range(5, 2000))
# The same constant fails for small n, which is why n0 matters.
assert f(1) > 4 * 1 * 1

# Omega(n^2): f(n) >= 3 n^2 for all n >= 1.
assert all(f(n) >= 3 * n * n for n in range(1, 2000))


def linear_search_comparisons(values, target):
    comparisons = 0
    for v in values:
        comparisons += 1
        if v == target:
            break
    return comparisons


data = list(range(100))
assert linear_search_comparisons(data, 0) == 1            # best case: Theta(1)
assert linear_search_comparisons(data, 99) == 100         # worst case: Theta(n)
assert linear_search_comparisons(data, -1) == 100         # missing target is also worst case
average = sum(linear_search_comparisons(data, t) for t in data) / len(data)
assert average == 50.5                                     # about n / 2
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

long long f(long long n) { return 3 * n * n + 5 * n; }

int linearSearchComparisons(const std::vector<int>& v, int target) {
    int comparisons = 0;
    for (int x : v) {
        ++comparisons;
        if (x == target) break;
    }
    return comparisons;
}

int main() {
    for (long long n = 5; n < 2000; ++n) {
        assert(f(n) <= 4 * n * n);  // O(n^2) with c = 4, n0 = 5
        assert(f(n) >= 3 * n * n);  // Omega(n^2) with c = 3
    }
    assert(f(1) > 4 * 1 * 1);       // the constant fails below n0

    std::vector<int> data;
    for (int i = 0; i < 100; ++i) data.push_back(i);
    assert(linearSearchComparisons(data, 0) == 1);     // best case
    assert(linearSearchComparisons(data, 99) == 100);  // worst case
    assert(linearSearchComparisons(data, -1) == 100);  // absent target

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
The notation itself has no running time, but each symbol answers a different question about an algorithm's cost function T(n). Big-O answers "how bad can it get at most", Omega answers "how good can it be at best, at minimum", and Theta answers "what is the exact growth rate". For common algorithms: linear search is O(n) worst case and O(1) best case; binary search is Theta(log n) in the worst case; insertion sort is Theta(n) best and Theta(n squared) worst; merge sort is Theta(n log n) in every case. The space needed to state a Theta bound is nothing, but proving one needs both an upper and a lower argument.

## Common Mistakes & Misconceptions
A very common mistake is equating Big-O with the worst case and Omega with the best case. They are bounds on functions, so each case has its own O, Omega and Theta. Another is claiming "O(n squared) means exactly quadratic": O is only an upper bound, so a linear algorithm is also technically O(n squared), although saying so is unhelpful. Students write "the algorithm is Theta(n)" when only the worst case is linear, or add constants and lower terms inside the notation. They also forget that the definition needs a threshold n0, and that "for large enough n" is part of the claim. Finally, comparing the average case against another algorithm's worst case, or mixing log bases as if they mattered, produces misleading conclusions.

## Builds On
This concept builds on Time Complexity & Big-O: it formalises the informal rules there, such as dropping constants and keeping the dominant term, and gives the exact definition behind the Big-O symbol you already used. The skill of counting steps as a function of n from that concept is the raw material to which the O, Omega and Theta definitions are then applied.

## Leads To
Recurrence relations and the Master Theorem produce Theta bounds for recursive algorithms. Amortized analysis refines worst-case bounds across sequences of operations, and the comparison-sorting lower bound is an Omega statement about every possible comparison sort.

## Check Yourself
**Q1.** Is Big-O the same thing as the worst case?
**A1.** No. Big-O is an upper bound on a growth function; the worst case is a scenario, and each scenario can have its own O, Omega and Theta.
**Q2.** What are the best and worst case comparisons for linear search on n items?
**A2.** The best case is 1 comparison and the worst case is n comparisons.
**Q3.** Is 3n + 7 in Theta(n)?
**A3.** Yes: it is at most 4n for n at least 7 and at least 3n for all n, so it is bounded above and below by multiples of n.
