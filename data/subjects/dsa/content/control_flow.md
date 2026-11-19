---
id: control_flow
name: "Conditionals & Loops"
cluster: foundations
reviewed: false
sources:
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (conditionals and loops)"
  - "CLRS, Section 2.1 (Insertion sort, loop invariants)"
---

## Overview
Control flow decides which statements run and how many times. Conditionals (if, else if, else) choose between paths based on a test. Loops (for and while) repeat work until a condition fails. Together they turn a fixed list of statements into a program that can react to input and process data of any size. Nearly every algorithm in this course is a carefully arranged combination of the two.

## Intuition
A conditional is a fork in the road with a sign: if the sign says the bridge is open, take the bridge, otherwise take the ferry. A loop is a washing machine cycle: keep rinsing until the water runs clear. The two dangers are the same in real life and in code. A loop whose "water never runs clear" condition never becomes true runs forever, and a loop that stops one rinse too early or too late has an off-by-one error.

## How It Works
An if statement evaluates a boolean expression. If it is true the indented block runs, otherwise the else block (if present) runs. Conditions are checked from top to bottom and only the first matching branch executes. Boolean operators and, or and not combine tests, and they short-circuit: in `a and b`, b is only evaluated when a is true.

A while loop checks its condition before every iteration. If the condition is false at the start, the body never runs. A for loop iterates over a sequence or a counted range. In Python `range(a, b)` yields a, a+1, ..., b-1, so the upper bound is excluded. The statement `break` leaves the nearest loop immediately and `continue` skips the rest of the current iteration.

To reason about a loop, find its invariant: a fact that is true before the loop starts and after every iteration. For a loop that sums 1 to n, the invariant "total equals the sum of 1 to i minus 1" holds at the top of each pass, and when the loop ends the invariant gives the answer. Termination needs a quantity that moves toward the stopping condition every iteration, such as a counter that only increases toward n.

Nested loops multiply: if the outer loop runs n times and the inner loop runs m times for each pass, the body runs n times m.

## Worked Example
Find the index of the first negative number in [3, 1, -2, 5].

Start i = 0. The value 3 is not negative, so continue. i = 1: value 1 is not negative. i = 2: value -2 is negative, so return 2 immediately. The loop never looks at 5, which shows how an early exit saves work. If the list had no negative numbers the loop would finish all iterations and return -1 to signal "not found".

For nested loops, count the passes of `for i in range(3): for j in range(i): count += 1`. For i = 0 the inner loop runs 0 times, for i = 1 once, for i = 2 twice, so count becomes 3, the sum 0 + 1 + 2.

## Code
```python
def sum_to(n):
    total = 0
    i = 1
    while i <= n:        # invariant: total == 1 + 2 + ... + (i - 1)
        total += i
        i += 1
    return total

assert sum_to(10) == 55 and sum_to(0) == 0

def first_negative(values):
    for i, v in enumerate(values):
        if v < 0:
            return i     # early exit
    return -1

assert first_negative([3, 1, -2, 5]) == 2
assert first_negative([1, 2]) == -1

# range(a, b) excludes b: a classic source of off-by-one errors
assert list(range(1, 4)) == [1, 2, 3]

count = 0
for i in range(3):
    for j in range(i):
        count += 1
assert count == 3

# continue skips the rest of one iteration
odds = []
for n in range(10):
    if n % 2 == 0:
        continue
    odds.append(n)
assert odds == [1, 3, 5, 7, 9]
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

int sumTo(int n) {
    int total = 0;
    int i = 1;
    while (i <= n) {  // invariant: total == 1 + 2 + ... + (i - 1)
        total += i;
        ++i;
    }
    return total;
}

int firstNegative(const std::vector<int>& values) {
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (values[i] < 0) return static_cast<int>(i);  // early exit
    }
    return -1;
}

int main() {
    assert(sumTo(10) == 55 && sumTo(0) == 0);
    assert(firstNegative({3, 1, -2, 5}) == 2);
    assert(firstNegative({1, 2}) == -1);

    int count = 0;
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < i; ++j) ++count;
    assert(count == 3);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
A single loop that runs n times does n units of work, so it is O(n). Two nested loops that both run n times do n times n work, O(n squared). A loop that halves its counter each pass, such as `while n > 1: n //= 2`, runs about log2 n times. The best case of a search loop with an early exit can be O(1), while the worst case still visits every element. Conditionals add only constant time per evaluation.

## Common Mistakes & Misconceptions
Typical symptoms are a program that hangs because the loop variable is never updated, or that prints one item too many or too few because of an off-by-one error in the bound, for example using `<=` where `<` was intended. Students also forget that `range` stops before the end value, write `=` instead of `==` in a condition, or place the update statement inside an else branch so it does not always run. In nested loops a break only leaves the inner loop. Finally, beginners sometimes believe that an if-elif chain runs every true branch, but only the first matching branch executes.

## Builds On
This concept builds on Variables, Data Types & Memory: loop counters and accumulators are variables whose values change each iteration, and conditions compare values whose types decide what the comparison means. Without the idea of a variable holding a changing value, loops have nothing to count.

## Leads To
Functions package loops and conditionals into reusable pieces, and arrays are almost always processed with loops. Time complexity analysis counts how often loop bodies run, so control flow is the raw material of Big-O reasoning.

## Check Yourself
**Q1.** What does `list(range(2, 6))` produce?
**A1.** [2, 3, 4, 5]; the upper bound 6 is excluded.
**Q2.** A while loop's condition is false the first time it is checked. How many times does the body run?
**A2.** Zero times.
**Q3.** What is a loop invariant used for?
**A3.** It is a fact true before and after every iteration; together with the stopping condition it proves the loop computes the right result.
