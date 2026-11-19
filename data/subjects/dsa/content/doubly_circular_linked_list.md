---
id: doubly_circular_linked_list
name: "Doubly & Circular Linked Lists"
cluster: linear
reviewed: false
sources:
  - "CLRS, Section 10.2 (Linked lists: doubly linked lists and sentinels)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.3 (Doubly linked lists)"
---

## Overview
A doubly linked list gives each node two links, next and prev, so the list can be walked in both directions and a node can be removed in constant time when you hold a reference to it. A circular list links the last node back to the first, so there is no null end and traversal can wrap around forever. The two ideas combine freely, and many real structures, such as an LRU cache or an operating system's ready queue, use a circular doubly linked list with a sentinel node.

## Intuition
A singly linked list is a one-way street: you can only drive forward, and to turn around you must go back to the start. A doubly linked list is a two-way street: every house knows its neighbour on each side, so you can leave in either direction, and a house can be demolished without anyone searching for its predecessor. A circular list is a roundabout: keep going forward and you arrive back where you started.

## How It Works
Each node stores `value`, `prev` and `next`. The list keeps `head` and often `tail`. To remove a node X, set `X.prev.next = X.next` and `X.next.prev = X.prev`. This is O(1) and needs no search for the predecessor, which a singly linked list cannot do. To insert Y after X, set `Y.prev = X`, `Y.next = X.next`, then fix the neighbours: `X.next.prev = Y` and `X.next = Y`. Order matters again, and four pointers are updated instead of two, so there are more chances for mistakes.

Special cases at the ends make code messy: a node at the head has no prev, and a node at the tail has no next. A sentinel (dummy) node removes these cases. The sentinel sits between the tail and the head of a circular list, so every real node always has a non-null prev and next. An empty list is just the sentinel pointing to itself, and the same insert and remove code works for every position.

A circular singly linked list links the last node's next to the head. Traversal must now stop when it returns to the starting node, not when it reaches null; a loop that waits for null would never end. Circular lists suit round-robin scheduling, where each task takes a turn and the pointer simply advances.

The cost of the extra links is memory (two pointers per node) and complexity. The benefit is O(1) removal given a node, O(1) insertion at both ends with a tail or sentinel, and backward traversal.

## Worked Example
Maintain the list A, B, C with a sentinel S in a circle: S ⇄ A ⇄ B ⇄ C ⇄ S. Remove B. Set A.next to C and C.prev to A. The circle is now S ⇄ A ⇄ C ⇄ S, and nothing else was touched.

Insert D at the end, which is just before the sentinel. Create D with prev = C and next = S, then set C.next = D and S.prev = D. The circle is S ⇄ A ⇄ C ⇄ D ⇄ S. Traversing backward from S.prev visits D, C, A, which is a reverse listing at no extra cost. With an empty list S.next and S.prev both point to S, and the same insertion code gives S ⇄ D ⇄ S without any special case.

## Code
```python
class Node:
    def __init__(self, value=None):
        self.value = value
        self.prev = self
        self.next = self


class CircularDoublyLinkedList:
    def __init__(self):
        self.sentinel = Node()               # empty list: sentinel points to itself

    def insert_after(self, node, value):
        new = Node(value)
        new.prev = node
        new.next = node.next
        node.next.prev = new
        node.next = new
        return new

    def append(self, value):
        return self.insert_after(self.sentinel.prev, value)

    def remove(self, node):
        node.prev.next = node.next           # O(1): no search for the predecessor
        node.next.prev = node.prev

    def to_list(self):
        out, node = [], self.sentinel.next
        while node is not self.sentinel:     # stop at the sentinel, not at None
            out.append(node.value)
            node = node.next
        return out

    def to_list_reversed(self):
        out, node = [], self.sentinel.prev
        while node is not self.sentinel:
            out.append(node.value)
            node = node.prev
        return out


lst = CircularDoublyLinkedList()
a = lst.append("A")
b = lst.append("B")
c = lst.append("C")
assert lst.to_list() == ["A", "B", "C"]
assert lst.to_list_reversed() == ["C", "B", "A"]
lst.remove(b)
assert lst.to_list() == ["A", "C"]
lst.append("D")
assert lst.to_list() == ["A", "C", "D"]
lst.remove(a)
lst.remove(c)
assert lst.to_list() == ["D"]
only = lst.sentinel.next
lst.remove(only)
assert lst.to_list() == [] and lst.sentinel.next is lst.sentinel
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

struct Node {
    int value;
    Node* prev;
    Node* next;
    explicit Node(int v = 0) : value(v), prev(this), next(this) {}
};

class CircularList {
public:
    CircularList() : sentinel_(new Node()) {}
    ~CircularList() {
        Node* n = sentinel_->next;
        while (n != sentinel_) {
            Node* next = n->next;
            delete n;
            n = next;
        }
        delete sentinel_;
    }
    Node* insertAfter(Node* node, int v) {
        Node* fresh = new Node(v);
        fresh->prev = node;
        fresh->next = node->next;
        node->next->prev = fresh;
        node->next = fresh;
        return fresh;
    }
    Node* append(int v) { return insertAfter(sentinel_->prev, v); }
    void remove(Node* node) {
        node->prev->next = node->next;
        node->next->prev = node->prev;
        delete node;
    }
    std::vector<int> toVector() const {
        std::vector<int> out;
        for (Node* n = sentinel_->next; n != sentinel_; n = n->next) out.push_back(n->value);
        return out;
    }
    std::vector<int> toVectorReversed() const {
        std::vector<int> out;
        for (Node* n = sentinel_->prev; n != sentinel_; n = n->prev) out.push_back(n->value);
        return out;
    }

private:
    Node* sentinel_;
};

int main() {
    CircularList lst;
    lst.append(1);
    Node* b = lst.append(2);
    lst.append(3);
    assert((lst.toVector() == std::vector<int>{1, 2, 3}));
    assert((lst.toVectorReversed() == std::vector<int>{3, 2, 1}));
    lst.remove(b);
    assert((lst.toVector() == std::vector<int>{1, 3}));

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Insertion after a node and removal of a node you hold are O(1), because only a fixed number of pointers change. Insertion and removal at either end are O(1) with a sentinel (or head and tail pointers). Searching by value is O(n). Reaching the kth node is O(n), though you can start from the nearer end to halve the distance. Space is O(n) with two pointers per node, roughly twice the pointer overhead of a singly linked list. Traversing a full circle costs O(n).

## Common Mistakes & Misconceptions
A common symptom is an infinite loop when traversing a circular list with `while node is not None`: the list never ends in null, so the loop must stop at the starting node or sentinel instead. Another is a broken list after an insertion or removal where only some of the four pointers were updated, leaving next and prev inconsistent, so that forward and backward walks disagree. Students forget to handle the empty list and single-node cases, or forget that removing the head or tail requires updating those references when no sentinel is used. Some think doubly linked lists make search faster; they only help with moving backwards and with removal given a node. Finally, memory leaks occur in C++ when removed nodes are not deleted.

## Builds On
This concept builds on Singly Linked List: it uses the same node-and-pointer idea and the same careful ordering of pointer updates, only with a prev link added and, for circular lists, a next link that wraps around. Knowing why removal in a singly linked list needs the predecessor explains the value of the extra prev link, which gives that predecessor for free.

## Leads To
The deque and circular queue use circular buffers and linked structures with access at both ends, which is the same two-ended access a doubly linked list provides. An LRU cache combines a hash table with a doubly linked list so entries can be moved to the front in constant time.

## Check Yourself
**Q1.** Why can a doubly linked list remove a node in O(1) when given only that node?
**A1.** The node knows its predecessor through prev, so both neighbours can be relinked without searching.
**Q2.** What does a sentinel node simplify?
**A2.** It removes special cases at the ends, because every real node always has a non-null prev and next.
**Q3.** Why does `while node is not None` loop forever on a circular list?
**A3.** The last node links back to the first, so no node ever has a null next.
