---
id: monotonic_stack
name: "Monotonic Stack"
cluster: linear
reviewed: false
sources:
  - "Competitive Programmer's Handbook (Laaksonen), Section 8.2 (Nearest smaller values)"
  - "CLRS, Chapter 10 (stacks) with the classic 'next greater element' and 'largest rectangle in a histogram' exercises"
---

## Overview
A monotonic stack is an ordinary stack that is kept in sorted order: either every item is larger than the one beneath it (a decreasing stack from bottom to top) or smaller (an increasing stack). Before pushing a new item, you pop all the items that would break the order. This small trick answers a whole family of questions, such as "for each element, where is the next greater element?" or "what is the largest rectangle in this histogram?", in a single pass of linear time instead of the quadratic time of comparing every pair.

## Intuition
Imagine people of different heights standing in a line looking to the right, and each person wants to know who is the first taller person to their right. Walk along the line holding a list of people still waiting for an answer. When a new person arrives who is taller than the waiting ones at the end of the list, those people have just found their answer, so you remove them. Everyone who stays waiting is taller than all the waiters after them, so the list is always ordered by height: that is the monotonic stack.

## How It Works
To find the next greater element for every position in an array, scan left to right keeping a stack of indexes whose answer is not yet known. The values at those indexes are in decreasing order from bottom to top. For each new index i with value v: while the stack is not empty and the value at the top index is smaller than v, pop that index and record v as its next greater element, then push i. When the scan ends, any indexes still on the stack have no greater element to their right.

Why is this linear? Each index is pushed once and popped at most once, so the total work over the whole scan is at most 2n stack operations, even though the while loop sits inside the for loop. Looking only at the loop nesting would suggest n squared; counting pushes and pops (an amortized argument) gives n.

Variations change the comparison or the direction. For the next smaller element, keep an increasing stack. For the previous greater or smaller element, read the stack's top before pushing, because the top is the nearest remaining candidate on the left. Equal values need a clear rule (pop on less-or-equal or only on less) and the choice depends on whether "greater" means strictly greater.

The largest rectangle in a histogram uses an increasing stack of bar indexes. When a bar shorter than the top arrives, the top bar cannot extend any further right, so pop it and compute the width that it could cover, using the new top as the left boundary. A sentinel bar of height zero at the end flushes the stack.

Another common use is the stock span: for each day, how many consecutive previous days had a price less than or equal to today's, solved with a stack of previous days that were higher.

## Worked Example
Find the next greater element for [2, 1, 2, 4, 3].

Scan with a stack of indexes. i = 0 (value 2): stack empty, push 0. i = 1 (value 1): top value 2 is not smaller, push 1: stack [0, 1]. i = 2 (value 2): the top value 1 is smaller, so pop index 1 and answer[1] = 2; the next top value 2 is not smaller than 2, push 2: stack [0, 2]. i = 3 (value 4): top value 2 smaller, pop index 2 and answer[2] = 4; top value 2 (index 0) smaller, pop and answer[0] = 4; push 3: stack [3]. i = 4 (value 3): top value 4 is not smaller, push 4: stack [3, 4]. The scan ends and indexes 3 and 4 have no greater element, so their answers are -1. Result: [4, 2, 4, -1, -1].

## Code
```python
def next_greater(values):
    answer = [-1] * len(values)
    stack = []                                   # indexes; their values decrease toward the top
    for i, v in enumerate(values):
        while stack and values[stack[-1]] < v:
            answer[stack.pop()] = v              # v is the next greater element of the popped index
        stack.append(i)
    return answer


def previous_smaller(values):
    answer = [-1] * len(values)
    stack = []                                   # values increase toward the top
    for i, v in enumerate(values):
        while stack and values[stack[-1]] >= v:
            stack.pop()
        if stack:
            answer[i] = values[stack[-1]]        # nearest smaller value to the left
        stack.append(i)
    return answer


def largest_rectangle(heights):
    best, stack = 0, []                          # stack of indexes with increasing heights
    for i, h in enumerate(heights + [0]):        # a zero-height sentinel flushes the stack
        while stack and heights[stack[-1]] >= h:
            height = heights[stack.pop()]
            left = stack[-1] if stack else -1
            best = max(best, height * (i - left - 1))
        stack.append(i)
    return best


assert next_greater([2, 1, 2, 4, 3]) == [4, 2, 4, -1, -1]
assert next_greater([]) == []
assert next_greater([5, 4, 3]) == [-1, -1, -1]
assert previous_smaller([3, 1, 4, 2]) == [-1, -1, 1, 1]
assert largest_rectangle([2, 1, 5, 6, 2, 3]) == 10
assert largest_rectangle([2, 4]) == 4
assert largest_rectangle([]) == 0

# Compare with the quadratic brute force on a larger input.
import random

random.seed(1)
data = [random.randint(0, 20) for _ in range(300)]
brute = []
for i, v in enumerate(data):
    brute.append(next((w for w in data[i + 1:] if w > v), -1))
assert next_greater(data) == brute
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <stack>
#include <vector>

std::vector<int> nextGreater(const std::vector<int>& v) {
    std::vector<int> answer(v.size(), -1);
    std::stack<std::size_t> st;  // indexes; values decrease toward the top
    for (std::size_t i = 0; i < v.size(); ++i) {
        while (!st.empty() && v[st.top()] < v[i]) {
            answer[st.top()] = v[i];
            st.pop();
        }
        st.push(i);
    }
    return answer;
}

int largestRectangle(std::vector<int> heights) {
    heights.push_back(0);  // sentinel flushes the stack
    int best = 0;
    std::stack<int> st;
    for (int i = 0; i < static_cast<int>(heights.size()); ++i) {
        while (!st.empty() && heights[st.top()] >= heights[i]) {
            int height = heights[st.top()];
            st.pop();
            int left = st.empty() ? -1 : st.top();
            best = std::max(best, height * (i - left - 1));
        }
        st.push(i);
    }
    return best;
}

int main() {
    assert((nextGreater({2, 1, 2, 4, 3}) == std::vector<int>{4, 2, 4, -1, -1}));
    assert((nextGreater({5, 4, 3}) == std::vector<int>{-1, -1, -1}));
    assert(largestRectangle({2, 1, 5, 6, 2, 3}) == 10);
    assert(largestRectangle({2, 4}) == 4);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Each index is pushed once and popped at most once, so a full scan performs at most 2n stack operations: O(n) time even though a while loop is nested inside a for loop. The stack holds at most n indexes, so the extra space is O(n), for example for a strictly decreasing input in the next-greater problem. The brute-force alternative compares every element with all later elements and takes O(n squared) time, which is too slow once n reaches around 100,000. Largest rectangle in a histogram also runs in O(n) with this method, versus O(n squared) for trying every pair of left and right boundaries.

## Common Mistakes & Misconceptions
A frequent symptom is "Time Limit Exceeded" from a nested-loop solution to a next-greater or span problem when a linear stack solution was possible. Another is believing the stack solution is quadratic because of the inner while loop; the amortized count of pops shows it is linear. Students push values instead of indexes and then cannot write the answer back to the right position or compute widths. Equal values cause subtle errors: popping on greater-or-equal versus strictly-greater changes which neighbour is found, so the rule must match the problem statement. Forgetting the final flush, either with a sentinel bar or a cleanup loop, loses rectangles that extend to the end of the histogram. Finally, mixing up the stack's ordering (increasing versus decreasing) for next-greater versus next-smaller leads to wrong answers.

## Builds On
This concept builds on Stack (ADT & implementations): it uses nothing but push, pop and peek, and the monotonic part is only a discipline about what may be pushed. Knowing that a stack removes the most recently added item first explains why the candidates waiting at the top are always the ones that get answered first, and that the stack naturally keeps the most recent unresolved items.

## Leads To
The sliding window technique has a closely related variant that uses a monotonic deque for window maxima. Many problems on histograms, temperatures, stock prices and bracket-like structures reduce to monotonic stacks, and the idea reappears in dynamic programming optimisations and in computing nearest-neighbour relations on trees.

## Check Yourself
**Q1.** In the next greater element scan, what is popped when a new value v arrives?
**A1.** Every index at the top whose value is smaller than v; v is their next greater element.
**Q2.** Why is the algorithm O(n) despite the while loop inside the for loop?
**A2.** Each index is pushed once and popped at most once, so there are at most 2n stack operations.
**Q3.** What does the stack contain at any moment?
**A3.** The indexes whose answer is still unknown, with their values in sorted (monotonic) order.
