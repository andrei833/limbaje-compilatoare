# Lab 3: lexical analysis

From `L3/01_lexical_analysis/`, activate the environment and run:

```sh
source "$(realpath ../.venv)/bin/activate"
python lexer.py examples/program-1-output < examples/program-1.txt
python lexer.py examples/program-2-output < examples/program-2.txt
python lexer.py examples/lexical-errors-output < examples/lexical-errors.txt
```

The optional argument is the output directory (default: `output`). Each run writes:

| File | Columns |
| --- | --- |
| `st.csv` | Index (bucket, index), Value / Lexeme, Type |
| `pif.csv` | ST Index (bucket, index), Token / Category, Value |
| `errors.csv` | Source Index, Value, Message |

PIF rows follow source token order; the first column is the ST reference, not a token position. Whitespace and invalid lexemes do not receive PIF entries. Errors use a zero-based character index in the original source, including whitespace, so invalid input can be located exactly.

`IDENTIFIER` and `CONSTANT` (labels from `tokens.txt`) refer to entries in the ST. Fixed tokens use their spelling and `(-1, -1)` as their ST reference. Symbol values and types are stored in C and retrieved through CFFI. Types are Identifier and Constant. Type is shown only in the ST.

The language remains the process-management DSL from Lab 2: its constants are `true`, `false`, `RUNNING`, `STOPPED`, and `ERROR`. The number/read/write example illustrates the output format; it does not add numeric constants or statements to this DSL.

Exit status is 0 on lexical success and 1 on lexical errors. Invalid input still writes all three CSVs. An empty errors table contains only its header.

Setup on another computer, from the repository root (requires uv and a C compiler):

```sh
uv venv L3/.venv
uv pip install --python L3/.venv/bin/python -r L3/requirements.txt
```

CFFI automatically compiles `02_symbol_table/symbol_table.c` and caches the generated files in the system temporary directory. No manual compilation or Makefile is needed.

Symbols are referenced by the pair (ST Bucket, Index in Bucket), both zero-based. Collisions share a bucket but have different positions in its linked list. New entries are appended, so earlier references stay stable. The CSV exporter retrieves symbols using both coordinates.

Hashing uses the sum of the lexeme's character codes modulo 101. For example, `net` hashes to `(110 + 101 + 116) % 101 = 24`. Different strings can have the same sum; linked lists handle these collisions.
