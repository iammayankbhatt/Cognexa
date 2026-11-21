---
id: twos_complement
name: "Two's Complement"
cluster: representation
reviewed: false
sources:
  - "Bryant and O'Hallaron, Computer Systems: A Programmer's Perspective 3rd ed., Section 2.2.3 (Two's-Complement Encodings) and 2.3 (Integer Arithmetic)"
  - "Patterson and Hennessy, Computer Organization and Design, Section 2.4 (Signed and Unsigned Numbers)"
---

## Overview
Two's complement is the way almost every computer stores signed integers. With n bits, the top bit has a negative weight of -2^(n-1) and every other bit keeps its usual positive weight. That single rule gives a range from -2^(n-1) to 2^(n-1) - 1, so an 8-bit signed integer holds -128 to 127. The same adding circuit works for signed and unsigned numbers, and negating a number is simple: invert every bit and add one.

## Intuition
Picture an 8-bit counter as a clock with 256 positions. Counting up from 0 reaches 127, and one more step lands on the pattern that unsigned arithmetic calls 128. Two's complement simply relabels the second half of the clock as negative: 128 becomes -128, 255 becomes -1. Going one step back from 0 lands on 255, which is exactly what -1 should be. Because the labels follow the clock, ordinary addition that wraps around 256 automatically gives the right signed answer, as long as the true result fits in the range.

## How It Works
**Value of a pattern.** For bits b(n-1) ... b0, the value is -b(n-1) x 2^(n-1) plus the sum of b(i) x 2^i for the other bits. With 8 bits, 11111011 is -128 + 64 + 32 + 16 + 8 + 2 + 1 = -5.

**Negation.** To get -x, invert every bit of x and add 1. For 5 = 00000101: invert to 11111010, add 1 to get 11111011, which is -5. This works because x plus its inversion is all ones, which is -1.

**Sign bit.** The top bit is 1 exactly for negative numbers, so the sign is easy to test, but it is not a separate minus sign: the other bits change too.

**Overflow.** If a true result is outside the range, the bits wrap around: in 8 bits, 127 + 1 gives the pattern 10000000, which reads as -128. Adding two positives that yields a negative, or two negatives that yields a positive, signals overflow.

## Worked Example
Compute 6 + (-9) in 8 bits.

1. 6 is 00000110.
2. 9 is 00001001; invert to 11110110 and add 1 to get 11110111, which is -9.
3. Add the patterns: 00000110 + 11110111 = 11111101 (no carry out of the top bit).
4. Read 11111101: -128 + 64 + 32 + 16 + 8 + 4 + 1 = -3. Correct, because 6 - 9 = -3.

To double-check, negate the result: invert 11111101 to 00000010 and add 1 to get 00000011, which is 3, so the result was -3.

## Code
```python
BITS = 8
MASK = (1 << BITS) - 1  # 0xFF

def encode(x: int) -> int:
    """Two's-complement bit pattern of x in BITS bits (as an unsigned int)."""
    assert -(1 << (BITS - 1)) <= x < (1 << (BITS - 1))
    return x & MASK

def decode(p: int) -> int:
    return p - (1 << BITS) if p & (1 << (BITS - 1)) else p

def negate(p: int) -> int:
    return ((~p) + 1) & MASK  # invert and add one

assert format(encode(-5), "08b") == "11111011" and decode(0b11111011) == -5
assert decode((encode(6) + encode(-9)) & MASK) == -3
assert decode(encode(127) + 1 & MASK) == -128  # overflow wraps
for x in range(-128, 128):
    assert decode(encode(x)) == x
    if x != -128:
        assert decode(negate(encode(x))) == -x
assert decode(negate(encode(-128))) == -128  # -128 has no positive partner in 8 bits
print(format(encode(-5), "08b"))
```

```cpp
#include <cassert>
#include <cstdint>
#include <iostream>

int main() {
    std::int8_t minus_five = -5;
    std::uint8_t pattern = static_cast<std::uint8_t>(minus_five);
    assert(pattern == 0xFB);  // 11111011
    std::uint8_t five = 5;
    assert(static_cast<std::uint8_t>(~five + 1) == pattern);  // invert and add one
    std::uint8_t sum = static_cast<std::uint8_t>(6 + 0xF7);   // 6 + (-9) as patterns
    assert(static_cast<std::int8_t>(sum) == -3);
    for (int x = -128; x <= 127; ++x) {
        std::uint8_t p = static_cast<std::uint8_t>(x);
        assert(static_cast<std::int8_t>(p) == x);
    }
    std::cout << int(pattern) << "\n";
    return 0;
}
```

## Complexity
Negation is one inversion and one addition, and signed addition uses the same adder as unsigned addition, so all of these are O(1) operations on a machine word (O(n) gate delays for n bits in hardware). No extra circuitry or sign handling is needed, which is the main reason two's complement won over sign-magnitude.

## Common Mistakes & Misconceptions
- **Treating the top bit as just a minus sign.** In two's complement 10000101 is -123, not -5; that reading belongs to sign-magnitude.
- **Inverting without adding one.** Inverting alone gives one's complement, which is -x - 1.
- **Expecting a symmetric range.** 8 bits go from -128 to 127; -128 has no positive counterpart, and negating it gives -128 again.
- **Ignoring overflow.** 127 + 1 wraps to -128 in 8 bits instead of raising an error in C and C++ fixed-width types.

## Builds On
Binary Numbers: a two's-complement pattern is a binary number in which only the top position changes its weight, from +2^(n-1) to -2^(n-1).

## Leads To
In this demo pack Two's Complement is a leaf concept. In a full course it leads on to integer overflow, arithmetic shifts and floating-point representation.

## Check Yourself
**Q1.** What range does a 16-bit two's-complement integer cover?
**A1.** -32768 to 32767.
**Q2.** What is -1 in 8-bit two's complement?
**A2.** 11111111.
**Q3.** How do you negate a two's-complement number?
**A3.** Invert every bit and add one.
