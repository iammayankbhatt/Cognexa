---
id: expression_evaluation
name: "Expression Evaluation (infix/postfix)"
cluster: linear
reviewed: false
sources:
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 1.3 (Dijkstra's two-stack algorithm)"
  - "Knuth, The Art of Computer Programming Vol. 1, Section 2.2.1 (Stacks, queues and deques) and Dijkstra's shunting-yard algorithm"
---

## Overview
People write arithmetic in infix notation, with the operator between its operands: 3 + 4 * 2. Computers find it easier to evaluate postfix (reverse Polish) notation, where the operator follows its operands: 3 4 2 * +. Postfix needs no parentheses and no precedence rules, because the order of tokens already says what to compute first. Two stack-based algorithms connect the two worlds: evaluating a postfix expression, and converting infix to postfix with the shunting-yard method. Calculators, compilers and interpreters use these ideas.

## Intuition
Imagine a cashier with a small pile of numbers on the counter. Reading "3 4 2 * +" aloud, they put 3, 4 and 2 on the pile. At "*" they take the top two numbers (4 and 2), multiply them and put the result 8 back. At "+" they take the top two (3 and 8), add them and leave 11. The pile always holds the intermediate results waiting for their operator, which is exactly a stack.

## How It Works
Evaluating postfix: scan tokens left to right. If the token is a number, push it. If it is an operator, pop the top two values, with the first popped as the right operand and the second as the left, apply the operator and push the result. At the end the stack holds one value, the answer. The order of operands matters for subtraction and division: for "7 2 -" you pop 2 first, then 7, and compute 7 - 2.

Converting infix to postfix with the shunting-yard algorithm uses an operator stack and an output list. Numbers go straight to the output. For an operator, while the stack top is an operator with higher precedence, or equal precedence for a left-associative operator, pop it to the output; then push the new operator. A left parenthesis is pushed, and a right parenthesis pops operators to the output until the matching left parenthesis, which is discarded. At the end pop all remaining operators to the output.

Precedence says that multiplication and division bind tighter than addition and subtraction. Associativity says how equal-precedence operators group: subtraction is left-associative (8 - 3 - 2 means (8 - 3) - 2 = 3), while exponentiation is right-associative (2 ^ 3 ^ 2 means 2 ^ (3 ^ 2) = 512).

Evaluating infix directly can also be done with two stacks (one for values, one for operators), the idea behind Dijkstra's two-stack algorithm. The result is the same: a left-to-right scan with stacks holding what is still waiting for its other operand.

Typical errors to guard against: malformed input leaves more or fewer than one value on the stack; division by zero; unmatched parentheses; unary minus, which needs extra handling.

## Worked Example
Convert 3 + 4 * 2 to postfix. Read 3: output [3]. Read +: stack [+]. Read 4: output [3, 4]. Read *: its precedence is higher than the + on top, so push: stack [+, *]. Read 2: output [3, 4, 2]. End: pop * then +, output [3, 4, 2, *, +]. The postfix is 3 4 2 * +.

Evaluate it: push 3, 4, 2: stack [3, 4, 2]. Operator *: pop 2 and 4, push 8: [3, 8]. Operator +: pop 8 and 3, push 11: [11]. The answer is 11.

With parentheses: (3 + 4) * 2. Push (, output 3, push +, output 4, then ) pops + to the output, giving 3 4 +. Push *, output 2, pop * at the end: 3 4 + 2 *, which evaluates to 14.

## Code
```python
PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}


def to_postfix(tokens):
    output, ops = [], []
    for tok in tokens:
        if tok.isdigit():
            output.append(tok)
        elif tok in PRECEDENCE:
            while ops and ops[-1] in PRECEDENCE and PRECEDENCE[ops[-1]] >= PRECEDENCE[tok]:
                output.append(ops.pop())       # left-associative: pop equal precedence too
            ops.append(tok)
        elif tok == "(":
            ops.append(tok)
        elif tok == ")":
            while ops[-1] != "(":
                output.append(ops.pop())
            ops.pop()                          # discard the left parenthesis
        else:
            raise ValueError("bad token: " + tok)
    while ops:
        if ops[-1] == "(":
            raise ValueError("unmatched parenthesis")
        output.append(ops.pop())
    return output


def eval_postfix(tokens):
    stack = []
    for tok in tokens:
        if tok.isdigit():
            stack.append(int(tok))
        else:
            right = stack.pop()                # the first popped is the right operand
            left = stack.pop()
            if tok == "+":
                stack.append(left + right)
            elif tok == "-":
                stack.append(left - right)
            elif tok == "*":
                stack.append(left * right)
            elif tok == "/":
                stack.append(left // right)
    if len(stack) != 1:
        raise ValueError("malformed expression")
    return stack[0]


assert to_postfix("3 + 4 * 2".split()) == ["3", "4", "2", "*", "+"]
assert to_postfix("( 3 + 4 ) * 2".split()) == ["3", "4", "+", "2", "*"]
assert to_postfix("8 - 3 - 2".split()) == ["8", "3", "-", "2", "-"]
assert eval_postfix(["3", "4", "2", "*", "+"]) == 11
assert eval_postfix("3 4 + 2 *".split()) == 14
assert eval_postfix("7 2 -".split()) == 5          # left minus right, not the reverse
assert eval_postfix(to_postfix("8 - 3 - 2".split())) == 3
assert eval_postfix(to_postfix("2 * ( 3 + 4 ) - 5".split())) == 9
try:
    eval_postfix(["1", "2"])
except ValueError:
    pass
else:
    raise AssertionError("expected malformed expression error")
print("all checks passed")
```

```cpp
#include <cassert>
#include <cctype>
#include <iostream>
#include <map>
#include <sstream>
#include <stack>
#include <string>
#include <vector>

std::vector<std::string> split(const std::string& s) {
    std::istringstream in(s);
    std::vector<std::string> out;
    std::string tok;
    while (in >> tok) out.push_back(tok);
    return out;
}

std::vector<std::string> toPostfix(const std::vector<std::string>& tokens) {
    std::map<std::string, int> prec = {{"+", 1}, {"-", 1}, {"*", 2}, {"/", 2}};
    std::vector<std::string> output;
    std::stack<std::string> ops;
    for (const std::string& tok : tokens) {
        if (std::isdigit(static_cast<unsigned char>(tok[0]))) {
            output.push_back(tok);
        } else if (prec.count(tok)) {
            while (!ops.empty() && prec.count(ops.top()) && prec[ops.top()] >= prec[tok]) {
                output.push_back(ops.top());
                ops.pop();
            }
            ops.push(tok);
        } else if (tok == "(") {
            ops.push(tok);
        } else if (tok == ")") {
            while (ops.top() != "(") {
                output.push_back(ops.top());
                ops.pop();
            }
            ops.pop();
        }
    }
    while (!ops.empty()) {
        output.push_back(ops.top());
        ops.pop();
    }
    return output;
}

int evalPostfix(const std::vector<std::string>& tokens) {
    std::stack<int> st;
    for (const std::string& tok : tokens) {
        if (std::isdigit(static_cast<unsigned char>(tok[0]))) {
            st.push(std::stoi(tok));
        } else {
            int right = st.top();
            st.pop();
            int left = st.top();
            st.pop();
            if (tok == "+") st.push(left + right);
            else if (tok == "-") st.push(left - right);
            else if (tok == "*") st.push(left * right);
            else st.push(left / right);
        }
    }
    return st.top();
}

int main() {
    assert(evalPostfix(split("3 4 2 * +")) == 11);
    assert(evalPostfix(split("7 2 -")) == 5);
    assert(evalPostfix(toPostfix(split("8 - 3 - 2"))) == 3);
    assert(evalPostfix(toPostfix(split("2 * ( 3 + 4 ) - 5"))) == 9);
    assert((toPostfix(split("3 + 4 * 2")) == std::vector<std::string>{"3", "4", "2", "*", "+"}));

    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Both algorithms scan the token list once, and every token is pushed and popped at most once, so each runs in O(n) time for n tokens. The operand or operator stack can hold up to O(n) items in the worst case, such as deeply nested parentheses or a long chain of numbers before any operator, so the space is O(n). Each stack operation is O(1). Compared with repeatedly searching a string for the highest-precedence operator, which can cost O(n squared), the stack-based approach is much faster on long expressions.

## Common Mistakes & Misconceptions
The most frequent bug is reversing the operands: for subtraction and division, the first value popped is the right operand, so computing `popped1 - popped2` gives the negated result and `8 3 -` wrongly yields -5. Another is using strict greater-than instead of greater-or-equal when comparing precedence, which makes subtraction and division right-associative and gives 8 - (3 - 2) = 7 for 8 - 3 - 2. Students forget to pop the left parenthesis after a closing one, leaving it on the stack, or forget to flush the remaining operators at the end. Multi-digit numbers and negative numbers break a character-by-character scanner unless tokens are separated. Finally, an invalid expression such as "1 2" or "+ 3" leaves the wrong number of values and should be reported as an error, not ignored.

## Builds On
This concept builds on Stack (ADT & implementations): both algorithms are nothing but pushing and popping, and understanding last-in first-out order explains why the most recently seen operands are the first ones an operator consumes. The balanced-bracket idea from the stack concept reappears as matching parentheses in the shunting-yard algorithm.

## Leads To
Compilers use the same idea to turn source expressions into stack-machine code, and expression trees generalise postfix evaluation to trees. Interpreters for calculator languages, spreadsheet formulas and query parsers all use these stack-based techniques.

## Check Yourself
**Q1.** What is the postfix form of 5 + 6 * 7?
**A1.** 5 6 7 * +
**Q2.** When evaluating "9 4 -", which popped value is the left operand?
**A2.** The second one popped (9); the first popped (4) is the right operand, so the result is 5.
**Q3.** Why is no parenthesis handling needed when evaluating postfix?
**A3.** The token order already encodes the evaluation order, so grouping is implicit.
