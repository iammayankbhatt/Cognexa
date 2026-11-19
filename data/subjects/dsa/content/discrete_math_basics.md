---
id: discrete_math_basics
name: "Discrete Math Basics (logs, sums, modular arithmetic)"
cluster: foundations
reviewed: false
sources:
  - "CLRS, Appendix A (Summations) and Section 3.2 (Standard notations and common functions)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.4 (Analysis of Algorithms)"
---

## Overview
Almost every statement about how fast an algorithm runs is written in the language of a few small mathematical tools. Logarithms tell you how many times a quantity can be halved. Summations add up the cost of a loop that runs many times. Powers of two describe how data doubles, and modular arithmetic describes wrapping around, such as an index that returns to zero at the end of a circular buffer. None of this is advanced, but you need to feel comfortable with it before running times make sense.

## Intuition
Imagine a phone book with one thousand names. If you open it in the middle, discard the half that cannot contain your name, and repeat, you need only about ten steps, because one thousand halved ten times is roughly one. That "how many halvings" count is the logarithm. Now imagine climbing a staircase where you do one unit of work on the first step, two on the second, and so on up to n. The total effort is a sum, and knowing a formula for it saves you from adding step by step. Finally, think of a clock: after 12 comes 1 again. That wrap-around is modular arithmetic, and the clock's 12 is the modulus.

## How It Works
A logarithm answers the question "to what power must the base be raised to get this number?". In computer science the base is almost always 2, so log2(n) is the number of times n can be divided by two before it reaches 1. Doubling and halving are inverse operations, which is why binary search and balanced trees run in logarithmic time.

A summation adds a sequence of terms. Two closed forms appear constantly. The arithmetic series 1 + 2 + ... + n equals n(n+1)/2, which grows like n squared. The geometric series 1 + 2 + 4 + ... + 2^(k-1) equals 2^k - 1, so the last term is about as large as everything before it combined. This second fact explains why doubling a dynamic array is cheap on average.

Modular arithmetic keeps only the remainder after division. The expression a mod m gives a value from 0 to m-1. Adding or multiplying before or after taking the remainder gives the same result, which is why hash functions can reduce large numbers to table positions safely. Be aware that languages differ on negative numbers: Python returns a non-negative result for a positive modulus, while C++ gives a result with the same sign as the dividend.

Floors and ceilings round down and up. They matter whenever a quantity is not exactly divisible, for example the number of halvings needed for 1000 is the floor of log2(1000), which is 9.

## Worked Example
How many comparisons does it take to find a name among 1,000,000 sorted names using repeated halving?

Start with n = 1,000,000. After 1 halving: 500,000. After 2: 250,000. Continue: 125,000, 62,500, 31,250, 15,625, 7,812, 3,906, 1,953, 976, 488, 244, 122, 61, 30, 15, 7, 3, 1. That is 19 halvings, matching the floor of log2(1,000,000), which is about 19.93. Allowing one final check on the last remaining name, about 20 comparisons are enough.

Compare that with the sum of a nested loop where the inner loop runs i times for i from 1 to n. The total work is 1 + 2 + ... + n = n(n+1)/2. For n = 1,000 that is 500,500 steps, which is why such a loop is called quadratic.

## Code
The Python and C++ programs below check each idea with assertions, so they only print when every claim holds.

```python
import math

# Logarithm: how many times can n be halved before reaching 1?
def halvings(n):
    steps = 0
    while n > 1:
        n //= 2
        steps += 1
    return steps

assert halvings(1024) == 10 == int(math.log2(1024))
assert halvings(1000) == 9 == math.floor(math.log2(1000))

# Arithmetic series: 1 + 2 + ... + n = n(n+1)/2
n = 100
assert sum(range(1, n + 1)) == n * (n + 1) // 2

# Geometric series: 1 + 2 + 4 + ... + 2^(k-1) = 2^k - 1
k = 10
assert sum(2 ** i for i in range(k)) == 2 ** k - 1

# Modular arithmetic: wrap an index around a circular buffer of size 8
size = 8
assert (5 + 6) % size == 3
assert (-1) % size == 7  # Python never returns a negative result for a positive modulus
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>

// Number of times n can be halved before it reaches 1 (floor of log2 n).
int halvings(long long n) {
    int steps = 0;
    while (n > 1) {
        n /= 2;
        ++steps;
    }
    return steps;
}

int main() {
    assert(halvings(1024) == 10);
    assert(halvings(1000) == 9);

    long long n = 100, total = 0;
    for (long long i = 1; i <= n; ++i) total += i;
    assert(total == n * (n + 1) / 2);  // arithmetic series

    int size = 8;
    assert((5 + 6) % size == 3);
    // In C++ the sign of % follows the dividend, so wrap negatives explicitly.
    assert((((-1) % size) + size) % size == 7);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
These tools are not algorithms, so they have no running time of their own, but they set the scale for everything else. Computing a logarithm by repeated halving takes O(log n) steps. Summing n numbers one by one takes O(n) time, while the closed form n(n+1)/2 takes O(1). A remainder operation is constant time. The key facts to remember are that logarithmic growth is extremely slow (a billion items need only about 30 halvings), that the arithmetic series grows quadratically, and that the geometric series is dominated by its largest term.

## Common Mistakes & Misconceptions
Students often write log n and mean "n divided by something", or forget that the base is 2 in computer science. Another frequent slip is an off-by-one in a sum: the series from 1 to n has n terms, but from 0 to n it has n+1 terms. Reasoning that the arithmetic series is "about n" instead of about n squared over two leads to wildly wrong running times. With remainders, a negative result such as -1 % 8 giving -1 in C++ or Java surprises people who learned the clock-like behaviour in Python. Finally, confusing log2 of n with the number of bits of n is close but not identical: the number of bits is the floor of log2 n plus one.

## Builds On
This is a foundation concept with no prerequisites in the graph. It assumes only school arithmetic: powers, division with remainder and reading a summation sign.

## Leads To
Time complexity and Big-O rely directly on logarithms and sums to describe how running time grows. Hash functions depend on modular arithmetic to map keys to table positions, and later topics such as binary search, balanced trees and amortized analysis all use the halving and doubling facts introduced here.

## Check Yourself
**Q1.** About how many times can 1,000,000,000 be halved before reaching 1?
**A1.** About 30, because 2 to the power 30 is roughly one billion.
**Q2.** What is 1 + 2 + 3 + ... + 50?
**A2.** 50 * 51 / 2 = 1275.
**Q3.** What is 17 mod 5, and what does it mean for a circular buffer of size 5?
**A3.** 17 mod 5 = 2, so position 17 wraps around to slot 2.
