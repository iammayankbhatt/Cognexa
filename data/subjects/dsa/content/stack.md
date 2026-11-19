---
id: stack
name: "Stack (ADT & implementations)"
cluster: linear
reviewed: false
sources:
  - "CLRS, Section 10.1 (Stacks and queues)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.3 (Bags, Queues, and Stacks)"
---

## Overview
A stack is a collection with last-in, first-out behaviour: the item added most recently is the first one removed. It supports three core operations: push adds an item on top, pop removes and returns the top item, and peek reads the top without removing it. Stacks are an abstract data type (ADT): the behaviour is defined independently of how it is stored, and it can be built on an array or a linked list. They appear everywhere: undo history, balanced-bracket checks, expression evaluation and the call stack itself.

## Intuition
A stack is a pile of plates. You can only add a plate to the top and take a plate from the top. The plate you put down last is the one you pick up first, and you cannot get at a plate in the middle without removing everything above it. A browser's back button works the same way: every page you visit is pushed, and pressing back pops the most recent one.

## How It Works
The ADT promises: push(x) puts x on top, pop() removes and returns the top item (error on an empty stack), peek() returns the top item, and isEmpty() and size() report the state. All operations should take constant time.

An array-based stack keeps items in a list and an index (or the length) marking the top. Push appends at the end and pop removes from the end, both O(1) amortized when the array is dynamic. A linked-list-based stack keeps the top as the head of a singly linked list: push inserts at the head and pop removes the head, both worst-case O(1), at the cost of one pointer per node. Using the wrong end of a linked list, such as appending at the tail of a list without a tail pointer, would make operations O(n).

Popping from an empty stack is an error condition called underflow. A fixed-capacity array-based stack can also overflow when it is full; with a dynamic array this does not occur.

Classic uses: matching brackets (push each opening bracket, pop on each closing bracket and check it matches); reversing a sequence; depth-first search with an explicit stack; evaluating postfix expressions; undo and redo; and converting recursion to iteration, because the call stack is itself a stack of frames.

## Worked Example
Check whether the string "([]{})" has balanced brackets.

Read '(' and push it: stack [(]. Read '[' and push: [(, []. Read ']' : the top is '[', which matches, so pop: [(]. Read '{' and push: [(, {]. Read '}': top is '{', match, pop: [(]. Read ')': top is '(', match, pop: []. The input is finished and the stack is empty, so the brackets are balanced. For "([)]" the third symbol ')' meets top '[' which does not match, so the answer is false at once. For "((" the stack is not empty at the end, so it is also unbalanced.

## Code
```python
class Stack:
    def __init__(self):
        self._items = []

    def push(self, x):
        self._items.append(x)          # amortized O(1)

    def pop(self):
        if not self._items:
            raise IndexError("pop from empty stack")   # underflow
        return self._items.pop()

    def peek(self):
        if not self._items:
            raise IndexError("peek at empty stack")
        return self._items[-1]

    def is_empty(self):
        return not self._items

    def __len__(self):
        return len(self._items)


def balanced(text):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = Stack()
    for ch in text:
        if ch in "([{":
            stack.push(ch)
        elif ch in pairs:
            if stack.is_empty() or stack.pop() != pairs[ch]:
                return False
    return stack.is_empty()


s = Stack()
for v in (1, 2, 3):
    s.push(v)
assert s.peek() == 3 and len(s) == 3
assert [s.pop(), s.pop(), s.pop()] == [3, 2, 1]
assert s.is_empty()
try:
    s.pop()
except IndexError:
    pass
else:
    raise AssertionError("expected underflow")

assert balanced("([]{})") and not balanced("([)]") and not balanced("((") and not balanced("]")
assert balanced("")
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <stack>
#include <string>

bool balanced(const std::string& text) {
    std::stack<char> st;
    for (char ch : text) {
        if (ch == '(' || ch == '[' || ch == '{') {
            st.push(ch);
        } else if (ch == ')' || ch == ']' || ch == '}') {
            if (st.empty()) return false;
            char open = st.top();
            st.pop();
            if ((ch == ')' && open != '(') || (ch == ']' && open != '[') ||
                (ch == '}' && open != '{'))
                return false;
        }
    }
    return st.empty();
}

int main() {
    std::stack<int> s;
    for (int v = 1; v <= 3; ++v) s.push(v);
    assert(s.top() == 3 && s.size() == 3);
    s.pop();
    s.pop();
    assert(s.top() == 1);
    s.pop();
    assert(s.empty());

    assert(balanced("([]{})") && !balanced("([)]") && !balanced("((") && !balanced("]"));
    assert(balanced(""));

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Push, pop, peek, isEmpty and size are all O(1): amortized for a dynamic-array stack and worst-case for a linked-list stack. Space is O(n) for n stored items. The bracket checker runs in O(n) time over n characters and uses O(n) extra space in the worst case, when every character is an opening bracket. Searching for an item that is not on top is O(n), but a stack is not designed for that: if you need it, you probably want a different structure.

## Common Mistakes & Misconceptions
Typical symptoms are `IndexError: pop from empty list` (underflow), caused by popping without checking for emptiness, for example in a bracket checker for input that starts with a closing bracket. Students often forget the final emptiness check, accepting "((" as balanced. Another mistake is mixing up which end is the top in a linked-list implementation, which turns O(1) operations into O(n). People confuse stack order with queue order and expect the oldest item back. Some believe a stack must be implemented with an array only; the ADT is independent of storage. Finally, using a stack when recursion would be cleaner, or the reverse, are design choices rather than bugs, but forgetting that a recursive solution already uses the call stack hides its O(depth) space.

## Builds On
This concept builds on Arrays because the simplest stack stores its items in an array (or dynamic array) with the top at the end, which is why push and pop are constant time. It builds on Singly Linked List because the alternative implementation uses the list head as the top, where insertion and removal at the head are O(1) and need no resizing.

## Leads To
Expression evaluation uses a stack for operands and operators, and the monotonic stack keeps its contents ordered to answer next-greater queries. Depth-first search can be written with an explicit stack, and the call stack explains recursion, since each function call pushes a frame in the same last-in, first-out manner.

## Check Yourself
**Q1.** In what order are items removed from a stack?
**A1.** Last in, first out: the most recently pushed item comes out first.
**Q2.** What is stack underflow?
**A2.** Trying to pop or peek when the stack is empty.
**Q3.** Which end of a singly linked list should be the top for O(1) push and pop?
**A3.** The head.
