---
id: hexadecimal
name: "Hexadecimal"
cluster: representation
reviewed: false
sources:
  - "Bryant and O'Hallaron, Computer Systems: A Programmer's Perspective 3rd ed., Section 2.1.1 (Hexadecimal Notation)"
  - "Petzold, Code: The Hidden Language of Computer Hardware and Software, chapter on hexadecimal"
---

## Overview
Hexadecimal, usually shortened to hex, is the base-16 number system. It uses sixteen digits: 0 to 9 for the values zero to nine and the letters A to F for ten to fifteen. Its value to programmers comes from one fact: sixteen is 2^4, so every hex digit corresponds to exactly four bits. A byte is always exactly two hex digits, which makes hex a compact and readable way to write binary data such as memory addresses, colour codes and bit masks.

## Intuition
Long binary strings are hard to read: 1101011010110011 is easy to misread by one digit. Split it into groups of four from the right, 1101 0110 1011 0011, and replace each group with one symbol: D, 6, B, 3. The result, D6B3, carries exactly the same information in a quarter of the length, and you can translate back group by group without any arithmetic on the whole number. Decimal has no such shortcut, because ten is not a power of two.

## How It Works
Each position in a hex number is worth a power of 16: 1, 16, 256, 4096 and so on from the right. So hex 2F is 2 x 16 + 15 = 47.

**Binary to hex.** Pad the binary number on the left to a multiple of four digits, split it into groups of four (nibbles) and convert each group: 0000 is 0, 1001 is 9, 1010 is A, 1111 is F.

**Hex to binary.** Replace every hex digit with its four-bit pattern, keeping leading zeros inside each group: 3A becomes 0011 1010.

**Decimal to hex.** Divide repeatedly by 16 and read the remainders from last to first, as in binary conversion but with base 16.

In code, Python writes hex literals as `0x2F`, `hex(47)` returns `'0x2f'`, and `int("2F", 16)` parses one. Hex digits are case-insensitive: 0x2f and 0x2F are the same number.

## Worked Example
A web colour is written #1E90FF. Each pair of hex digits is one byte for red, green and blue.

1. Red: 1E = 1 x 16 + 14 = 30.
2. Green: 90 = 9 x 16 + 0 = 144.
3. Blue: FF = 15 x 16 + 15 = 255.

So the colour is (30, 144, 255). In binary, 1E is 0001 1110, read straight from the two nibbles 1 and E. Converting decimal 500 to hex: 500 = 31 x 16 + 4, then 31 = 1 x 16 + 15, then 1 = 0 x 16 + 1; reading the remainders 1, 15, 4 gives 1F4.

## Code
```python
NIBBLES = "0123456789ABCDEF"

def bin_to_hex(bits: str) -> str:
    bits = bits.zfill((len(bits) + 3) // 4 * 4)  # pad to whole nibbles
    return "".join(NIBBLES[int(bits[i:i + 4], 2)] for i in range(0, len(bits), 4))

def hex_to_bin(h: str) -> str:
    return "".join(format(int(d, 16), "04b") for d in h)

assert bin_to_hex("1101011010110011") == "D6B3"
assert hex_to_bin("3A") == "00111010"
assert int("2F", 16) == 47 and int("1F4", 16) == 500 and hex(500) == "0x1f4"
assert [int(p, 16) for p in ("1E", "90", "FF")] == [30, 144, 255]
for n in range(4096):
    assert int(bin_to_hex(bin(n)[2:]), 16) == n
    assert int(hex_to_bin(format(n, "X")), 2) == n
print(bin_to_hex("1101011010110011"))
```

```cpp
#include <cassert>
#include <cstdio>
#include <iostream>
#include <string>

std::string to_hex(unsigned n) {
    const char* digits = "0123456789ABCDEF";
    if (n == 0) return "0";
    std::string s;
    while (n > 0) { s.insert(s.begin(), digits[n % 16]); n /= 16; }
    return s;
}

int main() {
    assert(to_hex(500) == "1F4" && to_hex(47) == "2F" && to_hex(255) == "FF");
    assert(0x2F == 47 && 0xff == 255);
    unsigned r = 0, g = 0, b = 0;
    std::sscanf("1E90FF", "%2x%2x%2x", &r, &g, &b);
    assert(r == 30 && g == 144 && b == 255);
    std::cout << to_hex(500) << "\n";
    return 0;
}
```

## Complexity
Binary to hex and back is a group-by-group table lookup, so it takes O(k) time for k bits with no carrying across groups. Converting a decimal value n to hex needs O(log n) divisions by 16, a quarter as many digits as binary.

## Common Mistakes & Misconceptions
- **Grouping from the left.** Split binary into nibbles from the right; pad on the left if the length is not a multiple of four.
- **Dropping zeros inside a nibble.** Hex 3A is 0011 1010, not 11 1010 squeezed together; each digit is always four bits.
- **Thinking hex digits above 9 are errors.** A to F are ordinary digits worth 10 to 15.
- **Reading 0x10 as ten.** Hex 10 is sixteen.

## Builds On
Binary Numbers: hex is a shorthand for binary in which each digit stands for four binary digits, and its place values are powers of 16 = 2^4.

## Leads To
Hex is how bit masks are usually written in code, for example `0xFF` or `0x0F`, so it pairs naturally with Bitwise Operations. In this demo pack no concept requires hex as a prerequisite.

## Check Yourself
**Q1.** What is hex FF in decimal?
**A1.** 255.
**Q2.** Write binary 10111100 in hex.
**A2.** BC (1011 is B, 1100 is C).
**Q3.** How many hex digits does one byte need?
**A3.** Exactly two, because each hex digit is four bits.
