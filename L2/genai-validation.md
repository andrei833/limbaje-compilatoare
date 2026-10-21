# GenAI BNF validation

Tool: Codex AI assistant (textual review).

## Prompt 1

**Prompt:** Review the Lab 1 BNF for undefined nonterminals, incomplete notation, and ambiguity. Recommend simple and concise but tought out corrections.

**Input:** `L1/process-lang BNF.txt`.

**Output:** `<proecess_dec>` is undefined; use `<process_dec>`. Expand the ellipses in `<letter>` into explicit alternatives. Separate `depends_on` from `:` to allow whitespace. Specify reserved keywords and whitespace handling. Braces avoid dangling-else ambiguity. Declaration and type checks belong to semantic validation.

## Prompt 2

**Prompt:** Apply the recommendations and return the complete revised BNF, preserving the original statement types and nonempty blocks and lists.

**Input:** Lab 1 BNF and the recommendations from Prompt 1.

**Output:**

```bnf
<program> ::= <statements>
<statements> ::= <statement> | <statement> <statements>
<statement> ::= <process_dec> | <group_dec> | <command> | <conditional> | <loop>

<process_dec> ::= "process" <identifier> <process_body> ";"
<process_body> ::= "{" "depends_on" ":" <identifier_list> "}" | epsilon
<group_dec> ::= "group" <identifier> "=" "[" <identifier_list> "]" ";"
<identifier_list> ::= <identifier> | <identifier> "," <identifier_list>

<command> ::= <action> "(" <identifier> ")" ";"
<action> ::= "start" | "stop" | "enable" | "disable"
<conditional> ::= "if" "(" <condition> ")" "{" <statements> "}" <else_clause>
<else_clause> ::= "else" "{" <statements> "}" | epsilon
<loop> ::= "for" "(" <identifier> "in" <identifier> ")" "{" <statements> "}"
<condition> ::= "status" "(" <identifier> ")" "==" <state>
              | "autostart" "(" <identifier> ")" "==" <boolean>
<state> ::= "RUNNING" | "STOPPED" | "ERROR"
<boolean> ::= "true" | "false"

<identifier> ::= <letter> <val_chars>
<val_chars> ::= <letter> <val_chars> | <digit> <val_chars> | "_" <val_chars> | epsilon
<letter> ::= "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h" | "i" | "j" | "k" | "l" | "m"
           | "n" | "o" | "p" | "q" | "r" | "s" | "t" | "u" | "v" | "w" | "x" | "y" | "z"
           | "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J" | "K" | "L" | "M"
           | "N" | "O" | "P" | "Q" | "R" | "S" | "T" | "U" | "V" | "W" | "X" | "Y" | "Z"
<digit> ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
```

`epsilon` denotes the empty string. The language is case-sensitive. Keywords and literals are reserved; identifiers are scanned as whole tokens. Whitespace is ignored between tokens, but adjacent word tokens must be separated. `==` is a single token.
