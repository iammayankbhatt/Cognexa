---
id: hash_tables
name: "Hash Tables (chaining, open addressing)"
cluster: searching_hashing
reviewed: false
sources:
  - "CLRS, Chapter 11 (Hash Tables), Sections 11.2 and 11.4"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 3.4 (Hash Tables)"
---

## Overview
A hash table stores key-value pairs in an array and uses a hash function to compute where each key belongs, so insertion, lookup and deletion take expected constant time regardless of how many items are stored. Because two keys can map to the same position, every hash table needs a collision strategy. The two classic ones are separate chaining, where each slot holds a small list of the keys that landed there, and open addressing, where a colliding key is placed in another free slot found by probing.

## Intuition
Think of a coat check with 100 numbered hooks. The attendant turns your name into a hook number with a fixed rule and hangs your coat there. To retrieve it, they apply the same rule and go straight to the hook. If two people map to the same hook, the attendant either hangs both coats on the same hook (chaining) or puts the second coat on the next free hook along the row (open addressing). As long as hooks are not all crowded, retrieval is almost instant.

## How It Works
The table is an array of m slots. To insert (key, value), compute `index = hash(key) % m` and store the pair at that slot. To look up a key, compute the same index and search there. Both depend on the hash function sending equal keys to equal indexes, as covered in the hash functions concept.

Separate chaining makes each slot a list (often a linked list) of pairs. Insert adds to the list after checking that the key is not already present, lookup scans the one list, and delete removes the pair from it. Performance depends on the load factor, the number of stored items divided by m. With a good hash function the average chain length equals the load factor, so operations take expected O(1 + load factor).

Open addressing stores every pair directly in the array. On a collision it probes other slots in a fixed sequence: linear probing tries the next slot, then the next, and so on (cheap but prone to clustering, long runs of occupied slots); quadratic probing and double hashing spread probes out. Deleting needs care: simply emptying a slot would break the probe chain for later keys, so slots are marked with a tombstone instead. Open addressing needs the load factor to stay well below 1 (typically under about 0.7) because the table cannot hold more items than slots.

To keep operations fast, the table resizes: when the load factor passes a threshold, allocate a larger array (often double) and reinsert every key, because the indexes depend on m. Resizing costs O(n) but happens rarely, so insertion is amortized O(1), the same argument as for dynamic arrays.

Worst case: if all keys collide, a lookup scans everything and costs O(n). That is why good hash functions and resizing matter, and why adversarial inputs can be a security concern.

## Worked Example
Table of size 4 with chaining and hash(k) = k. Insert keys 1, 5, 9 and 2. Index of 1 is 1 % 4 = 1, of 5 is 1, of 9 is 1, and of 2 is 2. The table is: slot 0 empty, slot 1 holds [1, 5, 9], slot 2 holds [2], slot 3 empty. Looking up 9 goes to slot 1 and scans three entries. The load factor is 4 items over 4 slots = 1.0, which is high, so doubling the table to size 8 reinserts them: 1 goes to slot 1, 5 to slot 5, 9 to slot 1 (9 % 8 = 1), 2 to slot 2, giving shorter chains.

Linear probing with the same keys and size 8: 1 goes to slot 1; 5 to slot 5; 9 hashes to slot 1, which is taken, so it probes slot 2 and stays there; 2 hashes to slot 2, which is occupied by 9, so it moves on to slot 3.

## Code
```python
class ChainedHashTable:
    def __init__(self, size=4):
        self.slots = [[] for _ in range(size)]
        self.count = 0

    def _index(self, key):
        return hash(key) % len(self.slots)

    def put(self, key, value):
        chain = self.slots[self._index(key)]
        for i, (k, _) in enumerate(chain):
            if k == key:
                chain[i] = (key, value)           # overwrite an existing key
                return
        chain.append((key, value))
        self.count += 1
        if self.count / len(self.slots) > 0.75:    # keep the load factor low
            self._resize()

    def get(self, key, default=None):
        for k, v in self.slots[self._index(key)]:
            if k == key:
                return v
        return default

    def remove(self, key):
        chain = self.slots[self._index(key)]
        for i, (k, _) in enumerate(chain):
            if k == key:
                del chain[i]
                self.count -= 1
                return True
        return False

    def _resize(self):
        old = [pair for chain in self.slots for pair in chain]
        self.slots = [[] for _ in range(len(self.slots) * 2)]
        for k, v in old:                           # indexes depend on the size: reinsert everything
            self.slots[self._index(k)].append((k, v))


class LinearProbingTable:
    EMPTY, DELETED = object(), object()

    def __init__(self, size=8):
        self.keys = [self.EMPTY] * size
        self.values = [None] * size

    def put(self, key, value):
        i = hash(key) % len(self.keys)
        for _ in range(len(self.keys)):
            if self.keys[i] is self.EMPTY or self.keys[i] is self.DELETED or self.keys[i] == key:
                self.keys[i], self.values[i] = key, value
                return
            i = (i + 1) % len(self.keys)           # probe the next slot
        raise OverflowError("table is full")

    def get(self, key, default=None):
        i = hash(key) % len(self.keys)
        for _ in range(len(self.keys)):
            if self.keys[i] is self.EMPTY:
                return default
            if self.keys[i] is not self.DELETED and self.keys[i] == key:
                return self.values[i]
            i = (i + 1) % len(self.keys)
        return default

    def remove(self, key):
        i = hash(key) % len(self.keys)
        for _ in range(len(self.keys)):
            if self.keys[i] is self.EMPTY:
                return False
            if self.keys[i] is not self.DELETED and self.keys[i] == key:
                self.keys[i] = self.DELETED        # tombstone keeps later probe chains intact
                return True
            i = (i + 1) % len(self.keys)
        return False


t = ChainedHashTable()
for k in range(20):
    t.put(k, k * k)
assert t.get(7) == 49 and t.get(99) is None and t.count == 20
assert len(t.slots) > 4                                # the table resized
t.put(7, "seven")
assert t.get(7) == "seven" and t.count == 20           # overwriting does not add an item
assert t.remove(7) and t.get(7) is None and not t.remove(7)

p = LinearProbingTable(8)
for k in (1, 9, 17):                                   # all map to slot 1 and must probe
    p.put(k, k + 100)
assert p.get(9) == 109 and p.get(17) == 117
assert p.remove(9)
assert p.get(17) == 117                                # still reachable past the tombstone
assert p.get(9) is None
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <list>
#include <string>
#include <utility>
#include <vector>

class ChainedHashTable {
public:
    ChainedHashTable() : slots_(4) {}
    void put(int key, int value) {
        auto& chain = slots_[index(key)];
        for (auto& kv : chain) {
            if (kv.first == key) {
                kv.second = value;
                return;
            }
        }
        chain.push_back({key, value});
        ++count_;
        if (static_cast<double>(count_) / slots_.size() > 0.75) resize();
    }
    bool get(int key, int& out) const {
        for (const auto& kv : slots_[index(key)]) {
            if (kv.first == key) {
                out = kv.second;
                return true;
            }
        }
        return false;
    }
    bool remove(int key) {
        auto& chain = slots_[index(key)];
        for (auto it = chain.begin(); it != chain.end(); ++it) {
            if (it->first == key) {
                chain.erase(it);
                --count_;
                return true;
            }
        }
        return false;
    }
    std::size_t size() const { return count_; }
    std::size_t capacity() const { return slots_.size(); }

private:
    std::size_t index(int key) const { return static_cast<std::size_t>(key) % slots_.size(); }
    void resize() {
        std::vector<std::list<std::pair<int, int>>> old;
        old.swap(slots_);
        slots_.assign(old.size() * 2, {});
        for (auto& chain : old)
            for (auto& kv : chain) slots_[index(kv.first)].push_back(kv);
    }
    std::vector<std::list<std::pair<int, int>>> slots_;
    std::size_t count_ = 0;
};

int main() {
    ChainedHashTable t;
    for (int k = 0; k < 20; ++k) t.put(k, k * k);
    int v = 0;
    assert(t.get(7, v) && v == 49);
    assert(!t.get(99, v));
    assert(t.size() == 20 && t.capacity() > 4);
    t.put(7, 1);
    assert(t.get(7, v) && v == 1 && t.size() == 20);
    assert(t.remove(7) && !t.get(7, v) && !t.remove(7));

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
With a good hash function and a bounded load factor, insert, lookup and delete are O(1) expected time, with chaining costing O(1 + load factor) and open addressing costing roughly 1 / (1 - load factor) probes. Resizing costs O(n) but occurs rarely, so insertion is O(1) amortized. The worst case, when every key collides, is O(n) per operation. Space is O(n + m), with extra pointers for chaining or spare slots for open addressing. A hash table does not keep keys in sorted order, so range queries or ordered iteration need a tree instead.

## Common Mistakes & Misconceptions
A frequent symptom is a hash-based collection that becomes slow as it fills, caused by a load factor that never triggers a resize or by a poor hash function that creates long chains or probe runs. With open addressing, emptying a slot on delete instead of leaving a tombstone makes later keys unreachable, so lookups fail for keys that are present. Students forget that resizing changes every key's index and must reinsert rather than copy. Another misconception is that lookups are always O(1): that is the expected cost, and the worst case is linear. People also expect iteration in insertion or sorted order, which hash tables do not guarantee in general, although Python dictionaries preserve insertion order as a language feature. Using mutable keys breaks the table when the key changes after insertion.

## Builds On
This concept builds on Hash Functions: the table is only as good as the function that turns keys into indexes, and the requirements of determinism and uniform spread are what keep chains short. It also builds on Singly Linked List because separate chaining stores the colliding keys of a slot in a linked list, inserting at the head or scanning the list in O(chain length).

## Leads To
Hash Sets & Maps in Practice shows how built-in dictionaries and sets use these ideas for counting, grouping and membership tests. The same structures underlie caches and symbol tables, and hash-based partitioning is used in databases and distributed systems.

## Check Yourself
**Q1.** What is the load factor of a hash table?
**A1.** The number of stored items divided by the number of slots.
**Q2.** Why must a deleted slot in open addressing be marked with a tombstone?
**A2.** Emptying it would break the probe chain and make later colliding keys unfindable.
**Q3.** Why is the table resized by reinserting every key?
**A3.** The index is the hash modulo the table size, so changing the size changes every key's position.
