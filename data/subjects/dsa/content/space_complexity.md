---
id: space_complexity
name: "Space Complexity"
cluster: complexity
reviewed: false
sources:
  - "CLRS, Section 2.2 (Analyzing algorithms) and the discussion of in-place sorting in Chapter 2"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.4 (Memory)"
---

## Overview
Space complexity measures how much memory an algorithm needs as a function of its input size n. Like time complexity it is stated with Big-O and ignores constants. We usually count the extra, or auxiliary, space the algorithm allocates beyond the input itself, including the memory used by its recursion. An algorithm that needs only a constant amount of extra memory is called in place. Memory limits are real: a solution that is fast but needs a billion extra cells will crash a judge with a 256 MB limit.

## Intuition
Imagine sorting a deck of cards on a small desk. You could shuffle cards around within the deck, using only a free spot or two on the desk: that is in-place work with constant extra space. Or you could lay out a complete second copy of the deck and build the sorted order there: that needs space proportional to the deck. Both produce the same result, but they need very different amounts of desk. Recursion is a hidden desk cost too, because every pending call keeps a note of where it stopped.

## How It Works
Count three kinds of memory. The input itself is usually not charged to the algorithm. Auxiliary memory is every extra variable, array, hash table or copy the algorithm creates. Recursion adds the call stack: a recursion that goes d levels deep keeps d frames alive at once, so it uses O(d) stack space even if it allocates nothing else.

A few shapes appear again and again. Fixed numbers of variables are O(1). Creating a new array of size n, or a copy of the input, is O(n). A two-dimensional table with n rows and n columns is O(n squared). A recursion that makes one call per level and descends n levels uses O(n) stack space, while one that halves the problem each call, like binary search, uses O(log n).

There are often trade-offs between time and space. Caching previously computed answers in a table can turn an exponential-time computation into a linear one, but the table costs memory. Conversely, recomputing values uses less memory and more time. Choosing an in-place algorithm may make code more complicated or change stability and speed.

Python-specific notes: slicing a list creates a new list, so `values[1:]` costs O(n) space and time at each call, and building new strings or lists inside a loop can accidentally use more memory than expected. Generators produce items one at a time and use O(1) space, unlike building a full list.

## Worked Example
Reverse a list of n items in two ways.

Way one creates a new list by copying the items in reverse order. It allocates n new cells, so the auxiliary space is O(n).

Way two swaps the first and last items, then the second and the second to last, and so on, using one temporary variable. It reuses the input's own cells, so the auxiliary space is O(1): it is in place.

Now compute the sum of 1 to n recursively as `total(n) = n + total(n - 1)`. There are no arrays, but the recursion is n levels deep, so at its deepest it holds n frames: O(n) space. The same sum with a loop and one accumulator variable needs only O(1) space.

## Code
```python
import sys


def reversed_copy(values):
    return values[::-1]          # allocates a new list of n items: O(n) extra space


def reverse_in_place(values):
    left, right = 0, len(values) - 1
    while left < right:          # only a few variables: O(1) extra space
        values[left], values[right] = values[right], values[left]
        left += 1
        right -= 1


a = [1, 2, 3, 4, 5]
b = reversed_copy(a)
assert b == [5, 4, 3, 2, 1] and a == [1, 2, 3, 4, 5] and b is not a

reverse_in_place(a)
assert a == [5, 4, 3, 2, 1]


max_depth = 0


def recursive_total(n, depth=1):
    global max_depth
    max_depth = max(max_depth, depth)
    return 0 if n == 0 else n + recursive_total(n - 1, depth + 1)


assert recursive_total(50) == 1275
assert max_depth == 51           # n + 1 frames were alive at the deepest point: O(n) stack space


def loop_total(n):
    total = 0
    for i in range(1, n + 1):
        total += i               # one accumulator: O(1) extra space
    return total


assert loop_total(50) == 1275

# A generator produces items lazily, so it needs O(1) memory, unlike a list of the same items.
gen = (i * i for i in range(100000))
assert sys.getsizeof(gen) < sys.getsizeof(list(range(100000)))
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

std::vector<int> reversedCopy(const std::vector<int>& v) {
    return std::vector<int>(v.rbegin(), v.rend());  // new vector: O(n) extra space
}

void reverseInPlace(std::vector<int>& v) {
    if (v.empty()) return;
    std::size_t left = 0, right = v.size() - 1;
    while (left < right) {
        std::swap(v[left], v[right]);  // O(1) extra space
        ++left;
        --right;
    }
}

int maxDepth = 0;

int recursiveTotal(int n, int depth = 1) {
    maxDepth = std::max(maxDepth, depth);
    return n == 0 ? 0 : n + recursiveTotal(n - 1, depth + 1);
}

int main() {
    std::vector<int> a = {1, 2, 3, 4, 5};
    std::vector<int> b = reversedCopy(a);
    assert(b[0] == 5 && a[0] == 1);

    reverseInPlace(a);
    assert(a[0] == 5 && a[4] == 1);

    assert(recursiveTotal(50) == 1275);
    assert(maxDepth == 51);  // n + 1 frames at the deepest point: O(n) stack space

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
For the examples above: copying a reversed list is O(n) space and O(n) time; reversing in place is O(1) extra space and O(n) time; the recursive sum is O(n) time and O(n) stack space; the loop sum is O(n) time and O(1) space. Typical algorithm costs worth remembering are binary search with a loop at O(1) space and with recursion at O(log n), merge sort at O(n) extra space, heap sort at O(1) extra space, and quicksort at O(log n) expected stack space. Storing an n by n table costs O(n squared), which for n = 10,000 is 100 million cells and may exceed memory limits even though the time is fine.

## Common Mistakes & Misconceptions
A typical symptom is "Memory Limit Exceeded" or a MemoryError on large inputs, for example from copying the list in every recursive call or building a table that is too big. Students forget that recursion uses stack space and report O(1) for a recursive algorithm that goes n levels deep. They also count the input as extra space, or the reverse, forget the output; the convention should be stated. Another misconception is that Python list slicing is free: `a[1:]` copies. Finally, believing that lower space is always better ignores trade-offs; sometimes using a table makes the time exponentially smaller and is the right choice.

## Builds On
This concept builds on Time Complexity & Big-O: the same notation, rules about dropping constants and growth classes apply, only to memory instead of steps. It also builds on Stack vs Heap Memory, because auxiliary space splits into heap allocations (arrays, tables, copies) and stack space for recursion frames, and you need to know where each kind of memory lives to count it.

## Leads To
Dynamic programming trades space for time and often reduces its tables from two dimensions to one, and sorting algorithms are compared by whether they are in place. Hash tables and graph representations are chosen partly by their memory footprint, and recurrence relations also describe the depth of recursion that drives stack space.

## Check Yourself
**Q1.** What does it mean for an algorithm to be in place?
**A1.** It uses only a constant amount of extra memory beyond the input.
**Q2.** What is the stack space of a recursion that goes n levels deep?
**A2.** O(n), because n frames are alive at the deepest point.
**Q3.** Why is `values[1:]` inside a recursive function costly?
**A3.** Each slice copies the remaining items, using extra time and memory at every call.
