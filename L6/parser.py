"""Lab 6: Yacc grammar, production trace, and command-line program."""

import argparse
import csv
import sys
from pathlib import Path

from lexer import PIF_HEADERS, TOKEN_TEXT, AnalysisError, create_lexer, load_pif
from lexer import tokens as lexer_tokens
from ply import yacc

# Yacc looks up this module-level token list when building the parser.
tokens = lexer_tokens

# Yacc calls a p_* function whenever it reduces a grammar production.
# These functions record rule numbers instead of building a syntax tree.
production_string = []


# Requirement 2 - output: record every applied production in reduction order.
def record(number, value=None):
    text = grammar[number - 1]
    if value is not None:
        text += f" ({value})"
    production_string.append((number, text))


# Requirement 1 - grammar: the p_* docstrings define the mini-DSL's CFG.
# The same 31 numbered rules are documented in documentation.txt.
def p_program_1(p):
    "program : statements"
    record(1)


def p_statements_2(p):
    "statements : statement"
    record(2)


def p_statements_3(p):
    "statements : statement statements"
    record(3)


def p_statement_4(p):
    "statement : process_dec"
    record(4)


def p_statement_5(p):
    "statement : group_dec"
    record(5)


def p_statement_6(p):
    "statement : command"
    record(6)


def p_statement_7(p):
    "statement : conditional"
    record(7)


def p_statement_8(p):
    "statement : loop"
    record(8)


def p_process_dec_9(p):
    "process_dec : PROCESS identifier process_body SEMI"
    record(9)


def p_process_body_10(p):
    "process_body : LBRACE DEPENDS_ON COLON identifier_list RBRACE"
    record(10)


def p_process_body_11(p):
    "process_body :"
    record(11)


def p_group_dec_12(p):
    "group_dec : GROUP identifier ASSIGN LBRACKET identifier_list RBRACKET SEMI"
    record(12)


def p_identifier_list_13(p):
    "identifier_list : identifier"
    record(13)


def p_identifier_list_14(p):
    "identifier_list : identifier COMMA identifier_list"
    record(14)


def p_command_15(p):
    "command : action LPAREN identifier RPAREN SEMI"
    record(15)


def p_action_16(p):
    "action : START"
    record(16, p[1])


def p_action_17(p):
    "action : STOP"
    record(17, p[1])


def p_action_18(p):
    "action : ENABLE"
    record(18, p[1])


def p_action_19(p):
    "action : DISABLE"
    record(19, p[1])


def p_conditional_20(p):
    "conditional : IF LPAREN condition RPAREN LBRACE statements RBRACE else_clause"
    record(20)


def p_else_clause_21(p):
    "else_clause : ELSE LBRACE statements RBRACE"
    record(21)


def p_else_clause_22(p):
    "else_clause :"
    record(22)


def p_loop_23(p):
    "loop : FOR LPAREN identifier IN identifier RPAREN LBRACE statements RBRACE"
    record(23)


def p_condition_24(p):
    "condition : STATUS LPAREN identifier RPAREN EQ state"
    record(24)


def p_condition_25(p):
    "condition : AUTOSTART LPAREN identifier RPAREN EQ boolean"
    record(25)


def p_state_26(p):
    "state : RUNNING"
    record(26, p[1])


def p_state_27(p):
    "state : STOPPED"
    record(27, p[1])


def p_state_28(p):
    "state : ERROR"
    record(28, p[1])


def p_boolean_29(p):
    "boolean : TRUE"
    record(29, p[1])


def p_boolean_30(p):
    "boolean : FALSE"
    record(30, p[1])


def p_identifier_31(p):
    "identifier : ID"
    record(31, p[1])


# Requirement 2 - syntax errors: report an unexpected token or end of input.
def p_error(token):
    if token is None:
        raise AnalysisError("Syntax error at EOF: unexpected end of input")
    raise AnalysisError(
        f"Syntax error at {token.location}: unexpected {token.value!r} ({token.type})"
    )


# Requirement 2 - parsing:  parser with PLY Yacc.
parser = yacc.yacc(start="program", write_tables=False, debug=False)
grammar = []
for rule in parser.productions[1:]:
    rhs = (
        " ".join(str(TOKEN_TEXT.get(symbol, symbol)) for symbol in rule.prod)
        or "epsilon"
    )
    grammar.append(f"{rule.name} -> {rhs}")


def analyze(source=None, pif=None):
    """Return the PIF and production string, like L5's analyze() function."""
    production_string.clear()
    if (source is None) == (pif is None):
        raise ValueError("Provide exactly one of source or pif")
    # Requirement 2 - input: accept a saved PIF using the grammar defined above.
    # Requirement 3 - integration: source input uses the PLY Lex scanner instead.
    lexer = load_pif(pif) if pif is not None else create_lexer(source)
    try:
        # Yacc obtains each next token directly through lexer.token().
        parser.parse(lexer=lexer)
    except AnalysisError:
        production_string.clear()
        raise
    return {"pif": lexer.rows, "productions": list(production_string)}


def grammar_lines():
    for number, rule in enumerate(grammar, 1):
        yield f"Rule {number}: {rule.replace(' -> ', ' ::= ', 1)}"


# Requirement 2 - output: show the readable trace and numeric production string.
def format_trace(productions):
    lines = []
    for step, (number, text) in enumerate(productions, 1):
        lines.append(f"{step}. [Rule {number}] {text}")
    numbers = " ".join(str(number) for number, _ in productions)
    lines.append("String of productions: " + numbers)
    return "\n".join(lines)


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


def save_tables(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    write_csv(directory / "pif.csv", PIF_HEADERS, result["pif"])
    trace = format_trace(result["productions"])
    (directory / "productions.txt").write_text(trace + "\n", encoding="utf-8")


def print_pif(rows):
    widths = [max(len(str(row[i])) for row in [PIF_HEADERS, *rows]) for i in range(3)]
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    print(border)
    for row in [PIF_HEADERS, *rows]:
        cells = [str(value).ljust(width) for value, width in zip(row, widths)]
        print("| " + " | ".join(cells) + " |")
        if row is PIF_HEADERS:
            print(border)
    print(border)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    inputs = cli.add_mutually_exclusive_group()
    inputs.add_argument(
        "source", nargs="?", type=Path, help="Source file (default: stdin)"
    )
    inputs.add_argument("--pif", type=Path, help="Lab 3/5 PIF CSV with lexeme values")
    cli.add_argument(
        "--grammar", action="store_true", help="Print numbered grammar and exit"
    )
    cli.add_argument(
        "--output", type=Path, help="Save productions.txt and pif.csv on success"
    )
    args = cli.parse_args(argv)
    if args.grammar:
        print("\n".join(grammar_lines()))
        return 0
    try:
        if args.pif:
            source = None
            result = analyze(pif=args.pif)
        else:
            source = (
                args.source.read_text(encoding="utf-8")
                if args.source
                else sys.stdin.read()
            )
            result = analyze(source=source)
        print("1. INPUT PART A: GRAMMAR RULES (CFG)")
        print("\n".join(grammar_lines()))
        print("\n2. INPUT PART B: PROGRAM INTERNAL FORM (PIF)")
        if source is not None:
            print("Source Code:\n" + source.rstrip() + "\n")
        print_pif(result["pif"])
        print("\n3. OUTPUT: STRING OF PRODUCTIONS (BOTTOM-UP REDUCTION TRACE)")
        print(format_trace(result["productions"]))
        if args.output:
            save_tables(result, args.output)
        print(
            "\nParsing completed successfully with 0 lexical errors and 0 syntax errors!"
        )
        return 0
    except (AnalysisError, OSError, UnicodeError, csv.Error) as error:
        print(str(error), file=sys.stderr)
        print(
            "Parsing failed. No complete production string was produced.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
