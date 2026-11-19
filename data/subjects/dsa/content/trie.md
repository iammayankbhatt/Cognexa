---
id: trie
name: "Trie"
cluster: trees
reviewed: false
sources:
  - "CLRS, Problem 12-2 (Radix trees)"
  - "Sedgewick and Wayne, Algorithms 4th ed., Section 5.2 (Tries)"
---

## Overview
A trie, also called a prefix tree, stores a set of strings in a tree where each edge is labelled with one character and the path from the root to a node spells a prefix. A flag on a node marks that the prefix ending there is a complete stored word. Because words that share a prefix share the same path, a trie answers "is this word present?" and "which words start with this prefix?" in time proportional to the length of the query, independent of how many words are stored. Tries power autocomplete, spell checkers, IP routing tables and dictionary games.

## Intuition
Imagine a phone's predictive keyboard. As you type "ca", the keyboard has already narrowed the dictionary to words beginning with "ca", and each new letter narrows it further. A trie is that narrowing made physical: the first letter chooses a branch, the next letter chooses a sub-branch, and so on. The words "car", "card" and "care" travel along the same path c, a, r and only separate at the end, so shared beginnings are stored once.

## How It Works
Node structure. Each node has a collection of children indexed by character (a fixed array of 26 slots for lowercase letters, or a hash map for general alphabets) and a boolean is_end that says whether a word finishes at this node. The root represents the empty prefix.

Insert a word. Start at the root. For each character, follow the child for that character, creating it if it does not exist. After the last character mark that node as a word end. The work is O(L) for a word of length L.

Search for a word. Follow the characters from the root. If any child is missing the word is absent. If you reach the end of the word, the word is present only if the final node has is_end set; otherwise the string is just a prefix of other words.

Prefix query (starts-with). Same walk as search, but you only need the path to exist. To list all words with a prefix, walk to the prefix node and then run a depth-first traversal of its subtree, collecting every node marked as a word end.

Delete. Unmark the end flag, and then walk back up removing nodes that have no children and are not word ends, so the trie does not keep unused branches.

Trade-offs. Array-based children give O(1) transitions but waste memory when most slots are empty: 26 references per node for a lowercase alphabet. A hash-map child table saves memory for sparse nodes and supports large alphabets, at the cost of hashing overhead. A compressed trie (radix tree) merges chains of single-child nodes to save space.

## Worked Example
Insert the words "to", "tea", "ten" and "inn". Insert "to": nodes t, o with o marked as an end. Insert "tea": follow t (it exists), then add e, a with a marked. Insert "ten": follow t, e, then add n marked. Insert "inn": a new branch i, n, n with the last n marked.

```
        (root)
        /    \
       t      i
      / \      \
     o*  e      n
        / \      \
       a*  n*     n*
```

Search "te": walk t, e. Both exist, but e is not marked as a word end, so "te" is not a word. Starts-with "te" is true. Words with prefix "te": go to node e and collect "tea" and "ten". Search "tin": t exists, but t has no child i, so the search fails at the second character after only two steps.

## Code
```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for ch in word:
            node = node.children.setdefault(ch, TrieNode())
        node.is_end = True

    def _walk(self, text):
        node = self.root
        for ch in text:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def search(self, word):
        node = self._walk(word)
        return node is not None and node.is_end

    def starts_with(self, prefix):
        return self._walk(prefix) is not None

    def words_with_prefix(self, prefix):
        node, out = self._walk(prefix), []
        if node is None:
            return out

        def collect(n, path):
            if n.is_end:
                out.append(path)
            for ch in sorted(n.children):
                collect(n.children[ch], path + ch)

        collect(node, prefix)
        return out


t = Trie()
for w in ["to", "tea", "ten", "inn"]:
    t.insert(w)
assert t.search("tea") and t.search("to")
assert not t.search("te") and not t.search("tin") and not t.search("")
assert t.starts_with("te") and not t.starts_with("x")
assert t.words_with_prefix("te") == ["tea", "ten"]
assert t.words_with_prefix("") == ["inn", "tea", "ten", "to"]
assert t.words_with_prefix("z") == []
print("all checks passed")
```

```cpp
#include <algorithm>
#include <array>
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

struct TrieNode {
    std::array<TrieNode*, 26> next{};
    bool isEnd = false;
};

class Trie {
public:
    Trie() : root(new TrieNode()) {}
    ~Trie() { destroy(root); }

    void insert(const std::string& word) {
        TrieNode* node = root;
        for (char ch : word) {
            int i = ch - 'a';
            if (!node->next[i]) node->next[i] = new TrieNode();
            node = node->next[i];
        }
        node->isEnd = true;
    }

    bool search(const std::string& word) const {
        const TrieNode* n = walk(word);
        return n && n->isEnd;
    }

    bool startsWith(const std::string& prefix) const { return walk(prefix) != nullptr; }

private:
    TrieNode* root;

    const TrieNode* walk(const std::string& s) const {
        const TrieNode* node = root;
        for (char ch : s) {
            node = node->next[ch - 'a'];
            if (!node) return nullptr;
        }
        return node;
    }

    static void destroy(TrieNode* n) {
        if (!n) return;
        for (TrieNode* c : n->next) destroy(c);
        delete n;
    }
};

int main() {
    Trie t;
    for (const char* w : {"to", "tea", "ten", "inn"}) t.insert(w);
    assert(t.search("tea") && t.search("to"));
    assert(!t.search("te") && !t.search("tin"));
    assert(t.startsWith("te") && !t.startsWith("x"));
    std::cout << "all checks passed\n";
    return 0;
}
```

## Complexity
Insert, search and starts-with each take O(L) time for a string of length L, no matter how many words are stored, which beats a balanced search tree of strings where each comparison itself costs O(L) and there are O(log n) comparisons. Listing all words under a prefix costs time proportional to the size of the subtree. Space is O(total characters) in the worst case, which is the sum of all word lengths when nothing is shared, multiplied by the per-node overhead: an array of 26 slots uses about 26 references per node, while a hash map grows with the actual number of children.

## Common Mistakes & Misconceptions
The classic bug is returning true from search when the walk succeeds, without checking the end flag, so "te" is wrongly found after inserting "tea". Another is forgetting to set the end flag on the last node, making search always fail. With array children, indexing by ch - 'a' fails with an IndexError or out-of-bounds access if the input contains uppercase letters, digits or spaces. Students assume a trie always saves memory, but a trie of unrelated long words uses much more than a plain list, because every character becomes a node. Deleting a word by just clearing its flag, or by removing nodes that other words still use, corrupts the structure. People also confuse a trie with a hash set: a hash set cannot answer prefix queries efficiently.

## Builds On
This concept builds on Tree Terminology & Properties. A trie is a rooted tree, so the root, path, depth (the length of the prefix) and subtree (all words with that prefix) all come from there, and the n - 1 edges property still holds. It also builds on Strings: a trie works with strings character by character, so understanding string indexing, characters as array indexes (ch - 'a') and the cost of operations proportional to string length is directly needed.

## Leads To
Autocomplete and spell-check use prefix queries. Compressed tries and suffix trees underpin fast substring search, and String Matching algorithms such as KMP and Rabin-Karp solve a related problem of finding a pattern in text by other means. Binary tries on bits are used in IP routing tables for longest-prefix matching, and the Aho-Corasick algorithm builds failure links on a trie to search for many patterns at once.

## Check Yourself
**Q1.** How long does searching a trie for a word of length L take?
**A1.** O(L), independent of the number of stored words.
**Q2.** Why does each node need an end-of-word flag?
**A2.** Because a prefix of a stored word is not itself a stored word unless it was inserted.
**Q3.** What is the main memory cost of an array-based trie node?
**A3.** One slot per alphabet letter (for example 26 references), even if most are empty.
