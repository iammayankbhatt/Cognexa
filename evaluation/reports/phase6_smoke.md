# Phase 6 smoke run: GraphRAG vs plain RAG

Generated 2026-11-20 01:44 UTC by `scripts/phase6_smoke.py`.

- LLM providers: fake:fake-model
- Embeddings: fake-embedding (dim 768)
- Retrieval source: Neo4j (NEO4J_URI) + pgvector (DATABASE_URL)
- Budget 3000 tokens, plain RAG top-k 6, classify threshold 0.55
- Personalisation: none (a new student: every prerequisite counts as weak). Agentic controller: on.

> **Fake mode.** Answers are the deterministic FakeProvider ones (assembled from the retrieved chunks), so only the retrieval columns are meaningful. Re-run with real keys to review real answers (Human Action Needed in progressfile.md).

## Summary

Coverage = gold ids that appear among the concepts of the chunks put in the context.

| id | category | gold concepts | gold prerequisites | GraphRAG concepts | GraphRAG prereqs | plain concepts | plain prereqs |
|---|---|---|---|---|---|---|---|
| ts-001 | direct | bst | - | 1/1 | n/a | 1/1 | n/a |
| ts-002 | direct | dijkstra | - | 1/1 | n/a | 1/1 | n/a |
| ts-023 | unnamed_prerequisite | recursion | call_stack | 1/1 | 1/1 | 1/1 | 1/1 |
| ts-024 | unnamed_prerequisite | recursion | call_stack | 0/1 | 1/1 | 0/1 | 0/1 |
| ts-025 | unnamed_prerequisite | dfs | call_stack | 1/1 | 1/1 | 1/1 | 0/1 |
| ts-026 | unnamed_prerequisite | amortized_analysis | dynamic_arrays | 0/1 | 1/1 | 0/1 | 1/1 |
| ts-050 | multi_concept | bfs, dfs | - | 2/2 | n/a | 0/2 | n/a |
| ts-051 | multi_concept | hash_tables, bst | - | 2/2 | n/a | 0/2 | n/a |
| ts-065 | misconception | binary_search | - | 1/1 | n/a | 1/1 | n/a |
| ts-078 | off_topic | - | - | n/a | n/a | n/a | n/a |

- Gold concepts in context: GraphRAG 9/11 (82%), plain RAG 5/11 (45%)
- Gold prerequisites in context: GraphRAG 4/4 (100%), plain RAG 2/4 (50%)

Review notes (fill in together): are the matched concepts right? Did the answer connect the weak prerequisite? Any hallucinated content outside the context?

# Details

## ts-001 (direct)

> What are binary search trees and how does searching for a key in one work?

### graphrag

- mode: `graphrag`, intent: `explain`, on topic: True
- classification path: `llm`
- matched: `bst` (0.95, llm), `binary_search` (0.90, llm), `tree_basics` (0.68, llm)
- prerequisites: `binary_tree` (d1, weak; binary_tree → bst), `singly_linked_list` (d1, weak; singly_linked_list → tree_basics), `time_complexity` (d1, weak; time_complexity → binary_search), `arrays` (d1, weak; arrays → binary_search), `stack_heap_memory` (d2, weak; stack_heap_memory → singly_linked_list → tree_basics), `pointers_references` (d2, weak; pointers_references → singly_linked_list → tree_basics), `control_flow` (d2, weak; control_flow → arrays → binary_search), `discrete_math_basics` (d2, weak; discrete_math_basics → time_complexity → binary_search)
- related: `hash_sets_maps`
- controller: answer_now (context covers the question)
- context (2967/3000 tokens): `bst/overview`, `binary_search/overview`, `tree_basics/overview`, `binary_tree/overview`, `singly_linked_list/overview`, `bst/intuition`, `bst/mechanism`, `bst/prerequisites`, `binary_search/intuition`, `binary_search/mechanism`, `binary_search/prerequisites`, `tree_basics/intuition`, `tree_basics/mechanism`, `tree_basics/prerequisites`, `binary_tree/pitfalls`, `singly_linked_list/pitfalls`
- citations: `bst`, `binary_search`
- timings (ms): classify 170, traverse 79, gather 30, controller 0, answer 0

Answer:

```text
Here is what the course notes say about "What are binary search trees and how does searching for a key in one work?":

Overview A binary search tree (BST) is a binary tree with an ordering rule: for every node, all keys in its left subtree are smaller than the node's key and all keys in its right subtree are larger. This rule lets search, insert and delete discard half of the remaining tree at each step, in the same way binary search discards half of a sorted array, but with a structure that can grow and shrink cheaply. When the tree is reasonably balanced the operations take O(log n) time, but a plain BST has no balancing mechanism, so in the worst case it degenerates into a chain and the operations take O(n). [[bst]]

Overview Binary search finds a target in a sorted array by repeatedly comparing it with the middle element and discarding the half that cannot contain it. Because each st …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (1057/3000 tokens): `binary_search/next` 0.42, `bst/overview` 0.41, `binary_tree/overview` 0.38, `bst/self_check` 0.38, `hash_sets_maps/mechanism` 0.38, `trie/next` 0.38
- citations: `binary_search`, `bst`
- timings (ms): retrieve 562, answer 0

Answer:

```text
Here is what the course notes say about "What are binary search trees and how does searching for a key in one work?":

Leads To Binary Search Trees store data in a tree shaped like the sequence of binary-search decisions, so insertion and deletion stay fast. Binary search on the answer solves optimisation problems by halving a range of candidates, and balanced tree and database index structures all follow the same halving logic. [[binary_search]]

Overview A binary search tree (BST) is a binary tree with an ordering rule: for every node, all keys in its left subtree are smaller than the node's key and all keys in its right subtree are larger. This rule lets search, insert and delete discard half of the remaining tree at each step, in the same way binary search discards half of a sorted array, but with a structure that can grow and shrink cheaply. When the tree is reasonably balanced the  …
```


## ts-002 (direct)

> Can you explain how Dijkstra's algorithm finds shortest paths?

### graphrag

- mode: `graphrag`, intent: `explain`, on topic: True
- classification path: `llm`
- matched: `dijkstra` (0.95, llm)
- prerequisites: `greedy` (d1, weak; greedy → dijkstra), `bfs` (d1, weak; bfs → dijkstra), `binary_heap` (d1, weak; binary_heap → dijkstra), `graph_representation` (d2, weak; graph_representation → bfs → dijkstra), `binary_tree` (d2, weak; binary_tree → binary_heap → dijkstra), `elementary_sorts` (d2, weak; elementary_sorts → greedy → dijkstra), `priority_queue_adt` (d2, weak; priority_queue_adt → binary_heap → dijkstra), `queue` (d2, weak; queue → bfs → dijkstra)
- related: `bellman_ford`
- controller: answer_now (context covers the question)
- context (2995/3000 tokens): `dijkstra/overview`, `greedy/overview`, `bfs/overview`, `dijkstra/intuition`, `dijkstra/mechanism`, `dijkstra/prerequisites`, `greedy/pitfalls`, `bfs/pitfalls`, `binary_heap/overview`, `binary_heap/pitfalls`, `graph_representation/overview`, `graph_representation/pitfalls`, `binary_tree/overview`, `binary_tree/pitfalls`, `elementary_sorts/overview`, `elementary_sorts/pitfalls`
- citations: `dijkstra`, `greedy`
- timings (ms): classify 15, traverse 15, gather 30, controller 0, answer 0

Answer:

```text
Here is what the course notes say about "Can you explain how Dijkstra's algorithm finds shortest paths?":

Overview Dijkstra's algorithm finds the shortest (least total weight) paths from one source vertex to every other vertex in a graph whose edge weights are all non-negative. It grows a set of vertices whose distance is final, always adding next the vertex with the smallest tentative distance, and then relaxes that vertex's outgoing edges to improve its neighbours' tentative distances. With a binary heap as the priority queue it runs in O((V + E) log V). It is the algorithm behind route planners, network routing protocols such as OSPF, and any problem that asks for a cheapest path with non-negative costs. It fails with negative edge weights, which is where Bellman-Ford takes over. [[dijkstra]]

Overview A greedy algorithm builds a solution step by step, at each step taking the choice  …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (797/3000 tokens): `dijkstra/next` 0.30, `dijkstra/overview` 0.22, `dijkstra/self_check` 0.22, `bellman_ford/overview` 0.21, `string_matching/intuition` 0.21, `bellman_ford/next` 0.20
- citations: `dijkstra`
- timings (ms): retrieve 125, answer 0

Answer:

```text
Here is what the course notes say about "Can you explain how Dijkstra's algorithm finds shortest paths?":

Leads To Bellman-Ford handles graphs with negative edges and detects negative cycles where Dijkstra cannot. A* search adds a heuristic estimate of the remaining distance to guide Dijkstra toward a target, which is what game and map pathfinding use. Dijkstra is also the core of link-state routing protocols, of Johnson's all-pairs algorithm (after reweighting), and of Prim's minimum spanning tree algorithm, which has the same heap-driven structure. [[dijkstra]]

Overview Dijkstra's algorithm finds the shortest (least total weight) paths from one source vertex to every other vertex in a graph whose edge weights are all non-negative. It grows a set of vertices whose distance is final, always adding next the vertex with the smallest tentative distance, and then relaxes that vertex's outg …
```


## ts-023 (unnamed_prerequisite)

> My recursive fibonacci function crashes with RecursionError: maximum recursion depth exceeded when I call it with n = 5000. Why?

### graphrag

- mode: `graphrag`, intent: `debug`, on topic: True
- classification path: `llm`
- matched: `call_stack` (0.95, llm), `recursion` (0.95, llm), `functions` (0.68, llm)
- prerequisites: `stack_heap_memory` (d1, weak; stack_heap_memory → call_stack), `control_flow` (d1, weak; control_flow → functions), `pointers_references` (d2, weak; pointers_references → stack_heap_memory → call_stack), `variables_memory` (d2, weak; variables_memory → control_flow → functions)
- related: `stack`, `divide_and_conquer`, `backtracking`
- controller: answer_now (context covers the question)
- context (2989/3000 tokens): `call_stack/pitfalls`, `recursion/pitfalls`, `functions/pitfalls`, `stack_heap_memory/overview`, `control_flow/overview`, `call_stack/mechanism`, `call_stack/prerequisites`, `recursion/mechanism`, `recursion/prerequisites`, `functions/mechanism`, `functions/prerequisites`, `stack_heap_memory/pitfalls`, `control_flow/pitfalls`, `pointers_references/overview`, `pointers_references/pitfalls`, `variables_memory/overview`, `stack/overview`
- citations: `call_stack`
- timings (ms): classify 0, traverse 78, gather 30, controller 0, answer 0

Answer:

```text
Here is what the course notes say about "My recursive fibonacci function crashes with RecursionError: maximum recursion depth exceeded when I call it with n = 50":

Common Mistakes & Misconceptions The signature symptoms are `RecursionError: maximum recursion depth exceeded` in Python, `StackOverflowError` in Java, and a segmentation fault in C++ when recursion goes too deep. Students who see these often assume the machine is too slow or the memory is full, when the real cause is a missing or unreachable base case or an input that needs more frames than the stack holds. Another misconception is that raising the recursion limit with `sys.setrecursionlimit` fixes the design; it only lets the program crash the interpreter at a larger depth. Students also forget that local variables are separate in each call, so a variable changed in a deeper frame does not change the caller's copy. [[call_s …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (1187/3000 tokens): `recursion/complexity` 0.28, `recurrence_relations/example` 0.26, `recursion/mechanism` 0.25, `recurrence_relations/complexity` 0.24, `recursion/pitfalls` 0.24, `call_stack/example` 0.24
- citations: `recursion`, `recurrence_relations`
- timings (ms): retrieve 110, answer 0

Answer:

```text
Here is what the course notes say about "My recursive fibonacci function crashes with RecursionError: maximum recursion depth exceeded when I call it with n = 50":

Complexity The cost of a recursive function is found by counting calls and the work per call. Factorial makes n calls with constant work each, so it takes O(n) time and O(n) stack space because the depth is n. The recursive list sum above takes O(n squared) time in Python because slicing copies the list on each call, even though the number of calls is n. The naive Fibonacci makes about 1.6 to the power n calls, so it takes exponential time but only O(n) space for the stack depth. A recursion that halves its input each call, as in binary search, takes O(log n) calls and O(log n) stack space. [[recursion]]

Worked Example Solve T(n) = 4T(n/2) + n. [[recurrence_relations]]

How It Works Every correct recursive function has two p …
```


## ts-024 (unnamed_prerequisite)

> My recursive factorial in C++ works for small n but segfaults for very large n. What is happening?

### graphrag

- mode: `graphrag`, intent: `debug`, on topic: True
- classification path: `llm`
- matched: `call_stack` (0.60, llm), `pointers_references` (0.60, llm)
- prerequisites: `stack_heap_memory` (d1, weak; stack_heap_memory → call_stack), `functions` (d1, weak; functions → call_stack), `variables_memory` (d1, weak; variables_memory → pointers_references), `control_flow` (d2, weak; control_flow → functions → call_stack)
- related: `stack`
- controller: answer_now (context covers the question)
- context (2711/3000 tokens): `call_stack/pitfalls`, `pointers_references/pitfalls`, `stack_heap_memory/overview`, `functions/overview`, `call_stack/mechanism`, `call_stack/prerequisites`, `pointers_references/mechanism`, `pointers_references/prerequisites`, `stack_heap_memory/pitfalls`, `functions/pitfalls`, `variables_memory/overview`, `variables_memory/pitfalls`, `control_flow/overview`, `control_flow/pitfalls`, `stack/overview`, `stack/pitfalls`
- citations: `call_stack`, `pointers_references`
- timings (ms): classify 14, traverse 47, gather 15, controller 0, answer 14

Answer:

```text
Here is what the course notes say about "My recursive factorial in C++ works for small n but segfaults for very large n. What is happening?":

Common Mistakes & Misconceptions The signature symptoms are `RecursionError: maximum recursion depth exceeded` in Python, `StackOverflowError` in Java, and a segmentation fault in C++ when recursion goes too deep. Students who see these often assume the machine is too slow or the memory is full, when the real cause is a missing or unreachable base case or an input that needs more frames than the stack holds. Another misconception is that raising the recursion limit with `sys.setrecursionlimit` fixes the design; it only lets the program crash the interpreter at a larger depth. Students also forget that local variables are separate in each call, so a variable changed in a deeper frame does not change the caller's copy. [[call_stack]]

Common Mistake …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (1747/3000 tokens): `asymptotic_notation/mechanism` 0.43, `stack/complexity` 0.42, `asymptotic_notation/code` 0.41, `recurrence_relations/complexity` 0.39, `time_complexity/mechanism` 0.39, `complexity_classes/complexity` 0.37
- citations: `asymptotic_notation`, `stack`
- timings (ms): retrieve 110, answer 0

Answer:

```text
Here is what the course notes say about "My recursive factorial in C++ works for small n but segfaults for very large n. What is happening?":

How It Works Formally, f(n) is O(g(n)) if there are positive constants c and n0 such that f(n) is at most c times g(n) for every n at least n0. In words: beyond some starting point, f stays under a constant multiple of g. For example 3n squared + 5n is O(n squared): choose c = 4 and n0 = 5, because 3n squared + 5n is at most 4n squared whenever 5n is at most n squared, which holds for n at least 5. [[asymptotic_notation]]

Complexity Push, pop, peek, isEmpty and size are all O(1): amortized for a dynamic-array stack and worst-case for a linked-list stack. Space is O(n) for n stored items. The bracket checker runs in O(n) time over n characters and uses O(n) extra space in the worst case, when every character is an opening bracket. Searching for an …
```


## ts-025 (unnamed_prerequisite)

> Why does my recursive DFS on a 1000 x 1000 grid in Python crash before visiting all the cells?

### graphrag

- mode: `graphrag`, intent: `debug`, on topic: True
- classification path: `llm`
- matched: `dfs` (0.60, llm)
- prerequisites: `graph_representation` (d1, weak; graph_representation → dfs), `stack` (d1, weak; stack → dfs), `recursion` (d1, weak; recursion → dfs), `singly_linked_list` (d2, weak; singly_linked_list → graph_representation → dfs), `call_stack` (d2, weak; call_stack → recursion → dfs), `arrays` (d2, weak; arrays → graph_representation → dfs)
- related: `dfs_tree_traversals`, `backtracking`
- controller: answer_now (context covers the question)
- context (2858/3000 tokens): `dfs/pitfalls`, `graph_representation/overview`, `stack/overview`, `dfs/mechanism`, `dfs/prerequisites`, `graph_representation/pitfalls`, `stack/pitfalls`, `recursion/overview`, `recursion/pitfalls`, `singly_linked_list/overview`, `singly_linked_list/pitfalls`, `call_stack/overview`, `call_stack/pitfalls`, `arrays/overview`, `arrays/pitfalls`, `dfs_tree_traversals/overview`
- citations: `dfs`
- timings (ms): classify 14, traverse 15, gather 30, controller 0, answer 0

Answer:

```text
Here is what the course notes say about "Why does my recursive DFS on a 1000 x 1000 grid in Python crash before visiting all the cells?":

Common Mistakes & Misconceptions The usual crash is a RecursionError or stack overflow on a long chain or large grid, because the recursion depth equals the path length; the cure is an iterative version or a larger limit. Forgetting the visited set makes DFS loop forever on any graph with a cycle, including every undirected graph (each edge leads back). Students mark vertices visited when they push them in the iterative version and then get an order that differs from the recursive one, or mark nothing at pop time and process duplicates. People expect DFS to find the shortest path to a vertex; the first path it finds can be very long. In directed graphs, confusing a cross or forward edge with a back edge leads to false cycle reports, because only an ed …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (876/3000 tokens): `cycle_detection/pitfalls` 0.33, `dfs/complexity` 0.31, `strings/self_check` 0.31, `dfs/pitfalls` 0.31, `cycle_detection/self_check` 0.30, `binary_search/intuition` 0.28
- citations: `cycle_detection`, `dfs`
- timings (ms): retrieve 125, answer 0

Answer:

```text
Here is what the course notes say about "Why does my recursive DFS on a 1000 x 1000 grid in Python crash before visiting all the cells?":

Common Mistakes & Misconceptions The most common bug in directed graphs is using a single visited flag, which reports a cycle whenever two paths meet at the same vertex, as in a diamond; only an edge to a vertex still on the current path (grey) means a cycle. In undirected graphs the opposite mistake is forgetting to skip the parent, so every graph with at least one edge "has a cycle". Students apply the undirected method to a directed graph or the reverse. Forgetting to reset a vertex from grey to black after exploring it makes later branches see false back edges. Only starting DFS from vertex 0 misses cycles in other components. In recursive code on large graphs, the recursion limit can be hit before any cycle is found; an iterative version avoids i …
```


## ts-026 (unnamed_prerequisite)

> Why is appending to a Python list O(1) on average when the list sometimes has to copy all its elements?

### graphrag

- mode: `graphrag`, intent: `complexity`, on topic: True
- classification path: `llm`
- matched: `dynamic_arrays` (0.75, llm), `time_complexity` (0.75, llm), `arrays` (0.60, llm)
- prerequisites: `pointers_references` (d1, weak; pointers_references → dynamic_arrays), `control_flow` (d1, weak; control_flow → time_complexity), `discrete_math_basics` (d1, weak; discrete_math_basics → time_complexity), `variables_memory` (d2, weak; variables_memory → pointers_references → dynamic_arrays)
- related: `singly_linked_list`
- controller: answer_now (context covers the question)
- context (2143/3000 tokens): `dynamic_arrays/complexity`, `time_complexity/complexity`, `arrays/complexity`, `pointers_references/overview`, `control_flow/overview`, `dynamic_arrays/overview`, `time_complexity/overview`, `arrays/overview`, `pointers_references/pitfalls`, `control_flow/pitfalls`, `discrete_math_basics/overview`, `discrete_math_basics/pitfalls`, `variables_memory/overview`, `variables_memory/pitfalls`, `singly_linked_list/overview`, `singly_linked_list/pitfalls`
- citations: `dynamic_arrays`, `time_complexity`
- timings (ms): classify 0, traverse 78, gather 31, controller 0, answer 0

Answer:

```text
Here is what the course notes say about "Why is appending to a Python list O(1) on average when the list sometimes has to copy all its elements?":

Complexity Indexing and setting are O(1). Appending is O(1) amortized and O(n) in the worst case when a resize happens. Removing the last item is O(1). Inserting or deleting at an arbitrary index is O(n) because of shifting. Searching an unsorted dynamic array is O(n). The memory used is O(n), between one and two times the number of stored items for a doubling strategy, because unused capacity is kept in reserve. [[dynamic_arrays]]

Complexity This section describes the common classes themselves. O(1) means the work does not depend on n, like reading an array element. O(log n) halves the problem each step, like binary search. O(n) touches each item once, like linear search. O(n log n) is the cost of efficient sorting. O(n squared) arises from …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (1325/3000 tokens): `dynamic_arrays/pitfalls` 0.48, `hash_tables/mechanism` 0.44, `functions/self_check` 0.43, `pointers_references/pitfalls` 0.42, `arrays/mechanism` 0.41, `tree_basics/prerequisites` 0.40
- citations: `dynamic_arrays`, `hash_tables`, `functions`
- timings (ms): retrieve 109, answer 15

Answer:

```text
Here is what the course notes say about "Why is appending to a Python list O(1) on average when the list sometimes has to copy all its elements?":

Common Mistakes & Misconceptions Students are often surprised that `list.append` is described as O(1) while an occasional append is slow: the cost is amortized, not constant every time. Another mistake is inserting at the front of a Python list in a loop (`list.insert(0, x)`), which is O(n) each time and makes the loop quadratic. In C++, keeping a pointer or iterator to a vector element and then calling push_back can leave a dangling reference after reallocation, giving crashes or garbage. People also assume that a list's capacity equals its length; the unused slots are real memory. Finally, using `list * n` to create a list of lists makes n references to the same inner list, a pointer aliasing bug rather than a dynamic array issue. [[dynamic …
```


## ts-050 (multi_concept)

> Compare BFS and DFS: how do they differ and when should I use each?

### graphrag

- mode: `graphrag`, intent: `compare`, on topic: True
- classification path: `llm`
- matched: `bfs` (0.60, llm), `dfs` (0.60, llm)
- prerequisites: `graph_representation` (d1, weak; graph_representation → bfs), `queue` (d1, weak; queue → bfs), `stack` (d1, weak; stack → dfs), `recursion` (d1, weak; recursion → dfs), `singly_linked_list` (d2, weak; singly_linked_list → graph_representation → bfs), `call_stack` (d2, weak; call_stack → recursion → dfs), `arrays` (d2, weak; arrays → graph_representation → bfs)
- related: `level_order_traversal`, `dfs_tree_traversals`, `backtracking`
- controller: answer_now (context covers the question)
- context (2948/3000 tokens): `bfs/overview`, `dfs/overview`, `graph_representation/overview`, `queue/overview`, `bfs/complexity`, `bfs/pitfalls`, `dfs/complexity`, `dfs/pitfalls`, `graph_representation/pitfalls`, `queue/pitfalls`, `stack/overview`, `stack/pitfalls`, `recursion/overview`, `recursion/pitfalls`, `singly_linked_list/overview`, `singly_linked_list/pitfalls`, `call_stack/overview`, `call_stack/pitfalls`
- citations: `bfs`, `dfs`
- timings (ms): classify 0, traverse 45, gather 32, controller 0, answer 0

Answer:

```text
Here is what the course notes say about "Compare BFS and DFS: how do they differ and when should I use each?":

Overview Breadth-first search (BFS) explores a graph in layers: first the start vertex, then all vertices one edge away, then all vertices two edges away, and so on. It uses a queue so that vertices discovered earlier are expanded earlier, and a visited marker so that no vertex is processed twice even when the graph has cycles. The main reason to use BFS is that, in an unweighted graph, the first time it reaches a vertex is along a path with the fewest edges, so BFS computes shortest path lengths from the start. It is also used to test reachability, count connected components, find the shortest route through a maze or a word ladder, and spread a signal level by level. [[bfs]]

Overview Depth-first search (DFS) explores a graph by going as deep as possible along one path before  …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (468/3000 tokens): `dp_classic/next` 0.38, `hash_tables/next` 0.33, `discrete_math_basics/next` 0.30, `space_complexity/next` 0.29, `variables_memory/next` 0.29, `control_flow/next` 0.29
- citations: `dp_classic`, `hash_tables`, `discrete_math_basics`, `space_complexity`
- timings (ms): retrieve 110, answer 0

Answer:

```text
Here is what the course notes say about "Compare BFS and DFS: how do they differ and when should I use each?":

Leads To These problems are templates for many applications: diff tools and version control use LCS, spell checkers and DNA sequence alignment (Needleman-Wunsch, Smith-Waterman) use edit distance, resource allocation and budgeting use knapsack, and patience sorting and scheduling use LIS. They also lead to the idea of pseudo-polynomial time and NP-hardness, and to more advanced DP such as interval DP, bitmask DP and DP on trees. [[dp_classic]]

Leads To Hash Sets & Maps in Practice shows how built-in dictionaries and sets use these ideas for counting, grouping and membership tests. The same structures underlie caches and symbol tables, and hash-based partitioning is used in databases and distributed systems. [[hash_tables]]

Leads To Time complexity and Big-O rely directly on l …
```


## ts-051 (multi_concept)

> When should I use a hash table instead of a binary search tree?

### graphrag

- mode: `graphrag`, intent: `explain`, on topic: True
- classification path: `llm`
- matched: `bst` (0.95, llm), `hash_tables` (0.95, llm), `binary_search` (0.90, llm)
- prerequisites: `binary_tree` (d1, weak; binary_tree → bst), `hash_functions` (d1, weak; hash_functions → hash_tables), `singly_linked_list` (d1, weak; singly_linked_list → hash_tables), `time_complexity` (d1, weak; time_complexity → binary_search), `arrays` (d1, weak; arrays → binary_search), `tree_basics` (d2, weak; tree_basics → binary_tree → bst), `stack_heap_memory` (d2, weak; stack_heap_memory → singly_linked_list → hash_tables), `pointers_references` (d2, weak; pointers_references → singly_linked_list → hash_tables), `control_flow` (d2, weak; control_flow → arrays → binary_search), `discrete_math_basics` (d2, weak; discrete_math_basics → hash_functions → hash_tables)
- related: `hash_sets_maps`
- controller: answer_now (context covers the question)
- context (2946/3000 tokens): `bst/overview`, `hash_tables/overview`, `binary_search/overview`, `binary_tree/overview`, `hash_functions/overview`, `bst/intuition`, `bst/mechanism`, `bst/prerequisites`, `hash_tables/intuition`, `hash_tables/mechanism`, `hash_tables/prerequisites`, `binary_search/intuition`, `binary_search/mechanism`, `binary_search/prerequisites`, `binary_tree/pitfalls`, `hash_functions/pitfalls`
- citations: `bst`, `hash_tables`
- timings (ms): classify 0, traverse 77, gather 47, controller 0, answer 0

Answer:

```text
Here is what the course notes say about "When should I use a hash table instead of a binary search tree?":

Overview A binary search tree (BST) is a binary tree with an ordering rule: for every node, all keys in its left subtree are smaller than the node's key and all keys in its right subtree are larger. This rule lets search, insert and delete discard half of the remaining tree at each step, in the same way binary search discards half of a sorted array, but with a structure that can grow and shrink cheaply. When the tree is reasonably balanced the operations take O(log n) time, but a plain BST has no balancing mechanism, so in the worst case it degenerates into a chain and the operations take O(n). [[bst]]

Overview A hash table stores key-value pairs in an array and uses a hash function to compute where each key belongs, so insertion, lookup and deletion take expected constant time re …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (1439/3000 tokens): `binary_tree/pitfalls` 0.50, `binary_tree/self_check` 0.44, `hash_functions/overview` 0.44, `fenwick_tree/overview` 0.44, `functions/pitfalls` 0.43, `binary_heap/code` 0.43
- citations: `binary_tree`
- timings (ms): retrieve 125, answer 0

Answer:

```text
Here is what the course notes say about "When should I use a hash table instead of a binary search tree?":

Common Mistakes & Misconceptions A common symptom is an AttributeError or segmentation fault on "None" or null when code reads node.left.value without checking that the child exists. Another is a stack overflow in recursive height or size on a very skewed tree with many thousands of nodes. Students use "full", "complete" and "perfect" interchangeably, although they differ: a complete tree can have a node with one child, a full tree need not be complete. Height is miscounted by one when an empty tree is treated as height 0 instead of -1, and some assume every binary tree is balanced, when inserting sorted data into an ordinary binary search tree produces a chain. [[binary_tree]]

Check Yourself **Q1.** How many nodes does a perfect binary tree of height 3 have? **A1.** 15, because 2 …
```


## ts-065 (misconception)

> Binary search works on any array, right? I tried it on my list of scores and it misses values.

### graphrag

- mode: `graphrag`, intent: `explain`, on topic: True
- classification path: `llm`
- matched: `arrays` (0.95, llm), `binary_search` (0.90, llm), `bst` (0.60, llm)
- prerequisites: `binary_tree` (d1, weak; binary_tree → bst), `time_complexity` (d1, weak; time_complexity → binary_search), `control_flow` (d1, weak; control_flow → arrays), `tree_basics` (d2, weak; tree_basics → binary_tree → bst), `variables_memory` (d2, weak; variables_memory → control_flow → arrays), `discrete_math_basics` (d2, weak; discrete_math_basics → time_complexity → binary_search)
- related: `singly_linked_list`, `hash_sets_maps`
- controller: answer_now (context covers the question)
- context (2908/3000 tokens): `arrays/overview`, `binary_search/overview`, `bst/overview`, `binary_tree/overview`, `time_complexity/overview`, `arrays/intuition`, `arrays/mechanism`, `arrays/prerequisites`, `binary_search/intuition`, `binary_search/mechanism`, `binary_search/prerequisites`, `bst/intuition`, `bst/mechanism`, `bst/prerequisites`, `binary_tree/pitfalls`, `time_complexity/pitfalls`, `control_flow/overview`
- citations: `arrays`, `binary_search`
- timings (ms): classify 0, traverse 77, gather 31, controller 0, answer 0

Answer:

```text
Here is what the course notes say about "Binary search works on any array, right? I tried it on my list of scores and it misses values.":

Overview An array stores a fixed number of elements of the same type in one continuous block of memory. Each element is reached by its index, a position counted from zero. Because the elements sit side by side, the computer can jump straight to any index in constant time, which makes arrays the simplest and fastest way to store a collection. The price is rigidity: the size is fixed when the array is created, and inserting or removing in the middle requires shifting other elements. [[arrays]]

Overview Binary search finds a target in a sorted array by repeatedly comparing it with the middle element and discarding the half that cannot contain it. Because each step halves the search range, it needs only about log2 n comparisons, so a billion items take a …
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (714/3000 tokens): `dijkstra/prerequisites` 0.38, `binary_search/prerequisites` 0.38, `bst/prerequisites` 0.37, `dynamic_arrays/prerequisites` 0.36, `string_matching/prerequisites` 0.34, `binary_search/next` 0.34
- citations: `dijkstra`, `binary_search`
- timings (ms): retrieve 108, answer 0

Answer:

```text
Here is what the course notes say about "Binary search works on any array, right? I tried it on my list of scores and it misses values.":

Builds On This concept builds on Breadth-First Search: Dijkstra keeps the same structure of a frontier that expands from the source and settles vertices in order of distance, but orders the frontier by total weight rather than by edge count. It builds on Binary Heap, because the min-heap is what returns the closest unsettled vertex in O(log V) and makes the algorithm fast on sparse graphs. It also builds on Greedy Algorithms: at each step it makes the locally best choice (settle the nearest vertex) and never revisits it, and the correctness proof is a classic greedy-choice argument that relies on non-negative weights. [[dijkstra]]

Builds On This concept builds on Arrays: it relies on constant-time access to any index, so that jumping to the middle is …
```


## ts-078 (off_topic)

> Can you give me a good recipe for chocolate chip cookies?

### graphrag

- mode: `graphrag`, intent: `explain`, on topic: False
- classification path: `none`
- matched: none
- context (0/3000 tokens): none
- timings (ms): classify 16

Answer:

```text
I'm Cognexa, a tutor for Data Structures & Algorithms, so I can't help with that one. I can explain topics like recursion and the call stack, arrays and linked lists, hashing, sorting, binary search trees, graph traversal or dynamic programming. What would you like to learn?
```

### plain_rag

- mode: `plain_rag`, intent: `explain`, on topic: True
- context (760/3000 tokens): `doubly_circular_linked_list/intuition` 0.35, `connectivity_scc/intuition` 0.33, `backtracking/intuition` 0.32, `graph_representation/intuition` 0.30, `dfs/intuition` 0.28, `topological_sort/next` 0.28
- citations: `doubly_circular_linked_list`, `connectivity_scc`
- timings (ms): retrieve 108, answer 0

Answer:

```text
Here is what the course notes say about "Can you give me a good recipe for chocolate chip cookies?":

Intuition A singly linked list is a one-way street: you can only drive forward, and to turn around you must go back to the start. A doubly linked list is a two-way street: every house knows its neighbour on each side, so you can leave in either direction, and a house can be demolished without anyone searching for its predecessor. A circular list is a roundabout: keep going forward and you arrive back where you started. [[doubly_circular_linked_list]]

Intuition For an undirected graph, think of islands joined by two-way bridges: a component is everything you can walk to from where you stand. For a directed graph, imagine a city of one-way streets. A strongly connected district is a set of intersections where you can drive from any one to any other and come back. You might be able to driv …
```
