# Lab 5: scanner with finite automata

This lab uses the Lab 2 programs, the Lab 3 scanner and C symbol table,
and the Lab 4 identifier and constant automata. Python 3, CFFI and a C
compiler are required.

From `L5/`, set up the environment:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
cd 01_lexical_analysis
python lexer.py examples/program-1-output < examples/program-1.txt
python lexer.py examples/program-2-output < examples/program-2.txt
python lexer.py examples/lexical-errors-output < examples/lexical-errors.txt
python -m unittest discover -s . -v
```

The last scanner example deliberately returns exit status 1. Successful
scanning returns 0. All runs write `st.csv`, `pif.csv` and `errors.csv`,
using the same columns and symbol references as Lab 3. The output directory
is optional and defaults to `output`. Input is read from standard input.
CFFI compiles the included C source automatically and caches it in the
system temporary directory.

The scanner uses explicit FA transitions for identifiers and constants.
It does not use regex. Constants are `true`, `false`, `RUNNING`, `STOPPED`
and `ERROR`; identifiers start with an ASCII letter. See `documentation.txt`
for the algorithm and examples.

To display the equivalent regular grammars from `01_lexical_analysis/`:

```sh
python automata.py --grammar identifier
python automata.py --grammar constant
```
