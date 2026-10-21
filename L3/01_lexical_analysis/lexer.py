"""Regex lexer for the Lab 2 process-management programs."""

import json
import re
import sys
from pathlib import Path

from symbol_table import SymbolTable

ROOT = Path(__file__).resolve().parent.parent


CONSTANTS = re.compile(r"(?:RUNNING|STOPPED|ERROR|true|false)\Z")
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
# Consume digit/underscore-led words together so 12abc is one error.
WORD = r"[A-Za-z0-9_]+"


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


def build_scanner(tokens):
    """Match whole words and longest punctuation first, then invalid characters."""
    punctuation = sorted(
        (token for token in tokens if not IDENTIFIER.fullmatch(token)),
        key=len,
        reverse=True,
    )
    alternatives = [r"(?P<space>\s+)", rf"(?P<word>{WORD})"]
    if punctuation:
        escaped_symbols = "|".join(re.escape(token) for token in punctuation)
        alternatives.append(rf"(?P<fixed>{escaped_symbols})")
    alternatives.append(r"(?P<error>[^\s])")
    return re.compile("|".join(alternatives))


def classify_token(lexeme, tokens, table):
    """Return (token code, symbol ID), or None for an invalid lexeme."""
    if CONSTANTS.fullmatch(lexeme):
        return tokens["CONSTANT"], table.insert(lexeme)
    if lexeme in tokens and lexeme not in ("IDENTIFIER", "CONSTANT"):
        return tokens[lexeme], -1
    if IDENTIFIER.fullmatch(lexeme):
        return tokens["IDENTIFIER"], table.insert(lexeme)
    return None


def advance_position(lexeme, line, column):
    """Move the one-based cursor past a matched token or whitespace."""
    if "\n" in lexeme:
        return line + lexeme.count("\n"), len(lexeme.rsplit("\n", 1)[1]) + 1
    return line, column + len(lexeme)


def analyze(source, tokens):
    """Scan source text, collecting the PIF, symbol table, and diagnostics."""
    scanner = build_scanner(tokens)
    pif = []
    errors = []
    line, column = 1, 1

    with SymbolTable() as table:
        for match in scanner.finditer(source):
            lexeme = match.group()
            if match.lastgroup != "space":
                classification = classify_token(lexeme, tokens, table)
                if classification is None:
                    errors.append(
                        {
                            "line": line,
                            "column": column,
                            "lexeme": lexeme,
                            "message": "Invalid lexical token",
                        }
                    )
                else:
                    token_code, symbol_id = classification
                    pif.append(
                        {
                            "token": token_code,
                            "st": symbol_id,
                            "lexeme": lexeme,
                            "line": line,
                            "column": column,
                        }
                    )
            line, column = advance_position(lexeme, line, column)

        return {"pif": pif, "st": table.rows(), "errors": errors}


def main():
    """Read source text from stdin and write the analysis as JSON to stdout."""
    tokens = load_tokens(ROOT / "01_lexical_analysis/tokens.txt")
    result = analyze(sys.stdin.read(), tokens)
    json.dump(result, sys.stdout, indent=2)
    print()
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
