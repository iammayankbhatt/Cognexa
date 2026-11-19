---
id: call_stack
name: "Function Calls & the Call Stack"
cluster: foundations
reviewed: false
sources:
  - "Bryant and O'Hallaron, Computer Systems: A Programmer's Perspective, Section 3.7 (Procedures)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (Recursion) and Section 1.3 (Stacks)"
---

## Overview
The call stack is the part of memory that keeps track of which functions are currently running and where each one should resume. Every time a function is called, a stack frame is pushed holding its parameters, its local variables and the address to return to. When the function returns, its frame is popped and execution resumes in the caller. The stack has a limited size, so a chain of calls that goes too deep causes a stack overflow, which Python reports as RecursionError and Java as StackOverflowError.

## Intuition
Imagine you are reading a book and your phone rings. You put a bookmark in the book and answer the call. During the call someone asks you to look something up, so you put the call on hold and open a web page. Each interruption adds a bookmark, and you resume them strictly in reverse order: finish the web page, return to the call, return to the book. The pile of bookmarks is the call stack, and if you stack interruptions on top of interruptions without ever finishing any, you eventually run out of room.

## How It Works
A call has three steps. First the caller evaluates the arguments and pushes a new frame. The frame stores the parameters, space for local variables and a return address that says where in the caller to continue. Second the body runs, possibly calling other functions that push more frames on top. Third, when the function finishes, its frame is popped and the return value is handed to the caller, which continues at the saved return address.

The stack is last in, first out, so only the topmost frame is active. If function a calls b and b calls c, the stack grows a, b, c from bottom to top, and returns unwind it in the reverse order c, b, a. The frames below the top are paused, each remembering exactly where it stopped.

The stack has a fixed capacity, typically a few megabytes. Python also limits the number of nested calls, by default about one thousand, and raises `RecursionError: maximum recursion depth exceeded` before the machine stack is exhausted. In C++ and Java there is no such friendly limit in the language itself: exhausting the stack crashes the program with a stack overflow or a segmentation fault.

A call that never reaches a stopping point, such as a recursive function missing its base case, keeps pushing frames until the stack is full. The same effect can happen with legitimate but very deep recursion, for example recursing a million levels deep on a long list. The remedy is to reduce depth, rewrite the algorithm with a loop, or use an explicit stack data structure on the heap, which can grow much larger.

## Worked Example
Trace `factorial(3)` defined as `1 if n <= 1 else n * factorial(n - 1)`.

Call factorial(3): frame F3 is pushed with n = 3 and it needs factorial(2) before it can multiply. Call factorial(2): frame F2 is pushed with n = 2 and needs factorial(1). Call factorial(1): frame F1 is pushed with n = 1 and returns 1 immediately, so F1 is popped. F2 now computes 2 times 1 = 2 and returns, popping F2. F3 computes 3 times 2 = 6 and returns, popping F3. At the deepest moment the stack held three frames. A call such as factorial(5000) would need 5000 frames and in Python would raise RecursionError.

## Code
```python
import sys


def factorial(n):
    return 1 if n <= 1 else n * factorial(n - 1)


assert factorial(5) == 120

# Record the order of entering and leaving calls to see the stack at work.
trace = []


def visit(n):
    trace.append("enter %d" % n)
    if n > 0:
        visit(n - 1)
    trace.append("exit %d" % n)


visit(2)
assert trace == ["enter 2", "enter 1", "enter 0", "exit 0", "exit 1", "exit 2"]


def depth(n):
    return 0 if n == 0 else 1 + depth(n - 1)


# Asking for more nested calls than the limit allows raises RecursionError.
too_deep = sys.getrecursionlimit() * 2
try:
    depth(too_deep)
except RecursionError:
    overflowed = True
else:
    overflowed = False
assert overflowed


# An explicit stack lives on the heap, so it can be far deeper than the call stack.
def depth_iterative(n):
    stack = list(range(n))
    count = 0
    while stack:
        stack.pop()
        count += 1
    return count


assert depth_iterative(100000) == 100000
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

std::vector<std::string> trace;

void visit(int n) {
    trace.push_back("enter " + std::to_string(n));
    if (n > 0) visit(n - 1);
    trace.push_back("exit " + std::to_string(n));
}

long long factorial(int n) { return n <= 1 ? 1 : n * factorial(n - 1); }

int main() {
    assert(factorial(5) == 120);

    visit(2);
    std::vector<std::string> expected = {"enter 2", "enter 1", "enter 0", "exit 0", "exit 1", "exit 2"};
    assert(trace == expected);

    // An explicit stack on the heap can grow far deeper than the call stack allows.
    std::vector<int> stack;
    for (int i = 0; i < 100000; ++i) stack.push_back(i);
    int count = 0;
    while (!stack.empty()) {
        stack.pop_back();
        ++count;
    }
    assert(count == 100000);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Pushing or popping a frame is O(1). A chain of d nested calls uses O(d) stack memory, because each frame has a roughly constant size. For recursive algorithms the space complexity therefore includes the recursion depth: a function that recurses n levels deep uses O(n) extra space, while one that halves the problem each time uses only O(log n). The time cost of the call mechanism itself is a small constant per call, which is why replacing recursion by a loop can be somewhat faster as well as safer.

## Common Mistakes & Misconceptions
The signature symptoms are `RecursionError: maximum recursion depth exceeded` in Python, `StackOverflowError` in Java, and a segmentation fault in C++ when recursion goes too deep. Students who see these often assume the machine is too slow or the memory is full, when the real cause is a missing or unreachable base case or an input that needs more frames than the stack holds. Another misconception is that raising the recursion limit with `sys.setrecursionlimit` fixes the design; it only lets the program crash the interpreter at a larger depth. Students also forget that local variables are separate in each call, so a variable changed in a deeper frame does not change the caller's copy.

## Builds On
This concept builds on Functions & Parameters: a stack frame is the machine's record of one call, holding exactly the parameters and locals that a function defines. It also builds on Stack vs Heap Memory, because the call stack is the stack region described there, with its automatic allocation, fixed size and limited depth, in contrast to the larger heap.

## Leads To
Recursion is a function calling itself, so each level adds a frame to the call stack and the base case ends the descent. The stack data structure gives a way to simulate the call stack explicitly, and depth-first search can be written recursively or with its own stack.

## Check Yourself
**Q1.** What is stored in a stack frame?
**A1.** The call's parameters, its local variables and the address where execution resumes in the caller.
**Q2.** What error does Python raise when recursion goes too deep?
**A2.** RecursionError: maximum recursion depth exceeded.
**Q3.** In what order are frames removed when functions return?
**A3.** In reverse order of calling: the most recently called function returns first.
