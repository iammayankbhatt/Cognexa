---
id: recursion
name: "Recursion"
cluster: foundations
reviewed: false
sources:
  - "CLRS, Section 2.3 (Designing algorithms: divide and conquer) and Chapter 4"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (Recursion)"
---

## Overview
Recursion solves a problem by solving smaller copies of the same problem. A recursive function calls itself on a simpler input, and a base case handles the smallest input directly so the chain of calls stops. Many problems with a naturally nested structure, such as trees, nested lists, divide-and-conquer sorting and exploring all choices, are easiest to express recursively.

## Intuition
Look at two mirrors facing each other: each reflection contains a smaller reflection of the same scene, until it becomes too small to see. Or imagine asking how many people are in a queue. You cannot see the whole line, so you ask the person ahead of you "how many people are in front of you?", then add one when they answer. They ask the person ahead of them in turn. The person at the front answers "zero" without asking anyone, and that is the base case. The answers then flow back down the line.

## How It Works
Every correct recursive function has two parts. The base case returns an answer directly for the smallest inputs, such as `n == 0` or an empty list. The recursive case reduces the input toward the base case and combines the result of the smaller call with a little extra work. If the input never gets closer to the base case, or the base case is missing, the recursion never stops.

To trust a recursive function, assume the recursive call returns the right answer for the smaller input (this is the leap of faith of induction) and check that the base case is right and the combination step is right. This mirrors a proof by induction.

Each call is a real function call with its own frame on the call stack, so a recursion of depth d uses d frames. Python caps the depth at about a thousand by default and raises `RecursionError: maximum recursion depth exceeded`. A recursive function can be rewritten with a loop and an explicit stack, which avoids the limit.

Some recursions branch: Fibonacci calls itself twice, so the number of calls grows exponentially and the same subproblems are recomputed again and again, which dynamic programming later fixes with caching. Tail-recursive functions do their work before the recursive call, but Python and most C++ compilers do not guarantee removing the extra frames.

## Worked Example
Compute factorial(4) where factorial(n) = n times factorial(n - 1) and factorial(0) = 1.

factorial(4) waits for factorial(3), which waits for factorial(2), which waits for factorial(1), which waits for factorial(0). The base case returns 1. Then factorial(1) returns 1 times 1 = 1, factorial(2) returns 2 times 1 = 2, factorial(3) returns 3 times 2 = 6 and factorial(4) returns 4 times 6 = 24.

Now count the sum of a list [3, 1, 2] recursively: sum([3, 1, 2]) is 3 plus sum([1, 2]), which is 1 plus sum([2]), which is 2 plus sum([]). The empty list is the base case and gives 0, so the answer is 6.

## Code
```python
def factorial(n):
    if n == 0:                  # base case
        return 1
    return n * factorial(n - 1)  # smaller problem


def list_sum(values):
    if not values:              # base case: empty list
        return 0
    return values[0] + list_sum(values[1:])


def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)   # two calls: exponential growth


def countdown(n):               # missing or unreachable base case never ends
    return countdown(n - 1)


assert factorial(4) == 24 and factorial(0) == 1
assert list_sum([3, 1, 2]) == 6 and list_sum([]) == 0
assert [fib(i) for i in range(8)] == [0, 1, 1, 2, 3, 5, 8, 13]

try:
    countdown(5)
except RecursionError:
    pass
else:
    raise AssertionError("expected RecursionError for a missing base case")


def factorial_loop(n):          # the same computation without recursion
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


assert factorial_loop(10) == factorial(10)
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

long long factorial(int n) {
    if (n == 0) return 1;       // base case
    return n * factorial(n - 1);
}

int listSum(const std::vector<int>& v, std::size_t index = 0) {
    if (index == v.size()) return 0;  // base case: past the end
    return v[index] + listSum(v, index + 1);
}

int fib(int n) {
    if (n < 2) return n;
    return fib(n - 1) + fib(n - 2);  // two calls: exponential growth
}

int main() {
    assert(factorial(4) == 24 && factorial(0) == 1);
    assert(listSum({3, 1, 2}) == 6 && listSum({}) == 0);
    int expected[8] = {0, 1, 1, 2, 3, 5, 8, 13};
    for (int i = 0; i < 8; ++i) assert(fib(i) == expected[i]);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
The cost of a recursive function is found by counting calls and the work per call. Factorial makes n calls with constant work each, so it takes O(n) time and O(n) stack space because the depth is n. The recursive list sum above takes O(n squared) time in Python because slicing copies the list on each call, even though the number of calls is n. The naive Fibonacci makes about 1.6 to the power n calls, so it takes exponential time but only O(n) space for the stack depth. A recursion that halves its input each call, as in binary search, takes O(log n) calls and O(log n) stack space.

## Common Mistakes & Misconceptions
The best-known symptom is `RecursionError: maximum recursion depth exceeded` in Python or a stack overflow crash elsewhere, usually caused by a missing base case or one that is never reached, for example calling `f(n + 1)` instead of `f(n - 1)`. Another symptom is a recursive function that is correct but takes forever, such as naive Fibonacci for n around 40, because the same subproblems are solved repeatedly. Students often forget to return the recursive call's result and get None. Some believe recursion is always slower or always better than loops; in fact the two are equally powerful and the choice depends on clarity, depth and cost. Finally, people try to trace every level mentally instead of trusting the induction step, which makes recursion feel harder than it is.

## Builds On
This concept builds on Function Calls & the Call Stack: every recursive call pushes a frame, which is why the depth is limited and why the unwinding order matters. Understanding that each call has its own parameters and locals, and that returns happen last in, first out, is what makes recursive traces make sense and explains the RecursionError that a missing base case produces.

## Leads To
Backtracking explores choices recursively and undoes them on return. Divide and conquer splits a problem into recursive subproblems, as in merge sort, and tree traversals visit a tree recursively. Recurrence relations describe the running time of recursive algorithms, and dynamic programming optimises recursions that repeat subproblems.

## Check Yourself
**Q1.** What are the two essential parts of a recursive function?
**A1.** A base case that stops the recursion and a recursive case that moves toward the base case.
**Q2.** What happens if a recursive function has no reachable base case?
**A2.** It keeps calling itself until the call stack is exhausted, causing a RecursionError or stack overflow.
**Q3.** Why is naive recursive Fibonacci slow?
**A3.** It recomputes the same smaller values many times, so the number of calls grows exponentially.
