---
id: functions
name: "Functions & Parameters"
cluster: foundations
reviewed: false
sources:
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.1 (Static methods)"
  - "CLRS, Chapter 2 (pseudocode conventions for procedures)"
---

## Overview
A function packages a piece of logic under a name so it can be reused with different inputs. It receives values through parameters, does some work, and hands a result back with a return statement. Functions let you break a big problem into small, testable parts, and they are the unit that recursion, and later the call stack, are built on.

## Intuition
A function is like a recipe card. The card lists the ingredients you must supply (the parameters), the steps to follow (the body) and what you end up with (the return value). You can use the same card for a small or large batch, and you do not need to know how the recipe works inside to use it. Two cooks using the same card in different kitchens do not interfere with each other, which mirrors how local variables are private to each call.

## How It Works
A function definition gives a name, a list of parameters and a body. A call supplies arguments, one for each parameter. When the call happens, the language creates fresh local variables for the parameters, runs the body, and when it reaches `return value` it stops and sends the value back to the caller. A function that finishes without a return statement gives back `None` in Python, which is a common source of surprises.

Scope decides where a name is visible. Variables created inside a function are local: they exist only during that call and disappear afterwards. Reading a global is possible, but assigning to a name inside a function creates a new local unless you declare it global.

Passing arguments works by assigning each argument to the parameter name. In Python this means the parameter refers to the same object as the argument. If the object is immutable, such as an integer or string, the function cannot change the caller's value. If it is mutable, such as a list, changes made inside the function are visible to the caller. C++ lets you choose explicitly: pass by value copies the argument, pass by reference with `&` shares it.

Default parameter values are evaluated once, when the function is defined. A mutable default such as `def f(x, items=[])` is therefore shared between calls, which is a classic bug. Use `None` and create the list inside.

## Worked Example
Trace `def area(width, height): return width * height` called as `area(3, 4) + area(2, 5)`.

The first call creates locals width = 3 and height = 4, computes 12, returns it and the locals vanish. The second call creates new locals width = 2 and height = 5, returns 10. The caller adds 12 + 10 = 22. The two calls never see each other's variables.

Now trace a list parameter: `def add_one(items): items.append(1)` with `data = []`. Calling `add_one(data)` makes `items` refer to the same list as `data`, so after the call `data` is `[1]`. The function returned None, but it changed the caller's list through the shared reference.

## Code
```python
def area(width, height):
    return width * height

assert area(3, 4) + area(2, 5) == 22

def add_one(items):
    items.append(1)       # mutates the caller's list: same object

data = []
add_one(data)
assert data == [1]

def rebind(n):
    n = n + 1             # rebinding a local name does not affect the caller's integer
    return n

x = 5
assert rebind(x) == 6 and x == 5

def no_return(a):
    a * 2                 # computes a value but never returns it

assert no_return(3) is None

def collect(value, bucket=None):   # safe pattern for a mutable default
    if bucket is None:
        bucket = []
    bucket.append(value)
    return bucket

assert collect(1) == [1] and collect(2) == [2]
print("all checks passed")
```

```cpp
#include <cassert>
#include <iostream>
#include <vector>

int area(int width, int height) { return width * height; }

void addOne(std::vector<int>& items) { items.push_back(1); }  // reference: changes the caller's vector

int rebind(int n) {  // pass by value: n is a private copy
    n = n + 1;
    return n;
}

int main() {
    assert(area(3, 4) + area(2, 5) == 22);

    std::vector<int> data;
    addOne(data);
    assert(data.size() == 1 && data[0] == 1);

    int x = 5;
    assert(rebind(x) == 6 && x == 5);

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Calling a function costs a small constant amount of time to set up its locals and jump to its code, plus whatever the body does. Passing a large object by value copies it, which can cost time proportional to its size, so C++ code often passes big objects by reference. Each active call also uses stack memory for its locals, which matters when functions call themselves deeply. The time of a function is usually described by how its body scales with the arguments, for example a function that loops over a list parameter is linear in the list's length.

## Common Mistakes & Misconceptions
A frequent symptom is a function that returns None when a value was expected, caused by a missing return statement or by printing instead of returning. Another is a function that mysteriously keeps data between calls, caused by a mutable default argument. Beginners often assume that reassigning a parameter changes the caller's variable, then are surprised when a list modified inside the function does change outside. Confusing printing with returning is also common: print shows text to the user, return gives a value to the calling code. Finally, using a local variable outside its function raises a NameError because it no longer exists.

## Builds On
This concept builds on Conditionals & Loops: the body of a function is made of the conditionals and loops from that concept, and a return statement is a controlled early exit similar to break. Writing a useful function requires deciding with a conditional when to return and with a loop how much work to repeat.

## Leads To
Function calls and the call stack explain what the machine does when a function runs, which is essential for understanding recursion. Stack versus heap memory builds on how a function's local variables are created and destroyed, and recursion is simply a function that calls itself.

## Check Yourself
**Q1.** What does a Python function return if it has no return statement?
**A1.** None.
**Q2.** Why is `def f(x, items=[])` dangerous?
**A2.** The default list is created once and shared by every call that uses the default.
**Q3.** If a function appends to a list parameter, does the caller's list change?
**A3.** Yes, because the parameter refers to the same list object.
