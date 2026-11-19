---
id: sliding_window
name: "Sliding Window"
cluster: searching_hashing
reviewed: false
sources:
  - "Competitive Programmer's Handbook (Laaksonen), Section 8.1 (Sliding window)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.4 (running totals over contiguous subarrays)"
---

## Overview
The sliding window technique answers questions about contiguous subarrays or substrings, such as the best sum of any k consecutive numbers or the longest stretch with no repeated character. It keeps a window, a range of the sequence bounded by a left and a right pointer, and updates the answer incrementally as the window slides or grows and shrinks. Instead of recomputing each window from scratch, each step adds the new element and removes the old one in constant time, so the whole scan is linear.

## Intuition
Think of looking through a rectangular frame as you slide it along a long banner. Moving the frame one step to the right reveals one new letter on its right edge and hides one on its left edge. To know how many letters inside the frame are vowels, you do not need to recount the whole frame each time: just adjust for the one letter that entered and the one that left.

## How It Works
There are two main kinds of window. A fixed-size window of length k slides one step at a time: compute the value of the first window, then for each step add the entering element and subtract the leaving element. The running sum for a window ending at index i is `window += values[i] - values[i - k]`.

A variable-size window grows and shrinks to satisfy a condition. Both ends only move to the right. The right pointer expands the window by one element at a time. While the window violates the condition (for instance it contains a repeated character, or its sum is too large), the left pointer moves right to shrink it. After each adjustment the window is valid and you update the best answer, such as the maximum length. For the longest substring without repeating characters, keep a set or a dictionary of the characters in the window; when the new character is already inside, advance left, removing characters, until the duplicate is gone.

The technique is a special case of two pointers where both pointers bound a region. Its correctness relies on a monotone property: if a window satisfies the condition, any smaller window inside it also does (or the reverse), so shrinking from the left can only help restore validity. This holds for sums of non-negative numbers and for distinctness conditions, but not for sums that include negative numbers, where shrinking can make the sum bigger and the method fails.

Complexity argument: each element enters the window once (when right passes it) and leaves at most once (when left passes it), so the total number of pointer moves is at most 2n. This holds even though a while loop sits inside the for loop, the same amortized argument as for the monotonic stack.

Typical problems: maximum sum of k consecutive elements; smallest subarray with a sum at least a target (positive numbers); longest substring with at most k distinct characters; counting anagrams of a pattern inside a text.

## Worked Example
Find the maximum sum of 3 consecutive elements in [2, 1, 5, 1, 3, 2].

The first window [2, 1, 5] sums to 8. Slide: remove 2, add 1: 8 - 2 + 1 = 7. Slide: remove 1, add 3: 7 - 1 + 3 = 9. Slide: remove 5, add 2: 9 - 5 + 2 = 6. The four windows are [2, 1, 5], [1, 5, 1], [5, 1, 3] and [1, 3, 2], with sums 8, 7, 9 and 6. The maximum is 9, from the window [5, 1, 3].

Longest substring without repeats in "abcabcbb": right adds a, b, c: window "abc", length 3. Next a repeats, so left advances past the first a: window "bca". Continuing, the best length is 3.

## Code
```python
def max_sum_window(values, k):
    if k > len(values):
        return None
    window = sum(values[:k])
    best = window
    for i in range(k, len(values)):
        window += values[i] - values[i - k]      # add the entering item, drop the leaving one
        best = max(best, window)
    return best


def longest_unique(text):
    last_seen = {}
    left = best = 0
    for right, ch in enumerate(text):
        if ch in last_seen and last_seen[ch] >= left:
            left = last_seen[ch] + 1             # shrink the window past the earlier duplicate
        last_seen[ch] = right
        best = max(best, right - left + 1)
    return best


def shortest_subarray_with_sum(values, target):
    """Smallest length of a contiguous subarray with sum >= target (positive numbers)."""
    left = total = 0
    best = float("inf")
    for right, v in enumerate(values):
        total += v
        while total >= target:
            best = min(best, right - left + 1)
            total -= values[left]
            left += 1
    return 0 if best == float("inf") else best


assert max_sum_window([2, 1, 5, 1, 3, 2], 3) == 9
assert max_sum_window([1, 2], 3) is None
assert longest_unique("abcabcbb") == 3
assert longest_unique("bbbbb") == 1 and longest_unique("") == 0 and longest_unique("pwwkew") == 3
assert shortest_subarray_with_sum([2, 3, 1, 2, 4, 3], 7) == 2
assert shortest_subarray_with_sum([1, 1, 1], 10) == 0

# Cross-check against brute force on random data.
import random

random.seed(3)
for _ in range(200):
    arr = [random.randint(1, 9) for _ in range(random.randint(3, 15))]
    k = random.randint(1, len(arr))
    brute = max(sum(arr[i:i + k]) for i in range(len(arr) - k + 1))
    assert max_sum_window(arr, k) == brute
print("all checks passed")
```

```cpp
#include <algorithm>
#include <cassert>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

int maxSumWindow(const std::vector<int>& v, std::size_t k) {
    int window = 0;
    for (std::size_t i = 0; i < k; ++i) window += v[i];
    int best = window;
    for (std::size_t i = k; i < v.size(); ++i) {
        window += v[i] - v[i - k];
        best = std::max(best, window);
    }
    return best;
}

int longestUnique(const std::string& s) {
    std::unordered_map<char, int> lastSeen;
    int left = 0, best = 0;
    for (int right = 0; right < static_cast<int>(s.size()); ++right) {
        auto it = lastSeen.find(s[right]);
        if (it != lastSeen.end() && it->second >= left) left = it->second + 1;
        lastSeen[s[right]] = right;
        best = std::max(best, right - left + 1);
    }
    return best;
}

int main() {
    assert(maxSumWindow({2, 1, 5, 1, 3, 2}, 3) == 9);
    assert(longestUnique("abcabcbb") == 3);
    assert(longestUnique("bbbbb") == 1 && longestUnique("") == 0);
    assert(longestUnique("pwwkew") == 3);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
A fixed-size window scan is O(n) time and O(1) extra space, versus O(n times k) if each window's sum is recomputed. The variable-size window is also O(n) time because the left and right pointers each move at most n times in total, even though a while loop appears inside the for loop. Extra space is O(1) for numeric sums and O(min(n, alphabet size)) for a set or dictionary of characters in the window. For a problem such as "longest substring without repeats", the brute force of checking all substrings is O(n cubed) naively or O(n squared) with care, so the window gives a large improvement.

## Common Mistakes & Misconceptions
A common symptom is wrong answers with negative numbers when using a variable-size window on sums: shrinking from the left can increase the sum, which breaks the logic, so another method such as prefix sums with a hash map is needed. Off-by-one errors are frequent: the window length is `right - left + 1`, not `right - left`. Students forget to update the best answer after shrinking, or after the final expansion, or mishandle k larger than the array length. Recomputing the window sum with `sum(values[i:i+k])` in a loop silently turns an O(n) solution into O(n times k). In the distinct-characters problem, not checking that the earlier occurrence lies inside the current window (`last_seen[ch] >= left`) makes the left pointer jump backward.

## Builds On
This concept builds on Two Pointers: a sliding window is exactly two pointers, left and right, that bound a region and only ever move forward, and the argument that each pointer moves at most n times is the one used there. Understanding why a pointer move discards only impossible candidates is what lets you shrink the window safely.

## Leads To
Window techniques appear in string problems, in streaming statistics such as moving averages, and in network rate limiting. Related structures such as the monotonic deque extend the idea to sliding-window maximum, and prefix sums give an alternative for fixed range-sum queries.

## Check Yourself
**Q1.** How is a fixed window's sum updated when it moves one step?
**A1.** Add the element entering on the right and subtract the element leaving on the left.
**Q2.** What is the length of a window with left and right inclusive indexes?
**A2.** right - left + 1.
**Q3.** Why is a variable-size window scan O(n) even with a while loop inside a for loop?
**A3.** Each element enters and leaves the window at most once, so there are at most 2n pointer moves.
