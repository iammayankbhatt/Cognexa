---
id: variables_memory
name: "Variables, Data Types & Memory"
cluster: foundations
reviewed: false
sources:
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (Basic Programming Model)"
  - "Bryant and O'Hallaron, Computer Systems: A Programmer's Perspective, Chapter 2 (Representing and Manipulating Information)"
---

## Overview
A variable is a name attached to a place in the computer's memory where a value is kept. The data type of that value decides how many bytes it occupies and what operations mean: adding two integers is not the same as adding two strings, and dividing integers is not the same as dividing floating-point numbers. Understanding this small model explains a surprising number of bugs, from integers that suddenly turn negative to decimal sums that are slightly off.

## Intuition
Think of memory as a long street of numbered mailboxes, each holding one byte. A variable is a label you stick on one mailbox, or on a short run of neighbouring mailboxes when the value is bigger than a byte. The type tells the computer how many mailboxes the label covers and how to read the bits inside: the same eight bits can mean the number 65 or the letter A, depending on the type.

## How It Works
Every value is stored as bits. An integer type has a fixed width in languages such as C++ and Java: a 32-bit signed integer holds values from about minus 2.1 billion to plus 2.1 billion. When arithmetic goes beyond the range, the result wraps around (for unsigned types) or is undefined behaviour (for signed types in C++). Python is different: its integers grow as needed, so they never overflow, but they are slower and use more memory.

Floating-point numbers store a sign, an exponent and a fraction in binary. Many decimal fractions, such as 0.1, have no exact binary representation, so 0.1 + 0.2 is not exactly 0.3. Compare floats with a small tolerance, never with equality.

Assignment copies a value or, for objects, a reference to it. In Python, `y = x` makes two names refer to the same object; since integers and strings cannot be changed in place, this is invisible, but with lists it causes sharing. Integer division in C++ truncates (7 / 2 is 3) while Python uses `//` for that and `/` always produces a float.

Types also determine what an operator does. In Python `"3" + "4"` joins text into "34", whereas `3 + 4` is 7. A type error appears when an operation makes no sense for the given types.

## Worked Example
Suppose a program stores a score in a 32-bit signed integer and adds one when the score is 2,147,483,647. The binary pattern 0111...1 becomes 1000...0 after adding one, which a signed type reads as minus 2,147,483,648. The score "wrapped" to the most negative value. In Python the same addition simply gives 2,147,483,648 because the integer silently grows.

Now compute 0.1 + 0.2 in a float. The nearest binary values to 0.1 and 0.2 are slightly off, and their sum is 0.30000000000000004. A test `x == 0.3` fails even though the mathematics is right, so the fix is `abs(x - 0.3) < 1e-9`.

## Code
```python
x = 7
y = x          # both names refer to the same int value
assert x == y == 7

# Python integers grow as needed; fixed-width integers wrap around.
assert 2 ** 100 > 2 ** 63

def wrap32(v):
    """Simulate what a 32-bit signed integer does with a value."""
    v &= 0xFFFFFFFF
    return v - 2 ** 32 if v >= 2 ** 31 else v

assert wrap32(2 ** 31 - 1) == 2147483647
assert wrap32(2 ** 31) == -2147483648      # overflow wraps to the most negative value

# Floats are binary approximations.
assert 0.1 + 0.2 != 0.3
assert abs((0.1 + 0.2) - 0.3) < 1e-9

# The type decides what an operator means.
assert "3" + "4" == "34" and 3 + 4 == 7
assert 7 // 2 == 3 and 7 / 2 == 3.5
print("all checks passed")
```

```cpp
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>

int main() {
    int32_t a = INT32_MAX;
    // Signed overflow is undefined behaviour in C++, so widen first, then wrap explicitly.
    int64_t wide = static_cast<int64_t>(a) + 1;
    assert(wide == 2147483648LL);
    uint32_t wrapped = static_cast<uint32_t>(a) + 1u;  // unsigned arithmetic wraps by definition
    assert(wrapped == 2147483648u);

    assert(sizeof(int32_t) == 4 && sizeof(int64_t) == 8 && sizeof(char) == 1);

    assert(0.1 + 0.2 != 0.3);                           // binary floating point is approximate
    assert(std::fabs((0.1 + 0.2) - 0.3) < 1e-9);

    assert(7 / 2 == 3);                                 // integer division truncates
    assert(7 / 2.0 == 3.5);                             // one double operand makes it floating point
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Reading or writing a variable is a constant-time operation, and a value of a fixed-width type occupies a constant amount of memory, for example 4 bytes for a 32-bit integer. Python integers are the exception: a big integer with b bits takes about b/8 bytes and arithmetic on it costs time proportional to its size, which is why very large numbers feel slower. The space a program uses is the sum of the sizes of its variables plus any structures they point to.

## Common Mistakes & Misconceptions
A classic symptom is a total that suddenly becomes a large negative number after many additions: that is integer overflow in a fixed-width type. Another is a comparison like `0.1 + 0.2 == 0.3` returning False. Beginners also use a variable before assigning it, which raises a NameError in Python or reads garbage in C++, and they confuse `=` (assignment) with `==` (comparison). Integer division surprises people who expect 7 / 2 to be 3.5 in C++. Finally, believing that `y = x` copies a list in Python leads to bugs where changing y changes x, which is explained in the pointers and references concept.

## Builds On
This is a foundation concept with no prerequisites in the graph. It assumes only that you know programs consist of statements that compute and store values.

## Leads To
Conditionals and loops use variables and comparisons to make decisions. Pointers and references extend the memory model by letting a variable hold the address of another value, and bit manipulation works directly on the binary representation described here.

## Check Yourself
**Q1.** Why does 0.1 + 0.2 not equal 0.3 in most languages?
**A1.** Those decimals cannot be stored exactly in binary, so each carries a tiny error that shows up in the sum.
**Q2.** What happens when a 32-bit signed integer holding 2,147,483,647 is incremented in a language that wraps?
**A2.** It wraps to minus 2,147,483,648.
**Q3.** What is 7 // 2 and 7 / 2 in Python?
**A3.** 3 and 3.5.
