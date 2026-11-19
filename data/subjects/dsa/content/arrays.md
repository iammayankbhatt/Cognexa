---
id: arrays
name: "Arrays"
cluster: foundations
reviewed: false
sources:
  - "CLRS, Section 10.1 (Stacks and queues; array basics) and Chapter 2 (sorting arrays)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (Arrays)"
---

## Overview
An array stores a fixed number of elements of the same type in one continuous block of memory. Each element is reached by its index, a position counted from zero. Because the elements sit side by side, the computer can jump straight to any index in constant time, which makes arrays the simplest and fastest way to store a collection. The price is rigidity: the size is fixed when the array is created, and inserting or removing in the middle requires shifting other elements.

## Intuition
Picture a row of numbered lockers in a school corridor, all the same size and all next to each other. If you know locker number 37, you walk straight to it without checking the first 36. If you want to squeeze a new locker between 10 and 11, though, every locker after it must be renumbered and moved over. That is exactly the trade-off of arrays: instant access by position, expensive insertion in the middle.

## How It Works
When an array of n elements is created, the program reserves n times the element size in bytes, in one block starting at some base address. The element at index i lives at the address base plus i times the element size. That single multiplication and addition is why access by index takes constant time, no matter how large the array is.

Indexes start at zero, so a valid index is from 0 to n minus 1. Reading outside that range is an error: Python raises IndexError, Java raises ArrayIndexOutOfBoundsException, and C++ may silently read other memory, which is far worse.

Traversal visits every element with a loop. Searching an unsorted array requires checking elements one by one. Writing to an existing index overwrites that slot in constant time. Inserting at position k requires shifting all elements from k onward one place to the right to make room, and deleting shifts them left to close the gap, so both take time proportional to the number of elements moved. Appending to the end is cheap only if there is spare room, which is why fixed arrays cannot simply grow.

Python's list looks like an array but is a dynamic array that resizes itself; a later concept explains how. In C++ a plain array has a fixed size, while std::vector is the resizable version.

## Worked Example
Take the array [10, 20, 30, 40, 50] stored at base address 1000 with 4 bytes per element. Index 3 lives at 1000 + 3 times 4 = 1012 and holds 40. Reading it needs one calculation, not a scan.

Now insert 25 at index 2. Elements 30, 40 and 50 must each shift one place right: 50 moves to index 5, 40 to index 4, 30 to index 3. Then 25 is written at index 2, giving [10, 20, 25, 30, 40, 50]. Three elements moved, which is why inserting near the front of a big array is slow. Deleting index 0 would move every other element left.

## Code
```python
arr = [10, 20, 30, 40, 50]
assert arr[3] == 40                 # constant-time access by index
assert arr[-1] == 50                # Python allows negative indexes from the end

# Insert 25 at index 2 by shifting the tail to the right.
def insert_at(a, k, value):
    a.append(None)                  # make room at the end
    for i in range(len(a) - 1, k, -1):
        a[i] = a[i - 1]             # shift right, starting from the end
    a[k] = value

insert_at(arr, 2, 25)
assert arr == [10, 20, 25, 30, 40, 50]

# Delete index 0 by shifting everything left.
def delete_at(a, k):
    for i in range(k, len(a) - 1):
        a[i] = a[i + 1]
    a.pop()

delete_at(arr, 0)
assert arr == [20, 25, 30, 40, 50]

# Out-of-range access is an error in Python.
try:
    arr[10]
except IndexError:
    pass
else:
    raise AssertionError("expected IndexError")
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>

int main() {
    int arr[8] = {10, 20, 30, 40, 50};
    int size = 5;
    assert(arr[3] == 40);  // constant-time access by index

    // Insert 25 at index 2: shift the tail right, starting from the end.
    for (int i = size; i > 2; --i) arr[i] = arr[i - 1];
    arr[2] = 25;
    ++size;
    assert(size == 6 && arr[2] == 25 && arr[3] == 30 && arr[5] == 50);

    // Delete index 0: shift everything left.
    for (int i = 0; i + 1 < size; ++i) arr[i] = arr[i + 1];
    --size;
    assert(size == 5 && arr[0] == 20 && arr[4] == 50);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Reading or writing by index is O(1). Searching an unsorted array is O(n) in the worst case, because every element may need to be examined, and O(1) in the best case if the target is first. Inserting or deleting at a given index is O(n) in the worst case because of shifting, though inserting or removing at the end is O(1) when there is capacity. An array of n elements uses O(n) memory with no per-element overhead beyond the element itself.

## Common Mistakes & Misconceptions
The typical symptom is an IndexError, ArrayIndexOutOfBoundsException or, in C++, a crash or garbage value, caused by an off-by-one error such as looping to `len(a)` inclusive or using index n on an array of size n. Another is forgetting that indexes start at zero, so the last element is at n minus 1. Students also assume inserting is constant time because access is, and are surprised when a program that inserts at the front of a large array becomes very slow. Finally, copying an array by assignment in Python (`b = a`) does not copy the elements, it creates a second name for the same list.

## Builds On
This concept builds on Conditionals & Loops: almost every array operation is a loop over indexes, and the bounds of those loops determine whether you stay inside the valid range. The shifting algorithms for insertion and deletion are loops whose direction (from the end or from the start) must be chosen carefully to avoid overwriting values.

## Leads To
Strings are arrays of characters with extra rules. Dynamic arrays add automatic resizing, stacks and queues are often implemented on top of arrays, and linear search, binary search, sorting and prefix sums all work directly on arrays.

## Check Yourself
**Q1.** What is the valid index range of an array with 8 elements?
**A1.** 0 through 7.
**Q2.** Why is reading arr[i] constant time?
**A2.** The address is computed directly as base plus i times the element size, with no scanning.
**Q3.** Why is inserting at the front of a large array slow?
**A3.** Every existing element must shift one place to make room, which takes O(n) time.
