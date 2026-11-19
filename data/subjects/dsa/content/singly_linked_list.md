---
id: singly_linked_list
name: "Singly Linked List"
cluster: linear
reviewed: false
sources:
  - "CLRS, Section 10.2 (Linked lists)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.3 (Linked lists)"
---

## Overview
A singly linked list stores a sequence as a chain of nodes. Each node holds a value and a pointer to the next node, and the list is reached through a head pointer to the first node. The last node's next pointer is null. Unlike an array, the nodes are scattered in memory, so there is no jumping to index i: you follow the chain. In return, inserting or deleting at a known position needs no shifting.

## Intuition
Picture a scavenger hunt. Each clue card tells you what the prize is and where to find the next card. You only ever hold the first card, and you reach the fifth by following four clues in order. If you want to add a new clue after the second card, you simply write the third card's location on the new card and update the second card, and nobody else has to move. But you cannot skip straight to the fifth card.

## How It Works
A node is a small object with two fields: `value` and `next`. The list keeps `head`, a reference to the first node, or null when empty. Traversal starts at head and repeatedly moves to `node.next` until it reaches null.

Insertion at the head creates a new node whose next is the old head, then sets head to the new node, in O(1). Insertion after a given node sets the new node's next to that node's next, then sets that node's next to the new node. The order matters: if you overwrite the existing next pointer first, you lose the rest of the list.

Deletion of the node after a given node sets its next to the next-next node, so the removed node is bypassed (and freed in C++). Deleting the head just moves head forward. To delete a node you must reach its predecessor, which in a singly linked list means walking from the head.

Searching is linear because there is no index. Reversing a list is a classic exercise: keep three references (previous, current, next) and flip each pointer in a single pass. Always handle the empty list and the single node as special cases, and watch for a null next before dereferencing it, otherwise Python raises `AttributeError: 'NoneType' object has no attribute 'next'` and C++ crashes.

Nodes are allocated individually on the heap. Each node carries pointer overhead, and following pointers to scattered memory is slower in practice than scanning a contiguous array because of cache effects.

## Worked Example
Build the list 1 → 2 → 3 by inserting at the head: insert 3, then 2, then 1. After inserting 3 the list is 3. Inserting 2 makes a node 2 whose next is the old head (3), and head now points to 2: 2 → 3. Inserting 1 gives 1 → 2 → 3.

Now insert 9 after node 2. Create a node 9 whose next is node 2's next (node 3), then set node 2's next to node 9: 1 → 2 → 9 → 3. Had we first changed node 2's next to 9, node 3 would have become unreachable and lost.

Reverse 1 → 2 → 3: start with previous = null and current = 1. Step one: save next = 2, point 1 to null, move previous to 1 and current to 2. Step two: save next = 3, point 2 to 1, move on. Step three: point 3 to 2. The head becomes 3: 3 → 2 → 1.

## Code
```python
class Node:
    def __init__(self, value, next=None):
        self.value = value
        self.next = next


class LinkedList:
    def __init__(self):
        self.head = None

    def push_front(self, value):
        self.head = Node(value, self.head)          # O(1)

    def insert_after(self, node, value):
        node.next = Node(value, node.next)          # new node first points at the rest

    def delete_after(self, node):
        if node.next is not None:
            node.next = node.next.next              # bypass the removed node

    def find(self, value):
        node = self.head
        while node is not None:
            if node.value == value:
                return node
            node = node.next
        return None

    def reverse(self):
        previous = None
        current = self.head
        while current is not None:
            nxt = current.next
            current.next = previous
            previous, current = current, nxt
        self.head = previous

    def to_list(self):
        out, node = [], self.head
        while node is not None:
            out.append(node.value)
            node = node.next
        return out


lst = LinkedList()
for v in (3, 2, 1):
    lst.push_front(v)
assert lst.to_list() == [1, 2, 3]
lst.insert_after(lst.find(2), 9)
assert lst.to_list() == [1, 2, 9, 3]
lst.delete_after(lst.find(2))
assert lst.to_list() == [1, 2, 3]
lst.reverse()
assert lst.to_list() == [3, 2, 1]
assert lst.find(42) is None
empty = LinkedList()
empty.reverse()
assert empty.to_list() == []
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

struct Node {
    int value;
    Node* next;
    Node(int v, Node* n = nullptr) : value(v), next(n) {}
};

class LinkedList {
public:
    ~LinkedList() {
        while (head) {
            Node* next = head->next;
            delete head;
            head = next;
        }
    }
    void pushFront(int v) { head = new Node(v, head); }
    void insertAfter(Node* node, int v) { node->next = new Node(v, node->next); }
    void deleteAfter(Node* node) {
        if (node->next) {
            Node* victim = node->next;
            node->next = victim->next;
            delete victim;
        }
    }
    Node* find(int v) const {
        for (Node* n = head; n; n = n->next)
            if (n->value == v) return n;
        return nullptr;
    }
    void reverse() {
        Node* prev = nullptr;
        Node* cur = head;
        while (cur) {
            Node* nxt = cur->next;
            cur->next = prev;
            prev = cur;
            cur = nxt;
        }
        head = prev;
    }
    std::vector<int> toVector() const {
        std::vector<int> out;
        for (Node* n = head; n; n = n->next) out.push_back(n->value);
        return out;
    }

private:
    Node* head = nullptr;
};

int main() {
    LinkedList lst;
    for (int v : {3, 2, 1}) lst.pushFront(v);
    assert((lst.toVector() == std::vector<int>{1, 2, 3}));
    lst.insertAfter(lst.find(2), 9);
    assert((lst.toVector() == std::vector<int>{1, 2, 9, 3}));
    lst.deleteAfter(lst.find(2));
    lst.reverse();
    assert((lst.toVector() == std::vector<int>{3, 2, 1}));
    assert(lst.find(42) == nullptr);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Inserting or deleting at the head is O(1). Inserting or deleting after a node you already hold is O(1). Finding a node by value, by index, or the predecessor of a node is O(n). Reversing takes O(n) time and O(1) extra space. Appending at the tail is O(n) unless the list also keeps a tail pointer, in which case it is O(1). Memory is O(n) plus one pointer per node, and each node is a separate heap allocation.

## Common Mistakes & Misconceptions
A common symptom is `AttributeError: 'NoneType' object has no attribute 'next'` (or a segmentation fault in C++), caused by following next on a null node, often at the end of the list or on an empty list. Another is losing the rest of the list during insertion or reversal by overwriting a next pointer before saving the old one. Students also assume that linked lists are always faster than arrays for insertion, forgetting that reaching the insertion point costs O(n). Others think index access is O(1) as in arrays, or forget to free removed nodes in C++, leaking memory. Updating the head when inserting or deleting at the front is another frequent omission: the caller's head variable then still points to the old first node.

## Builds On
This concept builds on Pointers & References: each next field is a reference, and the entire structure depends on following, copying and reassigning references correctly, including the null reference at the end. It builds on Stack vs Heap Memory, because nodes are allocated on the heap so that they outlive the function that created them, and in C++ each node must be released explicitly.

## Leads To
Stacks and queues can be implemented with a linked list, and doubly and circular linked lists add a previous pointer or a wrap-around link. Hash tables use linked lists for chaining, tree basics generalise the idea to nodes with several children, and graph representation uses adjacency lists built from linked structures.

## Check Yourself
**Q1.** What is the time to insert a new node at the head of a singly linked list?
**A1.** O(1): create the node, point it at the old head and update head.
**Q2.** Why must you set the new node's next before changing the previous node's next?
**A2.** Otherwise the rest of the list becomes unreachable and is lost.
**Q3.** Why is finding the kth item slower than in an array?
**A3.** You must follow k pointers from the head; there is no direct index calculation.
