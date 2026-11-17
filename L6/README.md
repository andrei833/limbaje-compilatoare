# Lab 6: syntactical analysis with Lex-Yacc

This lab parses the process-management DSL from Labs 1–5 using PLY's Lex
scanner and LALR(1) Yacc parser. Deliverables are [documentation.txt](documentation.txt)
(formal numbered CFG, input/output example, design and error reporting) and
[parser.py](parser.py) (grammar and parsing) with [lexer.py](lexer.py)
(scanner and PIF reader).

Like L5, the code uses plain functions: `analyze()` returns a dictionary with
`pif` and `productions`, and `save_tables()` writes the results. Each grammar
function contains one production and a `record(rule_number)` call. Start with
`p_process_dec_9()` to see how a process declaration is recognized. The small
`PIFLexer` class only supplies Yacc's required `token()` interface for CSV input.

From the repository root:

```sh
uv venv L6/.venv
uv pip install --python L6/.venv/bin/python -r L6/requirements.txt
L6/.venv/bin/python L6/parser.py L6/examples/minimal.txt
L6/.venv/bin/python L6/parser.py L6/examples/program.txt --output L6/output
L6/.venv/bin/python L6/parser.py --pif L5/01_lexical_analysis/examples/program-1-output/pif.csv
L6/.venv/bin/python L6/parser.py --pif L6/output/pif.csv
L6/.venv/bin/python L6/parser.py --grammar
L6/.venv/bin/python -m unittest discover -s L6 -v
```

Source input also defaults to stdin: `L6/.venv/bin/python L6/parser.py < L2/program-1.txt`.
Each successful run prints the numbered grammar, PIF table, reduction trace,
numeric production string and success message. `--output` saves `productions.txt`
and `pif.csv`. Existing files in that directory are replaced only after a
successful parse; files from an earlier run are retained if parsing fails.

Error examples (each exits with status 1):

```sh
L6/.venv/bin/python L6/parser.py L6/examples/lexical-error.txt
L6/.venv/bin/python L6/parser.py L6/examples/syntax-error.txt
```

The PIF reader consumes the Lab 3/5 CSV schema, including its lexeme values
and bucket references. The new scanner uses sequential `(index, 0)` symbol
references in the same CSV schema; it does not require the previous C symbol
table or its hash algorithm. Constants retain category `CONSTANT` in PIF and
are mapped to separate Yacc terminals to enforce state versus boolean conditions.

The CFG is supplied through the Yacc production functions in `parser.py`;
`--grammar` exports those exact rules. It is not a runtime parser for arbitrary
grammar documents. The reduction string records bottom-up rule applications;
reversing it yields the corresponding rightmost derivation order.

Library reference: [PLY documentation](https://github.com/dabeaz/ply/blob/master/doc/ply.md).
