---
id: linear_search
name: "Linear Search"
cluster: searching_hashing
reviewed: false
sources:
  - "CLRS, Exercise 2.1-3 (Linear search) and Section 2.1 (loop invariants)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (sequential search)"
---

## Overview
Linear search, also called sequential search, looks through a collection one element at a time from the start until it finds the target or runs out of elements. It is the simplest searching method, works on any collection, sorted or not, and needs no preparation. Its price is speed: in the worst case every element is examined, so the time grows in direct proportion to the size of the collection.

## Intuition
You are looking for your keys in a drawer full of unsorted objects. With no system, all you can do is pick up each item in turn and check whether it is your keys. If you are lucky they are on top; if you are unlucky they are at the very bottom, or not in the drawer at all, and you must have looked at everything to know. A drawer twice as full takes about twice as long to search.

## How It Works
The algorithm keeps an index i starting at 0. At each step it compares the element at i with the target. If they match, it returns i. Otherwise it increments i. If i reaches the length of the collection without a match, the target is absent and the algorithm returns a signal value such as -1 or None (or raises an error), never a valid index.

A useful way to reason about correctness is the loop invariant: at the start of each iteration, the target does not appear in any of the elements before position i. When the loop ends without finding it, all positions have been ruled out.

Variations change what you search for. Finding the first match returns at once. Finding the last match scans the whole list or scans from the end. Finding all matches continues after each hit and collects the indexes. Searching with a predicate (the first element that satisfies a condition, such as "first negative number") uses the same loop with a different test. A sentinel trick places the target at the end of the array to avoid checking the index bound on each step, a micro-optimisation rather than a change in complexity.

Linear search is the right tool when the data is unsorted, when the collection is very small, when you only search once (sorting first would cost more), or when elements can only be accessed in order, as in a linked list. For repeated searches on large data, a sorted array with binary search or a hash table is much faster.

## Worked Example
Search for 7 in the array [4, 9, 7, 1, 7].

i = 0: 4 is not 7. i = 1: 9 is not 7. i = 2: 7 matches, so return index 2 after 3 comparisons. The second 7 at index 4 is never seen, because the search stops at the first match.

Search for 5 in the same array. All five elements are compared, none matches, and the function returns -1 after 5 comparisons. This is the worst case: n comparisons for n elements, the same cost as a successful search that finds the last element.

Average case: if the target is equally likely to be at any position, the expected number of comparisons for a successful search is (n + 1) / 2, so about half the elements.

## Code
```python
def linear_search(values, target):
    for i, v in enumerate(values):
        if v == target:
            return i              # stop at the first match
    return -1                     # not found


def find_all(values, target):
    return [i for i, v in enumerate(values) if v == target]


def first_where(values, predicate):
    for i, v in enumerate(values):
        if predicate(v):
            return i
    return -1


def comparisons_needed(values, target):
    count = 0
    for v in values:
        count += 1
        if v == target:
            break
    return count


data = [4, 9, 7, 1, 7]
assert linear_search(data, 7) == 2
assert linear_search(data, 5) == -1
assert linear_search([], 1) == -1
assert find_all(data, 7) == [2, 4]
assert first_where([3, 8, -2, 5], lambda x: x < 0) == 2
assert comparisons_needed(data, 7) == 3
assert comparisons_needed(data, 5) == 5                  # worst case: n comparisons
average = sum(comparisons_needed(data, v) for v in [4, 9, 7, 1]) / 4
assert average == 2.5                                    # (1 + 2 + 3 + 4) / 4
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

int linearSearch(const std::vector<int>& v, int target) {
    for (std::size_t i = 0; i < v.size(); ++i)
        if (v[i] == target) return static_cast<int>(i);  // first match
    return -1;
}

std::vector<int> findAll(const std::vector<int>& v, int target) {
    std::vector<int> out;
    for (std::size_t i = 0; i < v.size(); ++i)
        if (v[i] == target) out.push_back(static_cast<int>(i));
    return out;
}

int main() {
    std::vector<int> data = {4, 9, 7, 1, 7};
    assert(linearSearch(data, 7) == 2);
    assert(linearSearch(data, 5) == -1);
    assert(linearSearch({}, 1) == -1);
    assert((findAll(data, 7) == std::vector<int>{2, 4}));

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Time: best case O(1), when the target is the first element; worst case O(n), when it is last or absent; average case about n/2 comparisons for a successful search, which is O(n). Space: O(1) extra, because only an index is kept. The method works on arrays and linked lists alike. When searching a Python list, `target in values` and `values.index(target)` use the same linear scan, so a membership test inside a loop over n items makes the program O(n squared).

## Common Mistakes & Misconceptions
A common bug is returning 0 or None for "not found" in a way that collides with a valid answer, for example returning 0 when index 0 is a legitimate result. Students forget the empty-collection case or loop one step past the end, causing an IndexError. Another mistake is using linear search inside a loop over the same data, such as checking `if x in big_list` for each of n items, which silently turns an O(n) task into O(n squared); a set would fix it. People sometimes believe linear search is "bad": for tiny or unsorted data it is perfectly good and often fastest. Others assume it finds all matches, but the basic version stops at the first.

## Builds On
This concept builds on Arrays: linear search is a loop over array indexes from 0 to n minus 1, and its constant-time per-element access and the valid index range come straight from the array model. The out-of-range error from reading past the end is exactly the arrays pitfall, avoided by stopping at the length.

## Leads To
Binary search speeds up searching when the data is sorted, and hash tables answer membership questions in expected constant time. Linear scans also form the inner step of many other algorithms, such as selection sort and the partition step of quick sort.

## Check Yourself
**Q1.** What does linear search return when the target is not present?
**A1.** A sentinel such as -1 (or None), never a valid index.
**Q2.** What is the worst-case number of comparisons for n elements?
**A2.** n, when the target is last or absent.
**Q3.** Why is `if x in my_list` inside a loop over my_list slow?
**A3.** Each membership test scans the list, so the whole program does O(n squared) work.
