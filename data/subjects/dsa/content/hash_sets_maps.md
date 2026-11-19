---
id: hash_sets_maps
name: "Hash Sets & Maps in Practice"
cluster: searching_hashing
reviewed: false
sources:
  - "Python documentation, Data Structures: Sets and Dictionaries"
  - "CLRS, Chapter 11 and Sedgewick and Wayne, Algorithms 4th ed., Section 3.5 (Applications of sets and maps)"
---

## Overview
Hash sets and hash maps (Python's `set` and `dict`, Java's HashSet and HashMap, C++'s `unordered_set` and `unordered_map`) are the hash tables you use every day. A set stores unique items and answers "is this in the collection?" in expected constant time. A map stores key-value pairs and returns the value for a key in expected constant time. Knowing a handful of patterns, such as counting, grouping, deduplicating and the one-pass two-sum, solves a large share of practical problems that would otherwise need nested loops.

## Intuition
A set is a guest list at the door: the bouncer can check in an instant whether a name is on it, without reading the list from top to bottom. A map is a phone book where you look up a name and get a number straight away. In both cases the speed comes from not searching: the name itself tells the lookup where to go.

## How It Works
A set supports add, remove, and membership test (`x in s`), each expected O(1). Duplicates are ignored, so converting a list to a set removes duplicates, though the order is not guaranteed in general. Sets also support union, intersection and difference, handy for comparing collections.

A map (dictionary) supports `d[key] = value`, `d[key]`, `d.get(key, default)`, `del d[key]` and iteration over keys, values or items. Reading a missing key with `d[key]` raises `KeyError`, while `d.get(key, default)` returns a default instead. Keys must be hashable and unique; setting the same key again replaces its value. Since Python 3.7 dictionaries preserve insertion order.

Core patterns: counting frequency (`counts[x] = counts.get(x, 0) + 1`, or `collections.Counter`); grouping items by a key (`groups.setdefault(key, []).append(item)` or `collections.defaultdict(list)`); detecting duplicates (add each item to a set and stop when it is already there); and the one-pass two-sum: for each number x, check whether `target - x` is already in a dictionary of earlier numbers, replacing an O(n squared) pair search with O(n). Another is caching results (memoization) in a dictionary keyed by the arguments.

Costs and traps: expected O(1) hides a worst case of O(n) with terrible hashes; keys must be immutable (use tuples, not lists); iteration order of a set is arbitrary; modifying a dictionary while iterating over it raises `RuntimeError`; and each entry uses far more memory than an array element, so a table of small integers is better served by a list. Floating-point keys are risky because of rounding.

In C++, `unordered_map` is the hash version, while `map` is a balanced tree with O(log n) operations and sorted keys. Choose hashing for speed and a tree when you need ordering or range queries.

## Worked Example
Count word frequencies in ["a", "b", "a", "c", "a", "b"]. Start with an empty dictionary. After the first a: {a: 1}; after b: {a: 1, b: 1}; after the second a: {a: 2, b: 1}; after c: {a: 2, b: 1, c: 1}; after the third a: {a: 3, b: 1, c: 1}; after the second b: {a: 3, b: 2, c: 1}. The set of distinct words has size 3.

Two-sum on [2, 7, 11, 15] with target 9: scan 2 (look for 7, not seen, store 2 at index 0); scan 7 (look for 2, found at index 0), so the answer is indexes 0 and 1. Only one pass was needed.

Group the words ["eat", "tea", "tan", "ate", "nat", "bat"] by their sorted letters: "eat", "tea" and "ate" all have key "aet"; "tan" and "nat" have "ant"; "bat" has "abt". The map has three groups.

## Code
```python
from collections import Counter, defaultdict


def word_counts(words):
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts


def has_duplicate(items):
    seen = set()
    for x in items:
        if x in seen:
            return True
        seen.add(x)
    return False


def two_sum(values, target):
    index_of = {}                              # value -> index of earlier occurrence
    for i, x in enumerate(values):
        need = target - x
        if need in index_of:
            return index_of[need], i
        index_of[x] = i
    return None


def group_anagrams(words):
    groups = defaultdict(list)
    for w in words:
        groups["".join(sorted(w))].append(w)
    return list(groups.values())


counts = word_counts(["a", "b", "a", "c", "a", "b"])
assert counts == {"a": 3, "b": 2, "c": 1}
assert counts == dict(Counter(["a", "b", "a", "c", "a", "b"]))
assert has_duplicate([1, 2, 3, 2]) and not has_duplicate([1, 2, 3])
assert two_sum([2, 7, 11, 15], 9) == (0, 1)
assert two_sum([3, 2, 4], 6) == (1, 2) and two_sum([1, 2], 10) is None
groups = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
assert sorted(sorted(g) for g in groups) == [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]

d = {"x": 1}
assert d.get("missing", 0) == 0
try:
    d["missing"]
except KeyError:
    pass
else:
    raise AssertionError("expected KeyError")

assert {1, 2, 3} & {2, 3, 4} == {2, 3} and {1, 2} | {2, 3} == {1, 2, 3}
assert len(set([1, 1, 2, 2, 3])) == 3

try:
    for k in d:
        d[k + "!"] = 0                         # changing size during iteration is an error
except RuntimeError:
    pass
else:
    raise AssertionError("expected RuntimeError")
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

bool hasDuplicate(const std::vector<int>& items) {
    std::unordered_set<int> seen;
    for (int x : items) {
        if (!seen.insert(x).second) return true;  // insert reports whether it was new
    }
    return false;
}

std::pair<int, int> twoSum(const std::vector<int>& v, int target) {
    std::unordered_map<int, int> indexOf;
    for (int i = 0; i < static_cast<int>(v.size()); ++i) {
        auto it = indexOf.find(target - v[i]);
        if (it != indexOf.end()) return {it->second, i};
        indexOf[v[i]] = i;
    }
    return {-1, -1};
}

int main() {
    std::unordered_map<std::string, int> counts;
    for (const std::string& w : std::vector<std::string>{"a", "b", "a", "c", "a", "b"}) ++counts[w];
    assert(counts["a"] == 3 && counts["b"] == 2 && counts["c"] == 1 && counts.size() == 3);

    assert(hasDuplicate({1, 2, 3, 2}) && !hasDuplicate({1, 2, 3}));
    assert((twoSum({2, 7, 11, 15}, 9) == std::make_pair(0, 1)));
    assert((twoSum({1, 2}, 10) == std::make_pair(-1, -1)));

    std::unordered_map<std::string, std::vector<std::string>> groups;
    for (std::string w : {"eat", "tea", "tan", "ate", "nat", "bat"}) {
        std::string key = w;
        std::sort(key.begin(), key.end());
        groups[key].push_back(w);
    }
    assert(groups.size() == 3 && groups["aet"].size() == 3);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Set insertion, removal and membership tests, and map insertion, lookup and deletion, are O(1) expected time and O(n) worst case. Building a set or map from n items is O(n). Set operations such as intersection cost about O(min(len a, len b)). The one-pass two-sum takes O(n) time and O(n) space, replacing the O(n squared) nested loops. Memory is O(n) with a sizeable constant per entry. For comparison, `x in some_list` is O(n), which is why converting a list to a set before many membership tests pays off immediately.

## Common Mistakes & Misconceptions
The standard symptom is `KeyError` when reading a missing key with `d[key]`, fixed with `get`, `setdefault` or `defaultdict`. Another is a slow program that checks `x in some_list` inside a loop, where a set would make each test constant time. Students use lists as dictionary keys and get `TypeError: unhashable type`. They also assume sets keep insertion order (they do not guarantee any order), or change a dictionary's size while iterating over it, which raises `RuntimeError: dictionary changed size during iteration`. Floating-point values as keys can silently fail to match because of rounding. In C++, `operator[]` on `unordered_map` inserts a default entry for a missing key, which can create entries you did not intend.

## Builds On
This concept builds on Hash Tables: sets and maps are the interface programmers use for hash tables, and their expected O(1) behaviour, need for hashable keys, resizing and degraded worst case all come from the table mechanics described there. Knowing about load factors and collisions explains why performance is excellent in practice but not guaranteed.

## Leads To
Binary search trees offer the ordered alternative (sorted keys and range queries) at O(log n) cost, which is the relevant comparison when you need order. Hash maps are the workhorse inside algorithms such as prefix-sum counting, sliding windows on strings and memoised dynamic programming.

## Check Yourself
**Q1.** What is the difference between `d[key]` and `d.get(key)` for a missing key?
**A1.** `d[key]` raises KeyError while `d.get(key)` returns None (or a supplied default).
**Q2.** Why is converting a list to a set useful before many membership tests?
**A2.** Set membership is O(1) expected, while a list scan is O(n) per test.
**Q3.** How does the one-pass two-sum use a dictionary?
**A3.** It stores each value's index and checks whether target minus the current value was already seen, finding the pair in O(n).
