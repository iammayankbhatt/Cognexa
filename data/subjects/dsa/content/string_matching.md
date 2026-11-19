---
id: string_matching
name: "String Matching (KMP, Rabin-Karp)"
cluster: paradigms
reviewed: false
sources:
  - "CLRS, Chapter 32 (String Matching), Sections 32.1, 32.2 and 32.4"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 5.3 (Substring Search)"
---

## Overview
String matching finds every position where a pattern P of length m occurs inside a text T of length n. The naive method tries every starting position and compares character by character, which costs O(nm) in the worst case. Two classic algorithms do better. Knuth-Morris-Pratt (KMP) precomputes, for each prefix of the pattern, the longest proper prefix that is also a suffix, so after a mismatch it never re-examines text characters, giving O(n + m) in the worst case. Rabin-Karp compares a rolling hash of each text window with the hash of the pattern and only checks characters when the hashes match, giving O(n + m) expected time and extending neatly to searching for many patterns at once. These ideas power text editors' find, grep, plagiarism detection and DNA search.

## Intuition
Suppose you are looking for "ABABC" in a long line and you have matched "ABAB" when the next character is wrong. The naive approach shifts by one and starts comparing from scratch. But you already know the last characters you read were "AB", which is also how the pattern begins, so you can keep that progress and continue from the third pattern character. KMP writes down this "how much can I keep" information in advance. Rabin-Karp takes a different shortcut: instead of comparing whole windows letter by letter, it compares a fingerprint (a number) of each window, which can be updated in constant time as the window slides.

## How It Works
Naive search. For each start s from 0 to n - m, compare P with T[s : s + m] character by character, stopping at the first mismatch. Worst case, such as T = "AAAA...A" and P = "AAA...AB", costs about nm comparisons.

KMP failure function. For the pattern build lps[i] = the length of the longest proper prefix of P[0..i] that is also a suffix of P[0..i]. For "ABABCABAB" this gives [0, 0, 1, 2, 0, 1, 2, 3, 4]. It is built in O(m) using the same matching idea on the pattern against itself.

KMP search. Keep j = the number of pattern characters currently matched. For each text character c: while j > 0 and c != P[j], set j = lps[j - 1] (fall back to the next shorter prefix that is still matched). If c == P[j], increase j. If j == m, report a match at position i - m + 1 and set j = lps[m - 1] to continue looking for overlapping matches. The text pointer never moves backwards, and the total number of fallbacks is bounded by the number of advances, so the search is O(n).

Rabin-Karp. Treat a string as a number in base b (for example 256) modulo a large prime q. Compute the hash of P and of the first text window. Sliding the window one step removes the leading character and adds a new trailing one: h = ((h - T[s] * b^(m-1)) * b + T[s + m]) mod q, which is O(1). When the window hash equals the pattern hash, compare the characters to rule out a collision (a spurious hit). With a good modulus, collisions are rare and the expected time is O(n + m); in the worst case every window collides and it degrades to O(nm).

Choosing. KMP has a guaranteed linear bound and no hashing. Rabin-Karp is simple, handles many patterns of the same length by putting their hashes in a set, and generalises to two-dimensional matching. Library functions such as Python's str.find use tuned variants of these ideas.

## Worked Example
Build the KMP table for P = "ABABCABAB". lps[0] = 0. At i = 1 "AB" has no proper border, 0. At i = 2 "ABA" has border "A", 1. At i = 3 "ABAB" has border "AB", 2. At i = 4 "ABABC" has none, 0. Then "ABABCA" gives 1, "ABABCAB" gives 2, "ABABCABA" gives 3 and "ABABCABAB" gives 4.

```
index   0 1 2 3 4 5 6 7 8
P       A B A B C A B A B
lps     0 0 1 2 0 1 2 3 4
```

Search T = "ABABDABACDABABCABAB". The first four characters match "ABAB" (j = 4); T[4] = D does not match P[4] = C, so j falls to lps[3] = 2, then D does not match P[2] = A, so j falls to lps[1] = 0, and D does not match P[0], so move on. The text pointer never goes back. Later, starting at text index 10, all nine characters match, so KMP reports one occurrence at index 10. For Rabin-Karp with the same input, only windows whose hash equals the pattern's hash are compared letter by letter.

## Code
```python
def naive_search(text, pattern):
    n, m = len(text), len(pattern)
    return [s for s in range(n - m + 1) if text[s:s + m] == pattern]


def build_lps(p):
    lps, k = [0] * len(p), 0                     # k: length of the current border
    for i in range(1, len(p)):
        while k > 0 and p[i] != p[k]:
            k = lps[k - 1]
        if p[i] == p[k]:
            k += 1
        lps[i] = k
    return lps


def kmp_search(text, pattern):
    if not pattern:
        return list(range(len(text) + 1))
    lps, j, out = build_lps(pattern), 0, []
    for i, c in enumerate(text):
        while j > 0 and c != pattern[j]:
            j = lps[j - 1]                         # fall back without moving i backwards
        if c == pattern[j]:
            j += 1
        if j == len(pattern):
            out.append(i - j + 1)
            j = lps[j - 1]                         # allow overlapping matches
    return out


def rabin_karp(text, pattern, base=256, mod=1_000_000_007):
    n, m = len(text), len(pattern)
    if m == 0 or m > n:
        return [] if m else list(range(n + 1))
    high = pow(base, m - 1, mod)
    hp = ht = 0
    for i in range(m):
        hp = (hp * base + ord(pattern[i])) % mod
        ht = (ht * base + ord(text[i])) % mod
    out = []
    for s in range(n - m + 1):
        if hp == ht and text[s:s + m] == pattern:  # verify to rule out a collision
            out.append(s)
        if s < n - m:                              # roll the window by one character
            ht = ((ht - ord(text[s]) * high) * base + ord(text[s + m])) % mod
    return out


assert build_lps("ABABCABAB") == [0, 0, 1, 2, 0, 1, 2, 3, 4]
assert build_lps("AAAA") == [0, 1, 2, 3]
text, pat = "ABABDABACDABABCABAB", "ABABCABAB"
assert kmp_search(text, pat) == [10] == rabin_karp(text, pat) == naive_search(text, pat)
assert kmp_search("AAAAA", "AA") == [0, 1, 2, 3]  # overlapping matches
assert rabin_karp("AAAAA", "AA") == [0, 1, 2, 3]
assert kmp_search("abc", "d") == [] and rabin_karp("ab", "abc") == []

import random

random.seed(13)
for _ in range(300):
    t = "".join(random.choice("ab") for _ in range(random.randint(0, 30)))
    p = "".join(random.choice("ab") for _ in range(random.randint(1, 4)))
    expected = naive_search(t, p)
    assert kmp_search(t, p) == expected and rabin_karp(t, p, mod=101) == expected   # tiny mod forces collisions
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

std::vector<int> buildLps(const std::string& p) {
    std::vector<int> lps(p.size(), 0);
    int k = 0;
    for (std::size_t i = 1; i < p.size(); ++i) {
        while (k > 0 && p[i] != p[k]) k = lps[k - 1];
        if (p[i] == p[k]) ++k;
        lps[i] = k;
    }
    return lps;
}

std::vector<int> kmpSearch(const std::string& text, const std::string& pattern) {
    std::vector<int> out;
    if (pattern.empty()) return out;
    std::vector<int> lps = buildLps(pattern);
    int j = 0, m = static_cast<int>(pattern.size());
    for (int i = 0; i < static_cast<int>(text.size()); ++i) {
        while (j > 0 && text[i] != pattern[j]) j = lps[j - 1];
        if (text[i] == pattern[j]) ++j;
        if (j == m) {
            out.push_back(i - m + 1);
            j = lps[j - 1];
        }
    }
    return out;
}

int main() {
    assert((buildLps("ABABCABAB") == std::vector<int>{0, 0, 1, 2, 0, 1, 2, 3, 4}));
    assert((kmpSearch("ABABDABACDABABCABAB", "ABABCABAB") == std::vector<int>{10}));
    assert((kmpSearch("AAAAA", "AA") == std::vector<int>{0, 1, 2, 3}));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Naive search is O(nm) in the worst case, though often close to O(n) on natural text. KMP builds its table in O(m) and searches in O(n), so O(n + m) time in the worst case, with O(m) extra space. Rabin-Karp takes O(m) to hash the pattern and O(n) to roll through the text, plus O(m) per verified hit, so O(n + m) expected time and O(nm) in the worst case when many windows collide; its extra space is O(1) for one pattern. Searching for k patterns of equal length with Rabin-Karp costs O(n + km) expected time using a set of hashes.

## Common Mistakes & Misconceptions
In KMP the classic bug is resetting j to 0 on every mismatch instead of following lps, which loses matches such as "ABABC" inside "ABABABC". Forgetting to set j = lps[m - 1] after a full match misses overlapping occurrences, so "AA" in "AAAA" is reported twice instead of three times. Off-by-one errors in the failure table (using the length of a border versus the index of its last character) produce an infinite loop or IndexError. In Rabin-Karp, skipping the character check after a hash match reports false positives, and forgetting to take the modulus (or getting a negative value in languages where % can be negative) breaks the rolling update. Students also believe hashing guarantees linear time; it is linear only in expectation. Another misconception is that str.find or "in" is always naive; real libraries use optimised algorithms.

## Builds On
This concept builds on Strings, because matching works on character indexing, substrings, and comparisons of string slices, and understanding that comparing two strings of length m costs O(m) explains why the naive method is O(nm). It also builds on Hash Functions: Rabin-Karp relies on a polynomial hash modulo a prime, on the fact that equal strings have equal hashes while unequal strings rarely collide, and on the need to verify a match when hashes collide, exactly the ideas behind hash tables.

## Leads To
String matching leads to the Aho-Corasick algorithm (many patterns at once, built on a trie with failure links), the Z-algorithm, suffix arrays and suffix trees for repeated queries on the same text, and the Boyer-Moore family used in practical search tools. Rolling hashes are also used for duplicate detection, plagiarism checkers and the content-defined chunking in backup systems.

## Check Yourself
**Q1.** What does the KMP failure (lps) table store?
**A1.** For each prefix of the pattern, the length of its longest proper prefix that is also a suffix.
**Q2.** Why must Rabin-Karp compare characters when hashes match?
**A2.** Because different strings can have the same hash (a collision), so a hash match is only a candidate.
**Q3.** What is the worst-case time of KMP for a text of length n and pattern of length m?
**A3.** O(n + m).
