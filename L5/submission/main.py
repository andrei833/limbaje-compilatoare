"""Lab 5 scanner. Keep tokens.txt and symbol_table.c beside this file."""

import string

LETTERS = set(string.ascii_letters)
DIGITS = set(string.digits)
CONSTANTS = {"true", "false", "RUNNING", "STOPPED", "ERROR"}
KEYWORDS = {
    "process",
    "depends_on",
    "group",
    "start",
    "stop",
    "enable",
    "disable",
    "if",
    "else",
    "for",
    "in",
    "status",
    "autostart",
}


class FiniteAutomaton:
    def __init__(self, Q, Sigma, delta, q0, F):
        self.Q = Q  # states
        self.Sigma = Sigma  # alphabet
        self.delta = delta  # transitions
        self.q0 = q0  # initial state
        self.F = F  # accepting states

    def accepts(self, word):
        state = self.q0  # start at q0
        for symbol in word:
            state = self.delta.get((state, symbol))  # follow the transition
            if state is None:  # no transition, reject
                return False
        return state in self.F  # must end in an accepting state

    def to_grammar(self):
        N = self.Q.copy()  # states become nonterminals
        T = self.Sigma.copy()  # alphabet becomes terminals
        S = self.q0  # start symbol
        P = {}
        for q in N:
            P[q] = set()

        for (q, a), r in self.delta.items():
            P[q].add((a, r))  # q -> a r

        for q in self.F:
            P[q].add(("", None))  # q -> epsilon for accepting states

        return RegularGrammar(N, T, P, S)


class RegularGrammar:
    def __init__(self, N, T, P, S):
        self.N = N
        self.T = T
        self.P = P  # production rules
        self.S = S

    def accepts(self, word):
        active = {self.S}
        for symbol in word:
            next_states = set()
            for source in active:
                for terminal, target in self.P[source]:
                    if terminal == symbol and target is not None:
                        next_states.add(target)
            active = next_states

        for state in active:
            if ("", None) in self.P[state]:  # can finish with epsilon
                return True
        return False

    def format(self):
        lines = ["Start: " + self.S]
        for source in sorted(self.N):
            alternatives = []
            for terminal, target in sorted(self.P[source]):
                if target is None:
                    alternatives.append("epsilon")
                else:
                    alternatives.append(repr(terminal) + " " + target)
            if alternatives:
                lines.append(source + " -> " + " | ".join(alternatives))
        return "\n".join(lines)


def identifier_automaton():
    Q = {"q0", "q1"}
    Sigma = LETTERS | DIGITS | {"_"}
    q0 = "q0"
    F = {"q1"}
    delta = {}

    for a in LETTERS:
        delta["q0", a] = "q1"  # first character must be a letter
    for a in Sigma:
        delta["q1", a] = "q1"  # letters, digits and underscore loop here

    return FiniteAutomaton(Q, Sigma, delta, q0, F)


def constant_automaton():
    Q = {"q0"}
    Sigma = set("".join(CONSTANTS))
    q0 = "q0"
    F = set()
    delta = {}

    for word in sorted(CONSTANTS):
        q = q0
        for i, a in enumerate(word, 1):
            r = "q_" + word[:i]  # one state for each prefix
            Q.add(r)
            delta[q, a] = r
            q = r
        F.add(q)  # complete constant is accepted

    return FiniteAutomaton(Q, Sigma, delta, q0, F)


def classify(word):
    if constant_automaton().accepts(word):
        return "CONSTANT"
    if word in KEYWORDS:  # keywords use a set, no automaton
        return "KEYWORD"
    if identifier_automaton().accepts(word):
        return "IDENTIFIER"
    return "INVALID"



# C symbol table interface
"""Small Python interface to the C symbol table; CFFI handles compilation."""

from functools import lru_cache
from os import getuid
from pathlib import Path
from tempfile import gettempdir

from cffi import FFI

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def load_library():
    """Compile once when needed, reusing CFFI's cache on subsequent runs."""
    ffi = FFI()
    ffi.cdef("""
        typedef ... SymbolTable;
        SymbolTable *st_create(void);
        int st_insert(SymbolTable *table, const char *value, int type);
        int st_lookup(const SymbolTable *table, const char *value);
        int st_position(const SymbolTable *table, const char *value);
        int st_size(const SymbolTable *table);
        int st_type(const SymbolTable *table, int row);
        int st_bucket(const SymbolTable *table, int row);
        const char *st_value(const SymbolTable *table, int row);
        void st_destroy(SymbolTable *table);
    """)
    cache = Path(gettempdir()) / f"lab5-cffi-{getuid()}"
    cache.mkdir(parents=True, exist_ok=True)
    source = (ROOT / "symbol_table.c").read_text(encoding="utf-8")
    library = ffi.verify(source, tmpdir=str(cache), extra_compile_args=["-std=c11"])
    return ffi, library


class SymbolTable:
    def __init__(self):
        self.ffi, self.lib = load_library()
        self.ptr = self.lib.st_create()
        if self.ptr == self.ffi.NULL:
            raise MemoryError("Cannot create symbol table")

    def insert(self, value, symbol_type):
        symbol_id = self.lib.st_insert(self.ptr, value.encode("ascii"), symbol_type)
        if symbol_id < 0:
            raise MemoryError("Cannot insert symbol")
        return symbol_id, self.lib.st_position(self.ptr, value.encode("ascii"))

    def rows(self):
        return [
            {
                "index": self.lib.st_bucket(self.ptr, index),
                "bucket_position": self.lib.st_position(
                    self.ptr, self.lib.st_value(self.ptr, index)
                ),
                "type": ("Identifier", "Constant", "Constant")[
                    self.lib.st_type(self.ptr, index)
                ],
                "value": self.ffi.string(self.lib.st_value(self.ptr, index)).decode(
                    "ascii"
                ),
            }
            for index in range(self.lib.st_size(self.ptr))
        ]

    def close(self):
        if self.ptr != self.ffi.NULL:
            self.lib.st_destroy(self.ptr)
            self.ptr = self.ffi.NULL

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


# Scanner
"""Scanner with integrated finite automata for the Lab 2 programs."""

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


IDENTIFIER = identifier_automaton()
CONSTANT = constant_automaton()
WORD_CHARACTERS = LETTERS | DIGITS | {"_"}


def load_tokens(path):
    """Read the fixed token inventory, rejecting duplicate names or codes."""
    tokens = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        lexeme, code = line.split()
        if lexeme in tokens or int(code) in tokens.values():
            raise ValueError("Duplicate token or code")
        tokens[lexeme] = int(code)
    for required in ("IDENTIFIER", "CONSTANT"):
        if required not in tokens:
            raise ValueError(f"Missing token {required}")
    return tokens


def scan_tokens(source, tokens):
    """Split input into words and symbols, returning (source index, text).
    Spaces around symbols are optional: net=3; becomes net, =, 3, ;.
    This only separates candidates; classify_token later rejects 3.
    """
    symbols = []
    for token in tokens:
        if not IDENTIFIER.accepts(
            token
        ):  # what is not a identifier (covers all constants and keywords) is only a symbol
            symbols.append(token)

    # longer symbols first, so == is recognized before =.
    symbols.sort(key=len, reverse=True)

    position = 0
    while position < len(source):
        character = source[position]

        if character.isspace():
            position += 1
            continue

        start = position

        if character in WORD_CHARACTERS:
            # matches just words skips symbols
            # net=3; stops at net then goes trough the loop again and = is catched by else
            while position < len(source):
                next_character = source[position]
                if next_character in WORD_CHARACTERS:
                    position += 1
                else:
                    break
        else:
            # starts at a symbol
            matched_symbol = None
            for symbol in symbols:
                if source.startswith(symbol, position):
                    matched_symbol = symbol
                    break

            if matched_symbol is not None:
                position += len(matched_symbol)
            else:
                # Pass an unknown character to classification for error reporting.
                position += 1

        lexeme = source[start:position]
        yield start, lexeme


def classify_token(lexeme, tokens, table):
    """Return (token code, (bucket index, position in bucket)), or None for an invalid lexeme."""
    if CONSTANT.accepts(lexeme):
        symbol_type = 1 if lexeme in ("true", "false") else 2
        return tokens["CONSTANT"], table.insert(lexeme, symbol_type)
    if lexeme in tokens and lexeme not in ("IDENTIFIER", "CONSTANT"):
        return tokens[lexeme], (-1, -1)
    if IDENTIFIER.accepts(lexeme):
        return tokens["IDENTIFIER"], table.insert(lexeme, 0)
    return None


def analyze(source, tokens):
    """Scan source text, collecting the PIF, symbol table, and errors."""
    pif = []
    errors = []

    with SymbolTable() as table:
        for source_index, lexeme in scan_tokens(source, tokens):
            classification = classify_token(lexeme, tokens, table)
            if classification is None:
                errors.append(
                    {
                        "source_index": source_index,
                        "lexeme": lexeme,
                        "message": "Invalid lexical token",
                    }
                )
            else:
                token_code, symbol_id = classification
                pif.append(
                    {
                        "token": token_code,
                        "st": symbol_id[0],
                        "bucket_position": symbol_id[1],
                        "lexeme": lexeme,
                    }
                )

        return {"pif": pif, "st": table.rows(), "errors": errors}


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)


def save_tables(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    symbols = result["st"]
    write_csv(
        directory / "st.csv",
        ["Index (bucket, index)", "Value / Lexeme", "Type"],
        [
            (str((s["index"], s["bucket_position"])), s["value"], s["type"])
            for s in symbols
        ],
    )

    token_names = {
        code: name
        for name, code in load_tokens(ROOT / "tokens.txt").items()
    }
    rows = []
    for entry in result["pif"]:
        symbol_id = entry["st"]
        if symbol_id != -1:
            symbol = next(
                s
                for s in symbols
                if s["index"] == symbol_id
                and s["bucket_position"] == entry["bucket_position"]
            )
            category = token_names[entry["token"]]
            value = symbol["value"]
        else:
            category = value = entry["lexeme"]
        reference = str((symbol_id, entry["bucket_position"]))
        rows.append((reference, category, value))
    write_csv(
        directory / "pif.csv",
        ["ST Index (bucket, index)", "Token / Category", "Value"],
        rows,
    )
    write_csv(
        directory / "errors.csv",
        ["Source Index", "Value", "Message"],
        [(e["source_index"], e["lexeme"], e["message"]) for e in result["errors"]],
    )


def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output")
    tokens = load_tokens(ROOT / "tokens.txt")
    result = analyze(sys.stdin.read(), tokens)
    save_tables(result, directory)
    if result["errors"]:
        for error in result["errors"]:
            print(
                f"Lexical error at source index {error['source_index']}: "
                f"{error['lexeme']!r} - {error['message']}"
            )
    else:
        print("Scanning completed successfully. No lexical errors.")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
