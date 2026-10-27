"""Regex lexer for the Lab 2 process-management programs."""

import csv
import re
import sys
from pathlib import Path

from symbol_table import SymbolTable

ROOT = Path(__file__).resolve().parent.parent


CONSTANTS = re.compile(r"(?:RUNNING|STOPPED|ERROR|true|false)\Z")
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
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
    """Return (token code, (bucket index, position in bucket)), or None for an invalid lexeme."""
    if CONSTANTS.fullmatch(lexeme):
        symbol_type = 1 if lexeme in ("true", "false") else 2
        return tokens["CONSTANT"], table.insert(lexeme, symbol_type)
    if lexeme in tokens and lexeme not in ("IDENTIFIER", "CONSTANT"):
        return tokens[lexeme], (-1, -1)
    if IDENTIFIER.fullmatch(lexeme):
        return tokens["IDENTIFIER"], table.insert(lexeme, 0)
    return None


def analyze(source, tokens):
    """Scan source text, collecting the PIF, symbol table, and diagnostics."""
    scanner = build_scanner(tokens)
    pif = []
    errors = []

    with SymbolTable() as table:
        for match in scanner.finditer(source):
            lexeme = match.group()
            if match.lastgroup != "space":
                classification = classify_token(lexeme, tokens, table)
                if classification is None:
                    errors.append(
                        {
                            "source_index": match.start(),
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
        [(str((s["index"], s["bucket_position"])), s["value"], s["type"])
         for s in symbols],
    )

    token_names = {code: name for name, code in load_tokens(
        ROOT / "01_lexical_analysis/tokens.txt"
    ).items()}
    rows = []
    for entry in result["pif"]:
        symbol_id = entry["st"]
        if symbol_id != -1:
            symbol = next(
                s for s in symbols
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
    print(f"Saved st.csv, pif.csv, errors.csv in {directory}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
