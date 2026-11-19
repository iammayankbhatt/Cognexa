---
id: time_complexity
name: "Time Complexity & Big-O"
cluster: complexity
reviewed: false
sources:
  - "CLRS, Chapter 3 (Characterizing Running Times) and Section 2.2 (Analyzing algorithms)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.4 (Analysis of Algorithms)"
---

## Overview
Time complexity describes how the running time of an algorithm grows as its input gets bigger. Instead of measuring seconds, which depend on the machine, we count basic steps as a function of the input size n and keep only the dominant term. Big-O notation writes this growth compactly: an algorithm that does about 3n + 10 steps is O(n), and one that does about n squared over two steps is O(n squared). It lets you compare algorithms and predict whether one will still be fast when the input is a thousand times larger.

## Intuition
Think about finding a name in a printed phone book. Reading every page from the start takes time proportional to the number of pages: double the book, double the time. Opening the book in the middle and discarding half each time needs only a handful of steps even for a huge book. Both methods work, but one scales far better. Big-O captures exactly that difference in scaling, ignoring details like how fast you turn pages.

## How It Works
First choose what to count, usually the number of basic operations such as comparisons or assignments, and express it in terms of the input size n. Then simplify: drop constant factors and lower-order terms, because for large n they matter little. So 5n squared + 20n + 7 simplifies to O(n squared).

The common growth classes, from slowest-growing to fastest, are constant O(1), logarithmic O(log n), linear O(n), linearithmic O(n log n), quadratic O(n squared), cubic O(n cubed), exponential O(2 to the power n) and factorial O(n!). A single loop over n items is O(n). Two nested loops over n items are O(n squared). A loop that halves its counter each pass is O(log n). Consecutive blocks of code add, so the slower one dominates; nested blocks multiply.

A simple recipe to analyse code: look at each loop, find how many times it runs in terms of n, multiply for nesting, add for sequences, and keep the largest term. Function calls cost whatever their own bodies cost, and recursion needs a recurrence to count calls, which is a later topic.

Big-O usually describes the worst case unless stated otherwise: the largest number of steps over all inputs of size n. Sometimes the best case and the average case are also given.

Why growth matters: with n equal to one million, an O(n) algorithm does about a million steps, an O(n log n) one about twenty million, and an O(n squared) one about a trillion, which is hours rather than milliseconds. Constants matter in practice for small n but never rescue a worse growth class for large n.

## Worked Example
Analyse this function that counts pairs of equal elements:

```
count = 0
for i in range(n):
    for j in range(i + 1, n):
        if a[i] == a[j]:
            count += 1
```

The outer loop runs n times. For a given i the inner loop runs n minus i minus 1 times. The total number of comparisons is (n-1) + (n-2) + ... + 1 + 0, which equals n(n-1)/2. That is about n squared over two, so the algorithm is O(n squared). If n doubles from 1,000 to 2,000, the comparisons grow from about 500,000 to about 2,000,000, four times as many.

## Code
The programs below count the actual number of steps taken by three loop shapes and check the growth formulas.

```python
import math


def linear_steps(n):
    steps = 0
    for _ in range(n):
        steps += 1
    return steps


def quadratic_steps(n):
    steps = 0
    for _ in range(n):
        for _ in range(n):
            steps += 1
    return steps


def logarithmic_steps(n):
    steps = 0
    while n > 1:
        n //= 2
        steps += 1
    return steps


def pair_comparisons(n):
    steps = 0
    for i in range(n):
        for j in range(i + 1, n):
            steps += 1
    return steps


assert linear_steps(1000) == 1000
assert quadratic_steps(100) == 10000
assert logarithmic_steps(1024) == 10 == int(math.log2(1024))
assert pair_comparisons(1000) == 1000 * 999 // 2

# Doubling n: linear doubles, quadratic quadruples, logarithmic adds one step.
assert linear_steps(2000) == 2 * linear_steps(1000)
assert quadratic_steps(200) == 4 * quadratic_steps(100)
assert logarithmic_steps(2048) == logarithmic_steps(1024) + 1
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>

long long linearSteps(int n) {
    long long steps = 0;
    for (int i = 0; i < n; ++i) ++steps;
    return steps;
}

long long quadraticSteps(int n) {
    long long steps = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j) ++steps;
    return steps;
}

int logarithmicSteps(long long n) {
    int steps = 0;
    while (n > 1) {
        n /= 2;
        ++steps;
    }
    return steps;
}

int main() {
    assert(linearSteps(1000) == 1000);
    assert(quadraticSteps(100) == 10000);
    assert(logarithmicSteps(1024) == 10);
    assert(linearSteps(2000) == 2 * linearSteps(1000));
    assert(quadraticSteps(200) == 4 * quadraticSteps(100));
    assert(logarithmicSteps(2048) == logarithmicSteps(1024) + 1);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
This section describes the common classes themselves. O(1) means the work does not depend on n, like reading an array element. O(log n) halves the problem each step, like binary search. O(n) touches each item once, like linear search. O(n log n) is the cost of efficient sorting. O(n squared) arises from comparing all pairs, as in the simple sorts. O(2 to the power n) arises from trying all subsets. The space the analysis itself needs is O(1), because it only reasons about counts. In practice, an algorithm with a few million simple steps runs in well under a second, while 10 to the power 9 steps takes on the order of seconds and 10 to the power 12 takes hours.

## Common Mistakes & Misconceptions
A typical symptom is a program that passes small tests but gets "Time Limit Exceeded" on large input: the algorithm's growth class is too high, for example a quadratic solution for n = 100,000. Students often count every instruction instead of the growth, or keep constants and lower-order terms in Big-O. They also assume that two nested loops are always quadratic even when the inner loop runs a fixed number of times, or that the faster-looking code on a small test must scale better. Another misconception is that O(n) always beats O(n squared); for small n the constant factors can reverse that, and Big-O says nothing about exact speed. Finally, people confuse Big-O with the worst case: it is an upper bound on growth, and any case (best, average, worst) can be described with it.

## Builds On
This concept builds on Conditionals & Loops, because running time is determined by how many times loops execute and how they nest; to count steps you must be able to read a loop's bounds and a loop's update rule. It also builds on Discrete Math Basics, which supplies the tools used to count: summations such as 1 + 2 + ... + n for nested loops and logarithms for loops that halve their counter.

## Leads To
Asymptotic notation makes the informal rules here precise with O, Theta and Omega and with best, average and worst cases. Space complexity applies the same idea to memory, recurrence relations count the time of recursive algorithms, and every later algorithm in this course is judged by its time complexity.

## Check Yourself
**Q1.** What is the time complexity of a loop that does a constant amount of work and runs n times?
**A1.** O(n), linear time.
**Q2.** Simplify 7n squared + 30n + 12 to Big-O form.
**A2.** O(n squared), dropping the constant factor and lower-order terms.
**Q3.** If an O(n squared) algorithm takes 1 second for n = 1,000, roughly how long for n = 2,000?
**A3.** About 4 seconds, because doubling n quadruples the work.
