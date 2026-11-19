---
id: strings
name: "Strings"
cluster: foundations
reviewed: false
sources:
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 and Chapter 5 (Strings)"
  - "CLRS, Chapter 32 (String Matching), introductory material on strings as arrays of characters"
---

## Overview
A string is a sequence of characters such as letters, digits and punctuation. Under the hood a string is an array of character codes, so most of what you know about arrays carries over: indexes start at zero, you can read the character at any position in constant time, and out-of-range indexes are errors. Strings add their own rules, especially around immutability, slicing, comparison and the cost of building them piece by piece.

## Intuition
Think of a string as a row of Scrabble tiles on a shelf. You can look at the tile in any slot, read a run of tiles, or compare two shelves tile by tile. In many languages the tiles are glued down: to "change" one letter you must build a brand new row. That is why repeatedly gluing small words onto the end of a long row feels slow, because each new row copies all the old tiles.

## How It Works
Each character has a numeric code. ASCII covers 128 characters such as English letters and digits, while Unicode covers characters from every language, and Python strings are sequences of Unicode characters. The functions `ord` and `chr` convert between a character and its code, so `ord('a')` is 97 and `chr(98)` is 'b'. Letters have consecutive codes, which is why `ord(c) - ord('a')` maps a lowercase letter to 0 to 25, a trick used in counting and hashing problems.

Indexing reads one character: `s[0]` is the first and `s[-1]` the last in Python. Slicing `s[a:b]` returns a new string from index a up to but excluding b. Comparison with `==` checks every character, and ordering comparisons use the character codes, so "apple" is less than "banana".

In Python, Java and C# strings are immutable: `s[0] = 'x'` raises a TypeError. Operations such as `upper()` or slicing return new strings. C++ std::string is mutable, so individual characters can be changed in place.

Because strings cannot change, concatenating inside a loop creates a new string each time and copies all characters so far. Building a result of length n by adding one character at a time can therefore take quadratic time. The usual fix in Python is to collect pieces in a list and call `"".join(pieces)` once. Common tasks include reversing, counting characters with a dictionary or an array of 26 counters, and checking palindromes with two indexes moving toward each other.

## Worked Example
Check whether "racecar" is a palindrome by comparing from both ends.

Set left = 0 and right = 6. Compare s[0] = 'r' with s[6] = 'r': equal. Move to left = 1, right = 5: 'a' and 'a': equal. Left = 2, right = 4: 'c' and 'c': equal. Left = 3, right = 3: the pointers meet in the middle, so the loop ends and the word is a palindrome. For "racecat" the first comparison would be 'r' versus 't' and the answer would be false immediately.

To count letters in "banana", keep 26 counters. For each character, compute index = ord(c) - ord('a') and increase that counter. The counter for 'a' ends at 3, for 'n' at 2 and for 'b' at 1.

## Code
```python
s = "hello"
assert s[0] == "h" and s[-1] == "o" and s[1:4] == "ell"

# Strings are immutable in Python.
try:
    s[0] = "J"
except TypeError:
    pass
else:
    raise AssertionError("strings should be immutable")

assert ord("a") == 97 and chr(98) == "b"
assert ord("d") - ord("a") == 3          # letter -> 0..25

def is_palindrome(text):
    left, right = 0, len(text) - 1
    while left < right:
        if text[left] != text[right]:
            return False
        left += 1
        right -= 1
    return True

assert is_palindrome("racecar") and not is_palindrome("racecat")

def count_letters(text):
    counts = [0] * 26
    for ch in text:
        counts[ord(ch) - ord("a")] += 1
    return counts

c = count_letters("banana")
assert c[0] == 3 and c[13] == 2 and c[1] == 1

# Build a string efficiently: collect pieces, join once.
pieces = [str(i) for i in range(5)]
assert "-".join(pieces) == "0-1-2-3-4"
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <string>

bool isPalindrome(const std::string& text) {
    if (text.empty()) return true;
    std::size_t left = 0, right = text.size() - 1;
    while (left < right) {
        if (text[left] != text[right]) return false;
        ++left;
        --right;
    }
    return true;
}

int main() {
    std::string s = "hello";
    assert(s[0] == 'h' && s.back() == 'o' && s.substr(1, 3) == "ell");

    s[0] = 'J';  // std::string is mutable, unlike Python strings
    assert(s == "Jello");

    assert(isPalindrome("racecar") && !isPalindrome("racecat"));

    int counts[26] = {0};
    for (char ch : std::string("banana")) ++counts[ch - 'a'];
    assert(counts[0] == 3 && counts['n' - 'a'] == 2 && counts[1] == 1);

    std::string r = "abc";
    std::reverse(r.begin(), r.end());
    assert(r == "cba");

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Reading a character by index is O(1). Comparing two strings of length n takes O(n) in the worst case, because every character may need checking. Slicing a substring of length k copies k characters, so it costs O(k). Concatenating two strings costs time proportional to the combined length, which means appending one character at a time in a loop over n characters costs O(n squared) in total for immutable strings, while joining a list of pieces once costs O(n). Storing a string of n characters needs O(n) space.

## Common Mistakes & Misconceptions
Students see `TypeError: 'str' object does not support item assignment` and wonder why a letter cannot be changed. They write slow code that builds long strings with `+=` in a loop and then find it takes ages on large input. Off-by-one errors in slicing are frequent because the end index is excluded. Others compare strings with `is` instead of `==`, which can give surprising results, and forget that comparison is case-sensitive so "Apple" is not equal to "apple". Mixing up characters and their codes, for instance adding 1 to a letter instead of to its `ord` value, raises type errors.

## Builds On
This concept builds on Arrays: a string is an array of characters, so indexing, bounds, traversal with loops and the cost of shifting all apply unchanged. The palindrome and counting examples are array algorithms (two indexes, an array of counters) applied to character data.

## Leads To
Tries store sets of strings by shared prefixes, and string matching algorithms such as KMP and Rabin-Karp find a pattern inside a text. Hash functions often start from a string's characters, and sliding window problems are frequently posed on strings.

## Check Yourself
**Q1.** Why does `s[0] = "x"` fail in Python?
**A1.** Python strings are immutable, so individual characters cannot be assigned.
**Q2.** What does ord("c") - ord("a") equal?
**A2.** 2.
**Q3.** Why is building a long string with += in a loop slow?
**A3.** Each concatenation copies all existing characters, giving quadratic total time.
