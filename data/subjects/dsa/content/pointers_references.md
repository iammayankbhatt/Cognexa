---
id: pointers_references
name: "Pointers & References"
cluster: foundations
reviewed: false
sources:
  - "Kernighan and Ritchie, The C Programming Language, Chapter 5 (Pointers and Arrays)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (references to objects)"
---

## Overview
A pointer or reference is a variable whose value is the location of another value in memory. Instead of holding the data itself, it holds directions to it. This indirection is what makes linked lists, trees and graphs possible, lets several names share one object, and allows a function to change its caller's data. It also introduces new bugs: following a null pointer, or following one whose target has been freed.

## Intuition
A pointer is like a street address written on a sticky note. The note is not the house; it just tells you where to find it. Two notes with the same address lead to the same house, so if one visitor repaints it, the other sees the new colour. A blank note, or a note for a house that has been demolished, leads nowhere, and trying to walk there is an error.

## How It Works
Every variable lives at a memory address. In C++ the expression `&x` gives the address of x, a pointer variable `int* p = &x` stores it, and `*p` follows the pointer to read or write x. The special value `nullptr` means "points to nothing", and dereferencing it crashes the program with a segmentation fault. A C++ reference `int& r = x` is an alias: another name for x that cannot be null and cannot be rebound.

In Python and Java you do not see addresses, but every variable holding an object is a reference. The assignment `b = a` copies the reference, not the object, so `a` and `b` are two names for one object. This is aliasing. With immutable objects such as integers it is harmless; with mutable objects such as lists, a change through one name is visible through the other. The `is` operator tests whether two names refer to the same object, while `==` compares their contents. The value `None` is Python's null, and calling a method on it gives an AttributeError such as "'NoneType' object has no attribute ...".

To get an independent copy you must copy explicitly: `b = a.copy()` or `b = a[:]` for a list. A shallow copy copies the outer container but still shares the inner objects, so nested lists need `copy.deepcopy`.

A dangling pointer points to memory that has been released, and reading it is undefined behaviour. Garbage-collected languages avoid this by keeping an object alive while any reference to it exists.

## Worked Example
Consider the C++ statements `int x = 10; int* p = &x; *p = 20;`. The variable p holds the address of x. The statement `*p = 20` follows that address and writes 20 there, so x becomes 20 without ever being named. A swap function can use this: `void swap(int* a, int* b)` exchanges the values stored at the two addresses, so the caller's variables really change.

In Python, trace `a = [1, 2]; b = a; b.append(3)`. After the second statement both names refer to the same list object. The append changes that one object, so `a` is now [1, 2, 3] too. With `b = a.copy()` the append would affect only b.

## Code
```python
a = [1, 2]
b = a                      # copies the reference, not the list
b.append(3)
assert a == [1, 2, 3] and a is b

c = a.copy()               # an independent shallow copy
c.append(4)
assert a == [1, 2, 3] and c == [1, 2, 3, 4] and a is not c

# == compares contents, is compares identity
assert [1, 2] == [1, 2] and [1, 2] is not [1, 2]

# A shallow copy still shares nested objects.
nested = [[1], [2]]
shallow = nested.copy()
shallow[0].append(99)
assert nested[0] == [1, 99]

# None is Python's null reference.
node = None
try:
    node.next
except AttributeError:
    pass
else:
    raise AssertionError("expected AttributeError")
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>

void swapValues(int* a, int* b) {  // pointers let the function change the caller's variables
    int tmp = *a;
    *a = *b;
    *b = tmp;
}

void increment(int& r) { ++r; }    // a reference parameter is an alias for the caller's variable

int main() {
    int x = 10;
    int* p = &x;
    *p = 20;
    assert(x == 20);

    int a = 1, b = 2;
    swapValues(&a, &b);
    assert(a == 2 && b == 1);

    increment(a);
    assert(a == 3);

    int* nothing = nullptr;
    assert(nothing == nullptr);  // check before dereferencing; *nothing would crash

    int arr[3] = {5, 6, 7};
    int* q = arr;                // an array name converts to a pointer to its first element
    assert(*(q + 2) == 7 && q[1] == 6);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Following a pointer or reference is a constant-time operation: one memory access. Copying a reference costs O(1) regardless of the size of the object it points to, whereas copying the object itself costs time and space proportional to its size, which is why passing large objects by reference is faster. A pointer takes a fixed amount of memory, typically 8 bytes on a 64-bit machine, so a structure made of n nodes joined by pointers needs space proportional to n plus the pointers.

## Common Mistakes & Misconceptions
Typical symptoms are `AttributeError: 'NoneType' object has no attribute ...` in Python, `NullPointerException` in Java and a segmentation fault in C++, all caused by following a null reference. In Python, a list that changes unexpectedly is usually aliasing: two names share one list because `b = a` did not copy it. Students also confuse `==` with `is`, or believe `copy()` copies nested lists too. In C++ forgetting that `*p` is the pointed-to value while `p` is the address leads to printing addresses instead of values, and returning a pointer to a local variable creates a dangling pointer because the variable is destroyed when the function returns.

## Builds On
This concept builds on Variables, Data Types & Memory: it depends on the idea that every variable occupies a location in memory and has a type. A pointer is simply a variable whose type is "address of a value of some type", so the memory model from that concept is what gives addresses their meaning.

## Leads To
Stack versus heap memory explains where pointed-to objects live and when they are released. Linked lists, trees and graphs are built from nodes that hold pointers to other nodes, and dynamic arrays rely on pointers to a block of memory that can be replaced by a bigger one.

## Check Yourself
**Q1.** After `b = a` for a Python list a, what happens when you append to b?
**A1.** The append is visible through a as well, because both names refer to the same list.
**Q2.** What is the difference between `==` and `is` in Python?
**A2.** `==` compares values, while `is` checks whether two names refer to the very same object.
**Q3.** What does dereferencing a null pointer in C++ do?
**A3.** It is undefined behaviour and usually crashes with a segmentation fault.
