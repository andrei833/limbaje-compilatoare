# Explanation of Labs L1–L6

Your labs build the first stages of a compiler for a **process-management DSL**.
A DSL is a language designed for one specific purpose—in your case, describing
services, their dependencies, and actions such as starting or stopping them.

| Lab | Main question | What you produce |
|---|---|---|
| L1 | What does the language look like? | Language description and grammar |
| L2 | Can we write programs in it? | Example programs and grammar review |
| L3 | What tokens occur in a program? | Scanner, symbol table, PIF |
| L4 | How can we formally recognize individual tokens? | Finite automata and regular grammars |
| L5 | Can those automata recognize tokens inside programs? | Scanner using finite automata |
| L6 | Are the tokens arranged according to the grammar? | Parser and production string |

The following program illustrates the language:

```text
process net;
process db { depends_on: net };
group core = [net, db];

for (node in core) {
    start(node);
}
```

## L1 — Define the language

In [L1’s description](L1/process-lang%20doc.txt), you decide what programmers
can express.

Your language includes:

- Process declarations: `process net;`
- Dependencies: `process db { depends_on: net };`
- Groups: `group core = [net, db];`
- Commands: `start`, `stop`, `enable`, `disable`.
- Queries: `status(net)` and `autostart(net)`.
- Conditions: `if (...) { ... } else { ... }`
- Loops: `for (node in core) { ... }`

`start` and `stop` concern whether a process runs. `enable` and `disable`
concern automatic startup.

You also define the **syntax**, meaning the allowed structure, using BNF:

```text
<process_dec> ::= "process" <identifier> <process_body> ";"
```

This says that a process declaration must contain:

1. The keyword `process`.
2. An identifier.
3. An optional process body.
4. A semicolon.

The optional body is expressed through:

```text
<process_body> ::= "{" "depends_on" ":" <identifier_list> "}"
                | epsilon
```

Here:

- `::=` means “can be formed as.”
- `|` separates alternatives.
- **Terminals** are actual language tokens, such as `process` and `;`.
- **Nonterminals** describe structures, such as `<process_dec>`.
- **epsilon** means the empty string: nothing appears there.

Therefore, both declarations are allowed:

```text
process net;
process db { depends_on: net };
```

L1 defines what these statements should mean, but it does not implement their
execution.

## L2 — Write programs and review the grammar

In [L2](L2/program-1.txt), you use the language to write complete examples.

For example:

```text
if (status(db) == RUNNING) {
    enable(api);
    start(api);
} else {
    disable(api);
    stop(api);
}
```

This demonstrates that the language can express decisions and sequences of
actions.

L2 also contains [a grammar review](L2/genai-validation.md). It identifies
issues such as `<proecess_dec>` being a misspelling of `<process_dec>`.

It also separates `depends_on` and `:` into two tokens. That allows either:

```text
depends_on: net
depends_on : net
```

The purpose of L2 is to exercise and refine the language design before building
the scanner and parser.

## L3 — Build the first scanner

[L3’s scanner](L3/01_lexical_analysis/lexer.py) performs **lexical analysis**.
It reads source characters and groups them into tokens.

For:

```text
process net;
```

it recognizes:

```text
process    → keyword
net        → identifier
;          → separator
```

A **lexeme** is the actual text, such as `net`. A **token category** says what
kind of text it is, such as `IDENTIFIER`.

Your L3 scanner uses regular expressions. The identifier pattern is:

```text
[A-Za-z][A-Za-z0-9_]*
```

This means:

- First character: an ASCII letter.
- Remaining characters: zero or more letters, digits, or underscores.

Examples:

```text
net         valid
node2       valid
data_tier   valid
2node       invalid
_node       invalid
```

The scanner processes whole words, so `12abc` is reported as one invalid token.

The recognition order matters:

```text
constants → keywords/fixed tokens → identifiers
```

For example, `true` matches the identifier pattern, but the language reserves it
as a constant. Checking constants first gives it the correct category.

L3 creates two main structures: the **symbol table** and the **PIF**.

### Symbol table

The **symbol table**, or ST, stores each distinct identifier or constant once.
Your implementation is in [C](L3/02_symbol_table/symbol_table.c), with Python
accessing it through CFFI.

It uses a hash table with 101 buckets:

```text
bucket = sum of character codes % 101
```

For `net`:

```text
110 + 101 + 116 = 327
327 % 101 = 24
```

If it is the first entry in that bucket, its reference is:

```text
(24, 0)
```

Different words can have the same hash. This is a **collision**. Your
implementation handles collisions using linked lists, so entries in the same
bucket have different positions.

### Program Internal Form

The **Program Internal Form**, or PIF, stores every token occurrence in source
order:

| Token/category | ST reference | Value |
|---|---|---|
| `process` | `(-1, -1)` | `process` |
| `IDENTIFIER` | `(24, 0)` | `net` |
| `;` | `(-1, -1)` | `;` |

`(-1, -1)` means that a fixed token does not need an ST entry.

If `net` appears ten times, the PIF contains ten occurrences, all pointing to
the same symbol-table entry.

L3 writes:

```text
st.csv       distinct identifiers and constants
pif.csv      token occurrences in source order
errors.csv   invalid lexemes and their positions
```

## L4 — Define finite automata and regular grammars

[L4](L4/automata.py) formalizes how to recognize individual identifiers and
constants.

A **finite automaton** reads characters one at a time and changes state.
Its formal definition is:

```text
M = (Q, Σ, δ, q0, F)
```

| Component | Meaning |
|---|---|
| `Q` | Set of states |
| `Σ` | Allowed input characters |
| `δ` | Transition function |
| `q0` | Initial state |
| `F` | Accepting states |

Your identifier automaton has two states:

```text
q0 --letter--> q1
q1 --letter, digit, or underscore--> q1
```

`q1` is accepting.

Reading `net2` works like this:

```text
q0 --n--> q1 --e--> q1 --t--> q1 --2--> q1
```

The input finishes in an accepting state, so the word is accepted.

Reading `2net` fails immediately because there is no transition from `q0` on
`2`.

Your constant automaton recognizes exactly:

```text
true
false
RUNNING
STOPPED
ERROR
```

For `true`, it follows:

```text
q0 → q_t → q_tr → q_tru → q_true
```

Only the complete word reaches an accepting state.

### Convert an automaton to a regular grammar

L4 also converts an automaton into an equivalent **regular grammar**:

1. Every state becomes a nonterminal.
2. Every transition `δ(q, a) = r` becomes `q → a r`.
3. Every accepting state gets `q → epsilon`.
4. The initial state becomes the grammar’s start symbol.

For example:

```text
q0 --n--> q1
```

becomes:

```text
q0 → n q1
```

An accepting `q1` also gets:

```text
q1 → epsilon
```

The automaton and its regular grammar recognize exactly the same words.

These grammars describe **individual tokens**. L1’s grammar describes
**whole program structures**, including nested statements.

## L5 — Integrate the automata into the scanner

[L5’s scanner](L5/01_lexical_analysis/lexer.py) connects L3 and L4.

It keeps L3’s:

- Token inventory.
- C symbol table.
- PIF structure.
- CSV output.

It replaces regular-expression recognition with explicit finite automata.

Its main flow is:

```text
source text
    ↓
split into candidate words and symbols
    ↓
classify each candidate
    ↓
update symbol table and PIF, or report an error
```

The important functions are:

| Function | Purpose |
|---|---|
| `load_tokens()` | Reads token names and numeric codes |
| `scan_tokens()` | Separates source text into candidates |
| `classify_token()` | Recognizes constants, fixed tokens, or identifiers |
| `analyze()` | Collects PIF, ST, and errors |
| `save_tables()` | Writes the CSV files |

Two details are especially useful.

First, symbols are checked longest first:

```text
== before =
```

Otherwise, `==` could incorrectly become two assignment tokens.

Second, words are recognized as a whole:

```text
trueValue
```

is one identifier, rather than constant `true` followed by identifier `Value`.

Similarly, `RUNN` is a valid identifier even though it is not a complete state
constant.

**L5 still does not check statement structure.**

For example:

```text
process ; net
```

contains valid tokens, so lexical analysis succeeds. Their order is a problem
for L6.

## L6 — Parse the tokens using the grammar

L6 performs **syntactical analysis**.

Its input is either:

- Source code, scanned by [the PLY lexer](L6/lexer.py).
- A previously generated PIF CSV.

Both feed [the same Yacc parser](L6/parser.py).

In source mode, L6 uses its own PLY scanner. It does not call L5’s
automata-based scanner. PIF mode is how it directly reuses L5’s output.

PLY Yacc uses **LALR(1) bottom-up shift-reduce parsing**. It maintains a stack
and consults parsing tables using the current state and next token.

Its actions are:

| Action | Meaning |
|---|---|
| Shift | Consume the next token and push it onto the stack |
| Reduce | Replace a recognized rule’s right-hand side with its left-hand side |
| Accept | The complete input matches the grammar |
| Error | No valid parsing action exists |

For:

```text
process net;
```

the main steps are:

```text
Shift PROCESS
Shift ID("net")
Reduce identifier → ID
Reduce process_body → epsilon
Shift SEMI
Reduce process_dec → PROCESS identifier process_body SEMI
Reduce statement → process_dec
Reduce statements → statement
Reduce program → statements
Accept
```

It is **bottom-up** because it recognizes smaller parts first and combines
them into larger structures until it reaches `program`.

Your grammar functions explicitly record each reduction:

```python
def p_process_dec_9(p):
    "process_dec : PROCESS identifier process_body SEMI"
    record(9)
```

The quoted line defines the grammar rule. When Yacc applies that rule, it runs
the function and records production 9.

The minimal program produces:

```text
31 11 9 4 2 1
```

These numbers identify:

```text
31  identifier → id
11  process_body → epsilon
9   process_dec → process identifier process_body ;
4   statement → process_dec
2   statements → statement
1   program → statements
```

Your L6 saves this **production sequence**. It does not create a stored
syntax-tree object.

The main functions are:

| Function | Purpose |
|---|---|
| `create_lexer()` | Prepares source scanning |
| `load_pif()` | Reads saved PIF tokens |
| `p_*()` | Defines productions and records reductions |
| `analyze()` | Runs parsing and returns results |
| `format_trace()` | Formats the production sequence |
| `save_tables()` | Saves PIF and production output |

## Which stage detects which error?

| Example | What is wrong? | Where detected? |
|---|---|---|
| `process 9net;` | Invalid identifier | Lexical analysis |
| `process net` | Missing semicolon | Syntax analysis |
| `process ; net` | Invalid token order | Syntax analysis |
| `start(unknown);` | Possibly undeclared process | Requires semantic analysis |

That last example has valid tokens and valid grammatical structure. Your
current labs do not check whether `unknown` was declared.

They also do not execute service commands, resolve dependency cycles, or
generate machine code. Those require additional stages after the lexical and
syntactical analysis implemented here.
