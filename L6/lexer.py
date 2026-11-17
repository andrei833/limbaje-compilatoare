"""Lex scanner and Lab 5 PIF reader for the process-management DSL."""

import ast
import csv
import re
from pathlib import Path

import ply.lex as lex

# Requirement 3 - scanning: define the tokens that PLY Lex supplies to Yacc.
KEYWORDS = {
    word: word.upper()
    for word in (
        "process", "depends_on", "group", "start", "stop", "enable", "disable",
        "if", "else", "for", "in", "status", "autostart",
    )
}
CONSTANTS = {
    word: word.upper() for word in ("RUNNING", "STOPPED", "ERROR", "true", "false")
}
SYMBOLS = {
    "==": "EQ", "=": "ASSIGN", "(": "LPAREN", ")": "RPAREN",
    "{": "LBRACE", "}": "RBRACE", "[": "LBRACKET", "]": "RBRACKET",
    ",": "COMMA", ":": "COLON", ";": "SEMI",
}
FIXED = {**KEYWORDS, **SYMBOLS}
TOKEN_TEXT = {kind: repr(word) for word, kind in {**FIXED, **CONSTANTS}.items()}
TOKEN_TEXT["ID"] = "id"
PIF_HEADERS = ["ST Index (bucket, index)", "Token / Category", "Value"]
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")

tokens = ["ID", *KEYWORDS.values(), *CONSTANTS.values(), *SYMBOLS.values()]
t_ignore = " \t\r"


class AnalysisError(Exception):
    """Stop scanning or parsing at the first invalid input."""


def location(source, position):
    line = source.count("\n", 0, position) + 1
    column = position - source.rfind("\n", 0, position)
    return f"line {line}, column {column}"


def save_token(token):
    """Record a recognized token in the PIF before returning it to Yacc."""
    value = token.value
    if token.type == "ID" or value in CONSTANTS:
        symbols = token.lexer.symbols
        if value not in symbols:
            symbols[value] = (len(symbols), 0)
        reference = symbols[value]
        category = "IDENTIFIER" if token.type == "ID" else "CONSTANT"
    else:
        reference, category = (-1, -1), value
    token.lexer.rows.append([str(reference), category, value])
    token.location = location(token.lexer.lexdata, token.lexpos)
    return token


def t_WORD(token):
    r"[A-Za-z0-9_]+"
    token.type = CONSTANTS.get(token.value) or KEYWORDS.get(token.value) or "ID"
    if token.type == "ID" and not IDENTIFIER.fullmatch(token.value):
        # Requirement 3 - lexical errors: reject malformed words such as 9net.
        place = location(token.lexer.lexdata, token.lexpos)
        raise AnalysisError(f"Lexical error at {place}: invalid token {token.value!r}")
    return save_token(token)


def t_SYMBOL(token):
    r"==|[=(){}\[\],:;]"
    token.type = SYMBOLS[token.value]
    return save_token(token)


def t_newline(token):
    r"\n+"
    token.lexer.lineno += len(token.value)


# Requirement 3 - lexical errors: report characters outside the token alphabet.
def t_error(token):
    place = location(token.lexer.lexdata, token.lexpos)
    raise AnalysisError(f"Lexical error at {place}: illegal character {token.value[0]!r}")


# Requirement 3 - integration: prepare the Lex scanner consumed by Yacc.
def create_lexer(source):
    lexer = lex.lex()
    lexer.rows = []
    lexer.symbols = {}
    lexer.input(source)
    return lexer


# Requirement 2 - PIF input: adapt Lab 5's CSV tokens for the same Yacc parser.
def load_pif(path):
    """Load and validate the CSV format produced by Lab 5."""
    rows = []
    items = []
    symbols = {}
    references = {}
    with Path(path).open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != PIF_HEADERS:
            raise AnalysisError(f'PIF error: expected CSV columns {PIF_HEADERS!r}')
        for row_number, row in enumerate(reader, 2):
            reference, category, value = (row.get(key) for key in PIF_HEADERS)
            if None in (reference, category, value) or None in row:
                raise AnalysisError(f'PIF error at CSV row {row_number}: malformed row')
            try:
                ref = ast.literal_eval(reference)
            except (ValueError, SyntaxError):
                ref = None
            if (not isinstance(ref, tuple) or len(ref) != 2
                    or any(type(index) is not int for index in ref)):
                raise AnalysisError(f'PIF error at CSV row {row_number}: invalid ST reference')
            if category == 'IDENTIFIER':
                valid_id = IDENTIFIER.fullmatch(value) and value not in KEYWORDS and value not in CONSTANTS
                kind = "ID" if valid_id else None
            elif category == 'CONSTANT':
                kind = CONSTANTS.get(value)
            else:
                kind = FIXED.get(category) if category == value else None
            is_symbol = category in ('IDENTIFIER', 'CONSTANT')
            valid_ref = all(index >= 0 for index in ref) if is_symbol else ref == (-1, -1)
            if kind is None or not valid_ref:
                raise AnalysisError(
                    f"PIF error at CSV row {row_number}: invalid category, value, or ST reference"
                )
            if is_symbol:
                if ((ref in references and references[ref] != value)
                        or (value in symbols and symbols[value] != ref)):
                    raise AnalysisError(f'PIF error at CSV row {row_number}: inconsistent ST reference')
                references[ref] = value
                symbols[value] = ref
            token = lex.LexToken()
            token.type, token.value = kind, value
            token.lineno, token.lexpos = row_number, len(items)
            token.location = f"PIF token {len(items) + 1} (CSV row {row_number})"
            items.append(token)
            rows.append([reference, category, value])
    return PIFLexer(rows, items)


class PIFLexer:
    """Adapt a saved token list to Yacc's token() interface."""

    def __init__(self, rows, items):
        self.rows = rows
        self.items = iter(items)

    def token(self):
        return next(self.items, None)
