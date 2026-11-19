---
id: hash_functions
name: "Hash Functions"
cluster: searching_hashing
reviewed: false
sources:
  - "CLRS, Section 11.3 (Hash functions)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.4 (Hash tables: hash functions)"
---

## Overview
A hash function takes a key of any size, such as a string or a record, and turns it into a fixed-size number called a hash value or hash code. Hash tables use that number to decide where to store and find the key, so the function must be fast, always return the same value for equal keys, and spread different keys evenly. A poor hash function, one that sends many keys to the same value, makes a hash table slow regardless of how it is otherwise built.

## Intuition
Think of a post office sorting letters into 100 pigeonholes by a rule applied to the address. A good rule sends roughly the same number of letters to every pigeonhole, so no single hole overflows and finding a letter is quick. A bad rule, such as "sort by the first letter of the street", piles most mail into a few holes because many streets start with the same letters. The hash function is the sorting rule, and the table positions are the pigeonholes.

## How It Works
A hash function must be deterministic: equal keys must always produce equal hash values, within one run of the program. It should be uniform, spreading keys evenly over the output range, and fast to compute. Unequal keys may collide (share a hash value), which is unavoidable because there are far more possible keys than hash values; a table needs a plan for collisions, covered in the next concept.

To turn a hash code into a table index, take the remainder modulo the table size m: `index = hash(key) % m`. Because of this step, the quality of the low-order behaviour matters. If m is a power of two and the hash code has patterns in its low bits, many keys collide; choosing a prime table size or mixing bits well avoids this.

For strings, a standard approach is a polynomial rolling hash: `h = (h * 31 + code(c)) % m` for each character c, which makes the result depend on every character and on its position, so "ab" and "ba" hash differently. A bad alternative is simply summing the character codes, which makes every anagram collide. For integers a simple multiplicative or modular scheme works; for compound keys, combine the hashes of the parts.

Hash codes are only meaningful for immutable keys. In Python, objects used as dictionary keys must define `__hash__` consistently with `__eq__`: if `a == b` then `hash(a) == hash(b)`. Lists are unhashable because they are mutable, and changing a key after insertion would make it unfindable. Python also randomises string hashes between program runs for security, so never persist them or depend on their values.

Cryptographic hash functions such as SHA-256 add extra goals: it is infeasible to find two inputs with the same hash or to reverse the hash. They are much slower and are used for integrity checks and passwords, not for ordinary hash tables.

## Worked Example
Hash the strings "ab" and "ba" into a table of size 100 with `h = (h * 31 + code) % 100` starting from 0.

For "ab": a has code 97, so h = 97. Then b has code 98: 97 * 31 + 98 = 3105, and 3105 % 100 = 5. For "ba": b gives h = 98, then a gives 98 * 31 + 97 = 3135, and 3135 % 100 = 35. The two anagrams land in different slots, 5 and 35. A sum-of-codes hash would give 195 % 100 = 95 for both, a guaranteed collision for every anagram.

Now consider 1,000 random keys into 100 slots with a good hash: each slot gets about 10 keys on average. With a bad hash that always returns the length of the key, every key of the same length lands in the same slot, and lookups degrade to scanning a long list.

## Code
```python
def poly_hash(text, m):
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) % m
    return h


def sum_hash(text, m):
    return sum(ord(ch) for ch in text) % m


assert poly_hash("ab", 100) == 5
assert poly_hash("ba", 100) == 35
assert sum_hash("ab", 100) == sum_hash("ba", 100) == 95     # every anagram collides

# Equal keys always give equal hash values (determinism).
assert poly_hash("hello", 97) == poly_hash("hello", 97)

# Compare how evenly two hash functions spread 2000 words over 50 buckets.
import random
import string

random.seed(5)
words = ["".join(random.choice(string.ascii_lowercase) for _ in range(6)) for _ in range(2000)]


def worst_bucket(hash_fn, m=50):
    buckets = [0] * m
    for w in words:
        buckets[hash_fn(w, m)] += 1
    return max(buckets)


assert worst_bucket(poly_hash) < worst_bucket(sum_hash)     # the polynomial hash spreads better

# Python's dict requires hashable keys: lists are mutable and therefore unhashable.
try:
    {[1, 2]: "x"}
except TypeError:
    pass
else:
    raise AssertionError("lists must not be usable as dict keys")
assert hash((1, 2)) == hash((1, 2))                         # tuples of immutable values are hashable
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

unsigned polyHash(const std::string& text, unsigned m) {
    unsigned long long h = 0;
    for (char ch : text) h = (h * 31 + static_cast<unsigned char>(ch)) % m;
    return static_cast<unsigned>(h);
}

unsigned sumHash(const std::string& text, unsigned m) {
    unsigned long long total = 0;
    for (char ch : text) total += static_cast<unsigned char>(ch);
    return static_cast<unsigned>(total % m);
}

int main() {
    assert(polyHash("ab", 100) == 5);
    assert(polyHash("ba", 100) == 35);
    assert(sumHash("ab", 100) == 95 && sumHash("ba", 100) == 95);  // anagrams collide

    assert(polyHash("hello", 97) == polyHash("hello", 97));  // deterministic

    std::vector<int> buckets(50, 0);
    for (int i = 0; i < 1000; ++i) ++buckets[polyHash(std::to_string(i * 7919), 50)];
    assert(*std::max_element(buckets.begin(), buckets.end()) < 60);  // roughly even spread

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Computing a hash of a string of length L takes O(L) time, since every character is processed, and O(1) extra space. Hashing an integer is O(1). Converting the hash to an index with the modulo operator is O(1). For a hash table with a good function, the expected cost of lookup, insert and delete is O(1) plus the cost of hashing the key. With a poor function that crowds keys into few slots, operations degrade to O(n), the cost of scanning all colliding keys. Cryptographic hashes cost considerably more per byte than the simple ones used for tables.

## Common Mistakes & Misconceptions
A frequent symptom is a dictionary or hash set that becomes very slow with certain data, caused by many keys sharing hash values, for example a hash that sums character codes so all anagrams collide. Students think collisions can be avoided entirely; with more possible keys than slots they cannot, so only their number can be controlled. Using a mutable object, such as a Python list, as a key raises `TypeError: unhashable type: 'list'`, or in C++ a key whose fields change after insertion becomes impossible to find. Another mistake is overriding equality without overriding the hash (or vice versa), violating the rule that equal keys must hash equally. Relying on Python's string hashes staying the same across runs is wrong, and treating a cryptographic hash as a general-purpose table hash wastes time.

## Builds On
This concept builds on Arrays: the hash value is reduced to an array index with a modulo, and the table that uses it is an array indexed by that position, which is why lookup is a single array access once the index is known. It builds on Discrete Math Basics because modular arithmetic is the operation that maps large hash values onto a small range, and ideas about remainders and powers explain why table size and multipliers matter.

## Leads To
Hash tables use hash functions to place and find keys, handling collisions by chaining or open addressing. String matching algorithms such as Rabin-Karp use rolling hashes, and hash sets and maps in everyday code depend on keys having good, consistent hash values.

## Check Yourself
**Q1.** What must be true of the hash values of two equal keys?
**A1.** They must be equal, because the hash function is deterministic.
**Q2.** Why is summing character codes a poor string hash?
**A2.** It ignores order, so every anagram of a word collides, creating long collision chains.
**Q3.** Why can a Python list not be a dictionary key?
**A3.** It is mutable, so its hash could change after insertion; Python refuses it with TypeError: unhashable type.
