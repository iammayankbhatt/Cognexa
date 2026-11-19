---
id: amortized_analysis
name: "Amortized Analysis"
cluster: complexity
reviewed: false
sources:
  - "CLRS, Chapter 16 (Amortized Analysis): aggregate, accounting and potential methods"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.4 (Amortized analysis) and resizing arrays"
---

## Overview
Some operations are usually cheap but occasionally very expensive. Appending to a dynamic array normally takes constant time, yet every so often the array runs out of room and must be copied into a bigger one. Amortized analysis averages the cost over a whole sequence of operations, guaranteeing that the average cost per operation is small even though a single operation may be costly. It is a worst-case guarantee about sequences, not a statement about random inputs, which makes it different from average-case analysis.

## Intuition
Think of a monthly gym membership paid as one big annual fee. In the month you pay, your expense looks huge, but spread across the twelve months it is a modest amount each month. Likewise, a dynamic array does a big copy only rarely, and the many cheap appends before it "pay" for it in advance. Over the long run each append costs a small constant amount on average.

## How It Works
Three methods compute the same answer. The aggregate method totals the actual cost of n operations and divides by n. The accounting method assigns each operation a fixed charge, possibly more than its real cost; the surplus is stored as credit that pays for later expensive steps. The potential method defines a function of the data structure's state, the potential, and charges the real cost plus the change in potential.

Consider appending n items to a dynamic array that doubles its capacity when full. Most appends write one element at cost 1. When the array of size k is full, appending triggers a copy of k elements plus the write. Resizes happen at sizes 1, 2, 4, 8, and so on. The total copying cost for n appends is at most 1 + 2 + 4 + ... + n/2 + n, which is less than 2n, because the geometric series is dominated by its last term. Adding the n writes, the total cost is below 3n, so the amortized cost per append is at most 3, which is O(1).

The accounting view agrees: charge every append 3 units. One unit pays for the write, and two units are saved as credit on the new element. When a resize comes, the credit stored on the elements added since the last resize pays for copying all of them, so the account never goes negative.

Another classic example is a binary counter. Incrementing a counter flips some bits; flipping every bit costs a lot occasionally (from 0111 to 1000 flips four bits), but over n increments the lowest bit flips n times, the next n/2 times, then n/4 times, giving at most 2n flips, so each increment costs about 2 bit flips amortized.

Important: growing by a fixed amount, such as adding 10 slots every time, does not give constant amortized cost; each resize copies everything, so n appends cost a quadratic total, and the amortized cost per append is linear. Growth by a constant factor greater than one is what makes it work.

## Worked Example
Append 8 items to an empty array with initial capacity 1 that doubles when full. Track the cost, counting one unit per element written or copied.

Append 1: capacity 1, write: cost 1. Append 2: full, copy 1 element into capacity 2, write: cost 2. Append 3: full at size 2, copy 2 into capacity 4, write: cost 3. Append 4: room, write: cost 1. Append 5: full at 4, copy 4 into capacity 8, write: cost 5. Appends 6, 7 and 8: room, cost 1 each. Total cost = 1 + 2 + 3 + 1 + 5 + 1 + 1 + 1 = 15. Divide by 8 operations: about 1.9 per append, comfortably below the bound of 3 and clearly constant per operation as n grows.

## Code
The simulation counts every write and copy while appending to a doubling array and to an array that grows by a fixed step.

```python
def total_cost_doubling(n):
    capacity, size, cost = 1, 0, 0
    for _ in range(n):
        if size == capacity:
            cost += size            # copy all existing elements to the bigger array
            capacity *= 2
        cost += 1                   # write the new element
        size += 1
    return cost


def total_cost_fixed_step(n, step=10):
    capacity, size, cost = step, 0, 0
    for _ in range(n):
        if size == capacity:
            cost += size
            capacity += step
        cost += 1
        size += 1
    return cost


assert total_cost_doubling(8) == 15
for n in (10, 100, 1000, 100000):
    assert total_cost_doubling(n) < 3 * n          # amortized O(1) per append

# Growing by a fixed amount costs quadratic total time: the cost per append keeps growing.
per_append_small = total_cost_fixed_step(1000) / 1000
per_append_large = total_cost_fixed_step(10000) / 10000
assert per_append_large > 5 * per_append_small    # ten times the data, far more than the same cost each


def counter_flips(n):
    bits, flips = [0] * 40, 0
    for _ in range(n):
        i = 0
        while bits[i] == 1:
            bits[i] = 0
            flips += 1
            i += 1
        bits[i] = 1
        flips += 1
    return flips


assert counter_flips(1000) < 2 * 1000
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

long long totalCostDoubling(int n) {
    long long capacity = 1, size = 0, cost = 0;
    for (int i = 0; i < n; ++i) {
        if (size == capacity) {
            cost += size;  // copy existing elements
            capacity *= 2;
        }
        cost += 1;         // write the new element
        ++size;
    }
    return cost;
}

long long totalCostFixedStep(int n, int step = 10) {
    long long capacity = step, size = 0, cost = 0;
    for (int i = 0; i < n; ++i) {
        if (size == capacity) {
            cost += size;
            capacity += step;
        }
        cost += 1;
        ++size;
    }
    return cost;
}

int counterFlips(int n) {
    std::vector<int> bits(40, 0);
    int flips = 0;
    for (int i = 0; i < n; ++i) {
        std::size_t j = 0;
        while (bits[j] == 1) {
            bits[j] = 0;
            ++flips;
            ++j;
        }
        bits[j] = 1;
        ++flips;
    }
    return flips;
}

int main() {
    assert(totalCostDoubling(8) == 15);
    for (int n : {10, 100, 1000, 100000}) assert(totalCostDoubling(n) < 3LL * n);
    assert(totalCostFixedStep(10000) / 10000.0 > totalCostFixedStep(1000) / 1000.0);
    assert(counterFlips(1000) < 2000);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
For a dynamic array that doubles, a single append is O(n) in the worst case, but any sequence of n appends costs O(n) in total, so the amortized cost per append is O(1). Reading by index remains O(1). The space used is at most twice the number of stored elements, O(n). For the binary counter, n increments cost at most 2n bit flips, so O(1) amortized per increment even though one increment can flip O(log n) bits. If an array grows by a fixed number of slots instead of a constant factor, n appends cost O(n squared) total and O(n) amortized each, which is why libraries use factors such as 1.5 or 2.

## Common Mistakes & Misconceptions
A typical symptom is saying "append is O(n) because of resizing" or, the opposite, "append is O(1) always" with no mention of the rare expensive step. Amortized is neither: it is a guarantee about the average cost over any sequence. Students confuse it with average-case analysis, which assumes a probability distribution over inputs, whereas amortized analysis needs no randomness and holds for the worst possible sequence. Another error is assuming that any growth rule works: adding a fixed number of slots each time gives linear amortized cost. A further mistake is forgetting to count shrinking operations or deletions when a structure can also contract, where thrashing at the boundary can destroy the bound unless the shrink threshold is chosen carefully.

## Builds On
This concept builds on Asymptotic Notation: the amortized bound is stated as a Big-O guarantee and relies on the geometric series bounds and dominant-term reasoning introduced there. It also builds on Dynamic Arrays, whose doubling strategy is the standard example: you need to know that a dynamic array allocates a larger block and copies the elements when it is full in order to see where the occasional expensive operation comes from.

## Leads To
Disjoint set union achieves its famously small amortized cost per operation with path compression and union by rank. Hash tables rely on amortized O(1) insertion when they rehash on growth, and splay trees and many other structures are analysed with the potential method.

## Check Yourself
**Q1.** What does it mean that dynamic array append is amortized O(1)?
**A1.** Any sequence of n appends costs O(n) in total, so the average cost per append is constant even though a single append can be expensive.
**Q2.** Why must the array grow by a constant factor rather than by a fixed amount?
**A2.** Growing by a fixed amount copies all elements every few appends, giving quadratic total cost.
**Q3.** Is amortized analysis the same as average-case analysis?
**A3.** No. Amortized analysis guarantees the average over a worst-case sequence and uses no probability assumptions.
