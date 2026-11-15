"""Scanner with integrated finite automata for the Lab 2 programs."""

import csv
import sys
from pathlib import Path

from automata import DIGITS, LETTERS, constant_automaton, identifier_automaton
from symbol_table import SymbolTable

ROOT = Path(__file__).resolve().parent.parent


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
        for name, code in load_tokens(ROOT / "01_lexical_analysis/tokens.txt").items()
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
    tokens = load_tokens(ROOT / "01_lexical_analysis/tokens.txt")
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
