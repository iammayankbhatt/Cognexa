---
id: binary_numbers
name: "Binary Numbers"
cluster: representation
reviewed: false
sources:
  - "Bryant and O'Hallaron, Computer Systems: A Programmer's Perspective 3rd ed., Section 2.1.2 and 2.2 (Integer Representations)"
  - "Knuth, The Art of Computer Programming Vol. 2, Section 4.1 (Positional Number Systems)"
---

## Overview
Binary is the base-2 positional number system. Just as each position in a decimal number is worth a power of ten, each position in a binary number is worth a power of two: 1, 2, 4, 8, 16 and so on, from right to left. A binary number is the sum of the place values whose digit is 1. Because computers store bits, binary is the natural way to write the numbers they hold, and converting between binary and decimal is a basic skill for reading memory, masks and bit patterns.

## Intuition
Decimal 305 means 3 hundreds, 0 tens and 5 ones. Binary 1101 means 1 eight, 1 four, 0 twos and 1 one, which is 8 + 4 + 1 = 13. The only difference is the base: decimal has ten digits and multiplies by ten per position, binary has two digits and doubles per position. Counting in binary works like an odometer with only 0 and 1 on each wheel: 0, 1, 10, 11, 100, 101, and so on. Every time a wheel passes 1 it rolls back to 0 and carries into the next position.

## How It Works
**Binary to decimal.** Number the positions from 0 on the right. Add 2^i for every position i that holds a 1. Equivalently, read left to right keeping a running total: double it, then add the next digit (Horner's rule).

**Decimal to binary.** Repeatedly divide by 2 and record the remainders. The remainders, read from last to first, are the binary digits. Each remainder is the lowest bit of the current number, and dividing by two shifts the remaining bits one place to the right.

In code, Python writes binary literals with the prefix `0b` (so `0b1101 == 13`), `bin(13)` returns the string `'0b1101'`, and `int("1101", 2)` parses one. The number of binary digits of a positive n is floor(log2 n) + 1.

## Worked Example
Convert 45 to binary by repeated division:

| Step | n | n // 2 | remainder |
|---|---|---|---|
| 1 | 45 | 22 | 1 |
| 2 | 22 | 11 | 0 |
| 3 | 11 | 5 | 1 |
| 4 | 5 | 2 | 1 |
| 5 | 2 | 1 | 0 |
| 6 | 1 | 0 | 1 |

Reading the remainders from the last step to the first gives 101101. Check it the other way: 32 + 8 + 4 + 1 = 45. With Horner's rule, the running total for 1, 0, 1, 1, 0, 1 is 1, 2, 5, 11, 22, 45.

## Code
```python
def to_binary(n: int) -> str:
    if n == 0:
        return "0"
    digits = []
    while n > 0:
        digits.append(str(n % 2))
        n //= 2
    return "".join(reversed(digits))

def from_binary(s: str) -> int:
    total = 0
    for ch in s:
        total = total * 2 + int(ch)  # Horner's rule
    return total

assert to_binary(45) == "101101" and from_binary("101101") == 45
assert to_binary(0) == "0" and to_binary(13) == "1101"
for n in range(1000):
    assert from_binary(to_binary(n)) == n
    assert to_binary(n) == bin(n)[2:]
    assert int(to_binary(n), 2) == n
assert len(to_binary(1000)) == 1000 .bit_length() == 10
print(to_binary(45))
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <string>

std::string to_binary(unsigned n) {
    if (n == 0) return "0";
    std::string s;
    while (n > 0) { s.push_back(char('0' + n % 2)); n /= 2; }
    std::reverse(s.begin(), s.end());
    return s;
}

unsigned from_binary(const std::string& s) {
    unsigned total = 0;
    for (char c : s) total = total * 2 + unsigned(c - '0');
    return total;
}

int main() {
    assert(to_binary(45) == "101101" && from_binary("101101") == 45);
    for (unsigned n = 0; n < 1000; ++n) assert(from_binary(to_binary(n)) == n);
    std::cout << to_binary(45) << "\n";
    return 0;
}
```

## Complexity
Converting a number n either way touches each binary digit once, and n has floor(log2 n) + 1 digits, so both directions take O(log n) steps. That is also why binary needs about 3.3 times as many digits as decimal: log2(10) is roughly 3.32.

## Common Mistakes & Misconceptions
- **Reading remainders in the wrong order.** The first remainder is the lowest bit; the binary number is the remainders read from last to first.
- **Numbering positions from 1.** The rightmost position is worth 2^0 = 1, not 2.
- **Treating 10 in binary as ten.** Binary 10 is two; always note the base when it is not obvious.
- **Forgetting that `bin()` adds a prefix.** `bin(5)` is `'0b101'`, so strip the first two characters when you need just the digits.

## Builds On
Bits & Bytes: a binary number is a bit pattern read as a sum of powers of two, so the counting rules for bits explain why k binary digits cover the values 0 to 2^k - 1.

## Leads To
Hexadecimal groups binary digits in fours for a compact notation; Two's Complement extends binary to negative numbers; Bitwise Operations act on the individual binary digits.

## Check Yourself
**Q1.** What is binary 10110 in decimal?
**A1.** 16 + 4 + 2 = 22.
**Q2.** What is 37 in binary?
**A2.** 100101 (32 + 4 + 1).
**Q3.** How many binary digits does 64 have?
**A3.** 7, because 64 is 1000000.
