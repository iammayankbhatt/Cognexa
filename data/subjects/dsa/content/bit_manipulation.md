---
id: bit_manipulation
name: "Bit Manipulation"
cluster: foundations
reviewed: false
sources:
  - "Warren, Hacker's Delight, Chapter 2 (Basics)"
  - "CLRS, Section 31.1 and exercises on binary representation; Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (bitwise operators)"
---

## Overview
Every integer is stored as a pattern of bits, ones and zeros. Bit manipulation means working on those bits directly with operators such as AND, OR, XOR, NOT and shifts. These operations are among the fastest the processor offers and they unlock compact tricks: testing whether a number is a power of two, packing many true or false flags into one integer, or finding the single unpaired value in a list. They also form the foundation of structures such as the Fenwick tree.

## Intuition
Picture a row of light switches, each either on or off. A number is just the pattern of the switches. AND with a mask is like covering all switches except the ones you care about so you can read only those. OR turns chosen switches on. XOR flips chosen switches. A shift slides the whole row left or right, which multiplies or divides by two, like adding or removing a zero at the end of a decimal number.

## How It Works
The bitwise AND `a & b` gives a one only where both bits are one. OR `a | b` gives a one where either is one. XOR `a ^ b` gives a one where the bits differ, so `x ^ x` is 0 and `x ^ 0` is x. NOT `~a` flips every bit. A left shift `a << k` moves bits k places left, which multiplies by 2 to the power k; a right shift `a >> k` divides by 2 to the power k and discards the remainder.

A mask is a number whose set bits select positions of interest. The mask for bit i is `1 << i`. To test bit i, compute `(x >> i) & 1`. To set bit i use `x | (1 << i)`, to clear it use `x & ~(1 << i)`, and to toggle it use `x ^ (1 << i)`.

Several classic tricks follow. A positive number is a power of two exactly when it has a single set bit, which is equivalent to `x & (x - 1) == 0`, because subtracting one flips the lowest set bit and everything below it. Repeating `x &= x - 1` removes the lowest set bit each time, so counting how many iterations it takes counts the set bits. XOR of all numbers in a list cancels pairs of equal values, so if every value appears twice except one, the XOR of all values is the unpaired one.

Negative integers are stored in two's complement: the value minus one is all ones, and `-x` equals `~x + 1`. In Python integers are unbounded, so `~x` is `-x - 1` and masks such as `& 0xFFFFFFFF` are used to simulate 32-bit behaviour.

## Worked Example
Is 12 a power of two? In binary 12 is 1100 and 11 is 1011, so 12 AND 11 is 1000, which is not zero; 12 is not a power of two. For 16 the binary is 10000 and 15 is 01111, so 16 AND 15 is 0; it is a power of two.

Count the set bits in 13, which is 1101. Step one: 1101 AND 1100 gives 1100, count 1. Step two: 1100 AND 1011 gives 1000, count 2. Step three: 1000 AND 0111 gives 0, count 3. So 13 has three set bits.

Find the unpaired number in [4, 7, 4, 9, 7]. XOR them: 4 ^ 7 = 3, 3 ^ 4 = 7, 7 ^ 9 = 14, 14 ^ 7 = 9. The unpaired value is 9.

## Code
```python
def is_power_of_two(x):
    return x > 0 and x & (x - 1) == 0


def count_set_bits(x):
    count = 0
    while x:
        x &= x - 1          # clear the lowest set bit
        count += 1
    return count


def single_number(values):
    result = 0
    for v in values:
        result ^= v         # equal pairs cancel out
    return result


assert is_power_of_two(16) and not is_power_of_two(12) and not is_power_of_two(0)
assert count_set_bits(13) == 3 and count_set_bits(0) == 0
assert single_number([4, 7, 4, 9, 7]) == 9

x = 0b1010
assert (x >> 1) & 1 == 1        # test bit 1
assert x | (1 << 2) == 0b1110   # set bit 2
assert x & ~(1 << 1) == 0b1000  # clear bit 1
assert x ^ (1 << 3) == 0b0010   # toggle bit 3
assert 3 << 2 == 12 and 20 >> 2 == 5   # shifts multiply and divide by powers of two
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

bool isPowerOfTwo(unsigned x) { return x != 0 && (x & (x - 1)) == 0; }

int countSetBits(unsigned x) {
    int count = 0;
    while (x) {
        x &= x - 1;  // clear the lowest set bit
        ++count;
    }
    return count;
}

int singleNumber(const std::vector<int>& values) {
    int result = 0;
    for (int v : values) result ^= v;  // equal pairs cancel out
    return result;
}

int main() {
    assert(isPowerOfTwo(16) && !isPowerOfTwo(12) && !isPowerOfTwo(0));
    assert(countSetBits(13) == 3 && countSetBits(0) == 0);
    assert(singleNumber({4, 7, 4, 9, 7}) == 9);

    unsigned x = 10;  // binary 1010
    assert(((x >> 1) & 1u) == 1u);
    assert((x | (1u << 2)) == 14u);
    assert((x & ~(1u << 1)) == 8u);
    assert((x ^ (1u << 3)) == 2u);
    assert((3u << 2) == 12u && (20u >> 2) == 5u);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Each bitwise operation and each shift on a machine word is O(1). Counting set bits with `x &= x - 1` loops once per set bit, so it takes time proportional to the number of ones, which is at most the word size, 32 or 64, and hence O(1) for fixed-width integers (O(log x) in general). Scanning all bit positions takes O(log x) steps. Using bits as flags can shrink memory by a factor of up to 64 compared to one boolean per integer, so a set of n small values can use about n over 64 words.

## Common Mistakes & Misconceptions
A frequent bug is writing `&` where `&&` was intended, or the reverse: `&` is a bitwise operator on numbers, while `&&` or `and` is a logical operator on truth values, so the two give different results. Operator precedence also bites: in C++ and Python `x & 1 == 0` is parsed as `x & (1 == 0)` in C++, so parentheses around bitwise operations are essential. Beginners confuse `^` with exponentiation, which Python writes `**`. Right-shifting negative numbers behaves differently across languages, and in C++ shifting a signed value into the sign bit or by too large an amount is undefined behaviour. Finally, many forget that bit positions count from zero at the right, so bit 0 is the least significant bit.

## Builds On
This concept builds on Variables, Data Types & Memory: you need the idea that an integer is stored as a fixed-width pattern of bits, that overflow wraps, and that signed numbers use two's complement. Without the memory model, shifts and masks have no meaning.

## Leads To
The Fenwick tree uses the lowest set bit of an index, computed as `i & -i`, to jump around its array. Bit masks also represent subsets in backtracking and dynamic programming, and hash functions mix bits with shifts and XOR.

## Check Yourself
**Q1.** What does `x & (x - 1)` do?
**A1.** It clears the lowest set bit of x, and the result is zero exactly when x is zero or a power of two.
**Q2.** What is 5 ^ 5, and what is 5 ^ 0?
**A2.** 0 and 5.
**Q3.** What is `1 << 4` and what does a left shift by k do in general?
**A3.** 16; a left shift by k multiplies the value by 2 to the power k.
