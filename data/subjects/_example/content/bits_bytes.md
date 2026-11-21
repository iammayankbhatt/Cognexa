---
id: bits_bytes
name: "Bits & Bytes"
cluster: representation
reviewed: false
sources:
  - "Bryant and O'Hallaron, Computer Systems: A Programmer's Perspective 3rd ed., Section 2.1 (Information Storage)"
  - "Petzold, Code: The Hidden Language of Computer Hardware and Software, chapters on bits and bytes"
---

## Overview
A bit is the smallest unit of information a computer stores: a single binary digit that is either 0 or 1. Everything a program handles, from numbers and text to images, is ultimately a pattern of bits. Bits are grouped into bytes of eight bits, and the byte is the unit that memory addresses count. The most useful fact about bits is how fast the number of patterns grows: one bit has 2 patterns, two bits have 4, and n bits have 2 to the power n. A single byte therefore has 256 different values.

## Intuition
Think of a row of light switches. One switch can be off or on. Add a second switch and every setting of the first can be paired with either setting of the second, so the number of combinations doubles to four. Each new switch doubles the count again. Eight switches give 2 x 2 x 2 x 2 x 2 x 2 x 2 x 2 = 256 combinations. That doubling is why storage sizes and value ranges are so often powers of two: 256 values in a byte, 65,536 in two bytes, and about four billion in four bytes.

## How It Works
Hardware stores a bit as one of two physical states, such as a high or low voltage or a charged or empty capacitor. Memory is organised as a long sequence of bytes, each with a numeric address. A byte holds eight bits, numbered from bit 0 (the least significant, on the right) to bit 7 (the most significant, on the left). Larger values use several consecutive bytes: a 32-bit integer takes four bytes.

To decide how many bits you need for k different values, find the smallest n with 2^n at least k. Storing the 26 lowercase letters needs 5 bits, because 2^4 = 16 is too few and 2^5 = 32 is enough. Larger units count bytes: a kilobyte is 1000 bytes in the SI sense, while a kibibyte (KiB) is exactly 1024 bytes, which is 2^10.

## Worked Example
How many bits are needed to give every student in a class of 100 a distinct code?

1. Try powers of two: 2^6 = 64 is fewer than 100, so 6 bits are not enough.
2. 2^7 = 128 is at least 100, so 7 bits suffice.
3. The 28 unused patterns (128 - 100) are simply never assigned.

And how many values fit in 3 bytes? Three bytes are 24 bits, so 2^24 = 16,777,216 values. This is exactly why 24-bit colour offers about 16.7 million colours: 8 bits each for red, green and blue.

## Code
```python
import math

def values(bits: int) -> int:
    return 2 ** bits

def bits_needed(k: int) -> int:
    """Smallest n with 2**n >= k (at least 1 bit)."""
    return max(1, math.ceil(math.log2(k)))

assert values(1) == 2 and values(8) == 256 and values(16) == 65536
assert bits_needed(26) == 5 and bits_needed(100) == 7 and bits_needed(256) == 8
assert bits_needed(257) == 9
assert values(24) == 16_777_216
print("a byte holds", values(8), "values")
```

```cpp
#include <cassert>
#include <cstdint>
#include <iostream>

long long values(int bits) { return 1LL << bits; }

int bits_needed(long long k) {
    int n = 1;
    while ((1LL << n) < k) ++n;
    return n;
}

int main() {
    assert(values(8) == 256 && values(16) == 65536);
    assert(bits_needed(26) == 5 && bits_needed(100) == 7 && bits_needed(257) == 9);
    assert(sizeof(std::uint8_t) == 1 && sizeof(std::uint32_t) == 4);
    std::cout << "a byte holds " << values(8) << " values\n";
    return 0;
}
```

## Complexity
Counting patterns is pure arithmetic: computing 2^n with a shift is O(1) for word-sized n. Finding the bits needed for k values takes O(log k) steps when you double a counter, or O(1) with a logarithm. Storage grows linearly with the number of bits, while the number of representable values grows exponentially, which is the whole point of binary encoding.

## Common Mistakes & Misconceptions
- **Thinking n bits hold n values.** They hold 2^n values; 8 bits hold 256, not 8.
- **Forgetting zero.** An 8-bit unsigned number ranges from 0 to 255, so the largest value is 2^8 - 1, not 256.
- **Mixing kilobytes and kibibytes.** 1 KB is 1000 bytes; 1 KiB is 1024 bytes. Drive makers use the first, many operating systems report the second.
- **Rounding bits down.** 100 values need 7 bits, because 6 bits give only 64 patterns.

## Builds On
This is a foundation concept with no prerequisites in this subject. It only assumes you can multiply and are comfortable with the idea of powers.

## Leads To
Binary Numbers use these bit patterns to write whole numbers in base 2, giving every pattern a numeric value. From there the pack moves on to hexadecimal, two's complement and bitwise operations.

## Check Yourself
**Q1.** How many different values can 10 bits represent?
**A1.** 2^10 = 1024.
**Q2.** What is the largest unsigned value in one byte?
**A2.** 255, because the 256 patterns are 0 through 255.
**Q3.** How many bits are needed to label 33 items uniquely?
**A3.** 6, because 2^5 = 32 is too few and 2^6 = 64 is enough.
