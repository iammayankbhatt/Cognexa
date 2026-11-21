---
id: bitwise_operations
name: "Bitwise Operations"
cluster: operations
reviewed: false
sources:
  - "Bryant and O'Hallaron, Computer Systems: A Programmer's Perspective 3rd ed., Sections 2.1.7-2.1.9 (Bit-Level, Logical and Shift Operations)"
  - "Warren, Hacker's Delight 2nd ed., Chapter 2 (Basics)"
---

## Overview
Bitwise operations treat a number as a row of bits and work on every position independently. AND (`&`) keeps a bit only where both inputs have a 1, OR (`|`) sets it where either has a 1, XOR (`^`) sets it where the inputs differ, and NOT (`~`) flips every bit. Shifts move all bits left (`<<`) or right (`>>`). Together with a mask, a number that has 1s only in the positions you care about, these operations test, set, clear and toggle individual bits in constant time.

## Intuition
Imagine eight light switches in a row and a stencil with holes over some of them. AND with the stencil shows you only the switches under the holes and hides the rest. OR with the stencil turns on every switch under a hole and leaves the others alone. XOR with the stencil flips the switches under the holes. Shifting slides the whole row of switches one place left or right, which in binary is the same as multiplying or dividing by two.

## How It Works
For a bit position i, the mask is `1 << i`.

- **Test bit i:** `(x >> i) & 1` is 1 if the bit is set, or check `x & (1 << i) != 0`.
- **Set bit i:** `x | (1 << i)`.
- **Clear bit i:** `x & ~(1 << i)`.
- **Toggle bit i:** `x ^ (1 << i)`.

Shifting left by k multiplies by 2^k, and shifting a non-negative number right by k divides by 2^k, rounding down. XOR has two handy properties: `x ^ x == 0` and `x ^ 0 == x`, so XOR-ing the same value twice cancels out. A classic trick is `x & (x - 1)`, which clears the lowest set bit; a positive x is a power of two exactly when that result is 0. Masks are usually written in hex, so `x & 0xFF` keeps the lowest byte.

## Worked Example
Let x = 44, which is 101100 in binary.

1. Test bit 3: 44 >> 3 is 101 (5), and 5 & 1 = 1, so bit 3 is set.
2. Set bit 0: 44 | 1 = 101101 = 45.
3. Clear bit 2: the mask 1 << 2 is 000100, its inverse keeps every other bit, and 101100 & ...111011 = 101000 = 40.
4. Toggle bit 5: 44 ^ 32 = 001100 = 12.
5. Lowest set bit: 44 & 43 = 101100 & 101011 = 101000 = 40, so 44 is not a power of two.

## Code
```python
def test(x: int, i: int) -> bool:
    return (x >> i) & 1 == 1

def set_bit(x: int, i: int) -> int:
    return x | (1 << i)

def clear_bit(x: int, i: int) -> int:
    return x & ~(1 << i)

def toggle(x: int, i: int) -> int:
    return x ^ (1 << i)

def is_power_of_two(x: int) -> bool:
    return x > 0 and x & (x - 1) == 0

x = 0b101100  # 44
assert test(x, 3) and not test(x, 0)
assert set_bit(x, 0) == 45 and clear_bit(x, 2) == 40 and toggle(x, 5) == 12
assert x & (x - 1) == 40 and not is_power_of_two(44) and is_power_of_two(64)
assert 5 << 3 == 40 and 45 >> 2 == 11 and 0x1234 & 0xFF == 0x34
assert [n for n in range(1, 200) if is_power_of_two(n)] == [1, 2, 4, 8, 16, 32, 64, 128]
for a in range(64):
    for b in range(64):
        assert a ^ b ^ b == a and (a & b) | (a ^ b) == a | b
print(bin(clear_bit(x, 2)))
```

```cpp
#include <cassert>
#include <iostream>

bool test(unsigned x, int i) { return (x >> i) & 1u; }
unsigned set_bit(unsigned x, int i) { return x | (1u << i); }
unsigned clear_bit(unsigned x, int i) { return x & ~(1u << i); }
unsigned toggle(unsigned x, int i) { return x ^ (1u << i); }
bool is_power_of_two(unsigned x) { return x != 0 && (x & (x - 1)) == 0; }

int main() {
    unsigned x = 44;  // 101100
    assert(test(x, 3) && !test(x, 0));
    assert(set_bit(x, 0) == 45 && clear_bit(x, 2) == 40 && toggle(x, 5) == 12);
    assert(!is_power_of_two(44) && is_power_of_two(64));
    assert((5u << 3) == 40 && (45u >> 2) == 11 && (0x1234u & 0xFFu) == 0x34u);
    std::cout << clear_bit(x, 2) << "\n";
    return 0;
}
```

## Complexity
Each bitwise operation and shift on a machine word is O(1); the processor handles all bits in parallel. Counting the set bits of x by repeatedly clearing the lowest one takes O(k) steps for k set bits, and many processors offer a single popcount instruction.

## Common Mistakes & Misconceptions
- **Confusing `&` with `and`.** `&` works bit by bit; `and` (or `&&` in C++) is a logical operator on whole truth values.
- **Operator precedence in C and C++.** `x & 1 == 0` parses as `x & (1 == 0)`; write `(x & 1) == 0`.
- **Using `^` for powers.** In Python and C++, `2 ^ 3` is XOR (1), not 8; use `2 ** 3` or `1 << 3`.
- **Shifting negative numbers right.** In Python `-5 >> 1` is -3 (rounds toward minus infinity); in C++ signed right shifts are implementation-defined before C++20, so use unsigned types for bit work.

## Builds On
Binary Numbers: every operation here is defined on the binary digits of a number, and shifts move those digits between place values. Masks are often written in Hexadecimal.

## Leads To
In this demo pack Bitwise Operations is a leaf concept. In a full course it leads on to bit sets, hashing, Gray codes and the bit tricks used in competitive programming.

## Check Yourself
**Q1.** What is 12 & 10?
**A1.** 8 (1100 & 1010 = 1000).
**Q2.** How do you clear bit 4 of x?
**A2.** x & ~(1 << 4).
**Q3.** What does x & (x - 1) do?
**A3.** It clears the lowest set bit of x.
