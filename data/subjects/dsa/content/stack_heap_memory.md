---
id: stack_heap_memory
name: "Stack vs Heap Memory"
cluster: foundations
reviewed: false
sources:
  - "Bryant and O'Hallaron, Computer Systems: A Programmer's Perspective, Chapter 3 (procedures) and Chapter 9 (dynamic memory allocation)"
  - "Stroustrup, A Tour of C++, Chapter on resource management"
---

## Overview
A running program keeps its data in two main regions. The stack holds the local variables of functions that are currently running, and it is managed automatically: space is reserved when a function is entered and released when it returns. The heap holds data that must outlive a single function call or whose size is not known in advance, and its lifetime is controlled either by the programmer or by a garbage collector. Knowing which region a value lives in explains lifetimes, memory leaks and a family of crashes.

## Intuition
The stack is like a stack of plates at a canteen: you can only add or remove the top plate, and you take the plate you need, use it, and put it back in strict order. It is fast and tidy but you cannot keep a plate for a long time without blocking everyone beneath it. The heap is like a big warehouse with shelves: you can reserve a shelf of any size and keep your goods as long as you want, but you must remember to return the space, and finding a free shelf takes more effort.

## How It Works
When a function is called, the machine pushes a block of memory for it onto the stack, containing its parameters and local variables. When the function returns, that block is popped and the memory becomes available again, so local variables vanish automatically. Allocation on the stack is just moving a pointer, which is why it is extremely fast, and its size is limited, often to a few megabytes.

The heap is a large pool from which a program requests blocks at runtime: `new` in C++, `malloc` in C, object creation in Python and Java. The block stays valid until it is released. In C++ the programmer must call `delete` (or use smart pointers such as `std::unique_ptr` that release automatically); forgetting causes a memory leak, and releasing twice or using memory after release causes crashes and corruption. In Python and Java a garbage collector frees an object when no reference to it remains. Python mostly uses reference counting, with an extra collector for cycles.

In Python, every object lives on the heap, while the local variable names and references live in the function's frame on the stack. When `make_box()` returns a new object, the name inside the function disappears but the object survives because the caller now holds a reference to it.

Because the stack is limited, very deep chains of function calls exhaust it and cause a stack overflow, while allocating too much on the heap leads to running out of memory.

## Worked Example
Consider a C++ function `int* make()` that does `return new int(42);`. The pointer variable is a local on the stack, but the integer 42 is created on the heap. When make returns, the pointer variable is popped, yet the caller received the address, so the integer is still alive. If the caller never deletes it, the 4 bytes leak for the rest of the program. If instead the function had returned the address of a local variable `int x = 42;`, that memory would be popped and reused, leaving a dangling pointer.

In Python, trace `b = make_box()` where make_box creates a Box object and returns it. During the call the frame holds the local name; after the return the frame is gone but `b` keeps the object alive. When `del b` removes the last reference, the object is reclaimed.

## Code
```python
import gc
import weakref


class Box:
    def __init__(self, value):
        self.value = value


def make_box():
    local = Box(7)       # the name 'local' lives in this call's frame; the object is on the heap
    return local


b = make_box()
assert b.value == 7      # the object outlived the call because a reference was returned

ref = weakref.ref(b)     # a weak reference does not keep the object alive
assert ref() is b
del b                    # last strong reference removed
gc.collect()
assert ref() is None     # the object has been reclaimed


def depth(n):            # every call gets its own frame on the call stack
    return 0 if n == 0 else 1 + depth(n - 1)


assert depth(100) == 100
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <memory>

struct Box {
    int value = 0;
};

int* makeOnHeap() { return new int(42); }  // heap memory survives after the function returns

int main() {
    int local = 5;  // stack: destroyed automatically at the end of its scope
    assert(local == 5);

    int* p = makeOnHeap();
    assert(*p == 42);
    delete p;       // heap memory must be released by the program
    p = nullptr;

    std::unique_ptr<Box> box = std::make_unique<Box>();  // released automatically
    box->value = 7;
    assert(box->value == 7);

    {
        int inner = 1;  // lives only inside these braces
        (void)inner;
    }

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Allocating and freeing on the stack costs O(1) because it only moves a stack pointer, and it needs no searching. Heap allocation is also usually fast but more variable, since the allocator may have to find a suitable free block, and it adds bookkeeping memory per block. Stack space is limited, so total recursion depth is bounded by the stack size divided by the frame size, while heap space is bounded by available memory. A program that leaks k bytes per iteration over n iterations uses O(n times k) memory.

## Common Mistakes & Misconceptions
Typical symptoms are a program whose memory usage grows steadily until it crashes (a leak), a crash or strange values caused by using a pointer after `delete` (use after free), and a `segmentation fault` after returning the address of a local variable. Students also believe that Python has no memory concerns, then are surprised by lists that keep growing because references to big objects are kept alive in a global. Another misconception is that `new` is required for every object in C++; ordinary local objects live on the stack and are cleaned up automatically. Finally, many assume the stack and heap are separate hardware, when both are just regions of ordinary memory.

## Builds On
This concept builds on Pointers & References: heap objects are reached through pointers or references, and a dangling pointer is exactly a reference to memory that was released. It also builds on Functions & Parameters, because the stack frame is created per function call and holds that call's parameters and local variables, which is why locals disappear when a function returns.

## Leads To
Function calls and the call stack describe exactly how frames are pushed and popped, which explains stack overflow in recursion. Linked lists allocate each node on the heap, and space complexity analysis counts the heap and stack memory an algorithm uses.

## Check Yourself
**Q1.** Where do local variables of a running function live?
**A1.** On the stack, in the function's frame, and they are released when the function returns.
**Q2.** What is a memory leak?
**A2.** Heap memory that is no longer needed but never released, so the program's memory use keeps growing.
**Q3.** Why is returning the address of a local variable in C++ a bug?
**A3.** The variable is destroyed when the function returns, leaving a dangling pointer.
