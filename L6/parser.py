"""Lab 6: integrated PLY Lex-Yacc parser for the process-management DSL."""

import argparse
import ast
import csv
import re
import sys
from pathlib import Path

import ply.lex as lex
import ply.yacc as yacc


KEYWORDS = {
    word: word.upper()
    for word in (
        'process', 'depends_on', 'group', 'start', 'stop', 'enable', 'disable',
        'if', 'else', 'for', 'in', 'status', 'autostart',
    )
}
CONSTANTS = {word: word.upper() for word in ('RUNNING', 'STOPPED', 'ERROR', 'true', 'false')}
SYMBOLS = {
    '==': 'EQ', '=': 'ASSIGN', '(': 'LPAREN', ')': 'RPAREN',
    '{': 'LBRACE', '}': 'RBRACE', '[': 'LBRACKET', ']': 'RBRACKET',
    ',': 'COMMA', ':': 'COLON', ';': 'SEMI',
}
FIXED = {**KEYWORDS, **SYMBOLS}
TOKEN_TEXT = {kind: repr(word) for word, kind in {**FIXED, **CONSTANTS}.items()}
TOKEN_TEXT['ID'] = 'id'
PIF_HEADERS = ['ST Index (bucket, index)', 'Token / Category', 'Value']
IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_]*\Z')


class AnalysisError(Exception):
    """A lexical, syntax, or PIF input error; abort without a success trace."""


class Scanner:
    tokens = ['ID', *KEYWORDS.values(), *CONSTANTS.values(), *SYMBOLS.values()]

    t_EQ = r'=='
    t_ASSIGN = r'='
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_LBRACE = r'\{'
    t_RBRACE = r'\}'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_COMMA = r','
    t_COLON = r':'
    t_SEMI = r';'
    t_ignore = ' \t\r'

    def __init__(self):
        self.lexer = lex.lex(module=self)
        self.rows = []
        self.symbols = {}
        self.source = ''

    def t_WORD(self, token):
        r'[A-Za-z0-9_]+'
        value = token.value
        token.type = CONSTANTS.get(value) or KEYWORDS.get(value) or 'ID'
        if token.type == 'ID' and not IDENTIFIER.fullmatch(value):
            raise AnalysisError(
                f'Lexical error at {self.location(token.lexpos)}: invalid token {value!r}'
            )
        return token

    def t_newline(self, token):
        r'\n+'
        token.lexer.lineno += len(token.value)

    def t_error(self, token):
        raise AnalysisError(
            f'Lexical error at {self.location(token.lexpos)}: illegal character {token.value[0]!r}'
        )

    def input(self, source):
        self.source = source
        self.rows = []
        self.symbols = {}
        self.lexer.lineno = 1
        self.lexer.input(source)

    def token(self):
        token = self.lexer.token()
        if token is None:
            return None
        value = token.value
        if token.type == 'ID' or value in CONSTANTS:
            reference = self.symbols.setdefault(value, (len(self.symbols), 0))
            category = 'IDENTIFIER' if token.type == 'ID' else 'CONSTANT'
        else:
            reference, category = (-1, -1), value
        self.rows.append([str(reference), category, value])
        return token

    def location(self, position):
        line = self.source.count('\n', 0, position) + 1
        column = position - self.source.rfind('\n', 0, position)
        return f'line {line}, column {column}'


class PIFLexer:
    """Supply Lab 3/5 CSV tokens directly to Yacc, without rescanning source."""

    def __init__(self, path):
        self.rows = []
        self.items = []
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
                    kind = 'ID' if IDENTIFIER.fullmatch(value) and value not in KEYWORDS and value not in CONSTANTS else None
                elif category == 'CONSTANT':
                    kind = CONSTANTS.get(value)
                else:
                    kind = FIXED.get(category) if category == value else None
                is_symbol = category in ('IDENTIFIER', 'CONSTANT')
                valid_ref = all(index >= 0 for index in ref) if is_symbol else ref == (-1, -1)
                if kind is None or not valid_ref:
                    raise AnalysisError(f'PIF error at CSV row {row_number}: invalid category, value, or ST reference')
                if is_symbol:
                    if (ref in references and references[ref] != value) or (value in symbols and symbols[value] != ref):
                        raise AnalysisError(f'PIF error at CSV row {row_number}: inconsistent ST reference')
                    references[ref] = value
                    symbols[value] = ref
                token = lex.LexToken()
                token.type, token.value = kind, value
                token.lineno, token.lexpos = row_number, len(self.items)
                self.items.append(token)
                self.rows.append([reference, category, value])
        self.position = 0

    def token(self):
        if self.position == len(self.items):
            return None
        token = self.items[self.position]
        self.position += 1
        return token

    def location(self, position):
        return f'PIF token {position + 1} (CSV row {self.items[position].lineno})'


class Parser:
    tokens = Scanner.tokens
    start = 'program'

    def __init__(self):
        self.productions = []
        self.lexer = None
        self.parser = yacc.yacc(module=self, write_tables=False, debug=False)
        self.rule_ids = {
            (rule.name, tuple(rule.prod)): rule.number
            for rule in self.parser.productions[1:]
        }

    def reduce(self, p):
        rhs = tuple(symbol.type for symbol in p.slice[1:])
        number = self.rule_ids[(p.slice[0].type, rhs)]
        text = f'{p.slice[0].type} -> ' + (' '.join(TOKEN_TEXT.get(s, s) for s in rhs) or 'epsilon')
        if len(rhs) == 1 and rhs[0] in TOKEN_TEXT:
            text += f' ({p[1]})'
        self.productions.append((number, text))

    def p_program(self, p):
        'program : statements'
        self.reduce(p)

    def p_statements(self, p):
        '''statements : statement
                      | statement statements'''
        self.reduce(p)

    def p_statement(self, p):
        '''statement : process_dec
                     | group_dec
                     | command
                     | conditional
                     | loop'''
        self.reduce(p)

    def p_process_dec(self, p):
        'process_dec : PROCESS identifier process_body SEMI'
        self.reduce(p)

    def p_process_body(self, p):
        '''process_body : LBRACE DEPENDS_ON COLON identifier_list RBRACE
                        |'''
        self.reduce(p)

    def p_group_dec(self, p):
        'group_dec : GROUP identifier ASSIGN LBRACKET identifier_list RBRACKET SEMI'
        self.reduce(p)

    def p_identifier_list(self, p):
        '''identifier_list : identifier
                           | identifier COMMA identifier_list'''
        self.reduce(p)

    def p_command(self, p):
        'command : action LPAREN identifier RPAREN SEMI'
        self.reduce(p)

    def p_action(self, p):
        '''action : START
                  | STOP
                  | ENABLE
                  | DISABLE'''
        self.reduce(p)

    def p_conditional(self, p):
        'conditional : IF LPAREN condition RPAREN LBRACE statements RBRACE else_clause'
        self.reduce(p)

    def p_else_clause(self, p):
        '''else_clause : ELSE LBRACE statements RBRACE
                       |'''
        self.reduce(p)

    def p_loop(self, p):
        'loop : FOR LPAREN identifier IN identifier RPAREN LBRACE statements RBRACE'
        self.reduce(p)

    def p_condition(self, p):
        '''condition : STATUS LPAREN identifier RPAREN EQ state
                     | AUTOSTART LPAREN identifier RPAREN EQ boolean'''
        self.reduce(p)

    def p_state(self, p):
        '''state : RUNNING
                 | STOPPED
                 | ERROR'''
        self.reduce(p)

    def p_boolean(self, p):
        '''boolean : TRUE
                   | FALSE'''
        self.reduce(p)

    def p_identifier(self, p):
        'identifier : ID'
        self.reduce(p)

    def p_error(self, token):
        if token is None:
            raise AnalysisError('Syntax error at EOF: unexpected end of input')
        raise AnalysisError(
            f'Syntax error at {self.lexer.location(token.lexpos)}: unexpected {token.value!r} ({token.type})'
        )

    def parse(self, source=None, pif=None):
        if (source is None) == (pif is None):
            raise ValueError('Provide exactly one of source or pif')
        self.productions = []
        self.lexer = PIFLexer(pif) if pif is not None else Scanner()
        try:
            self.parser.parse(source, lexer=self.lexer)
        except AnalysisError:
            self.productions = []
            raise
        return list(self.productions)

    def grammar_lines(self):
        for rule in self.parser.productions[1:]:
            rhs = ' '.join(TOKEN_TEXT.get(s, s) for s in rule.prod) or 'epsilon'
            yield f'Rule {rule.number}: {rule.name} ::= {rhs}'

    def trace(self):
        lines = [f'{index}. [Rule {number}] {text}' for index, (number, text) in enumerate(self.productions, 1)]
        lines.append('String of productions: ' + ' '.join(str(number) for number, _ in self.productions))
        return '\n'.join(lines)


def print_pif(rows):
    widths = [max(len(str(row[i])) for row in [PIF_HEADERS, *rows]) for i in range(3)]
    border = '+' + '+'.join('-' * (width + 2) for width in widths) + '+'
    print(border)
    for row in [PIF_HEADERS, *rows]:
        print('| ' + ' | '.join(str(value).ljust(width) for value, width in zip(row, widths)) + ' |')
        if row is PIF_HEADERS:
            print(border)
    print(border)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    inputs = cli.add_mutually_exclusive_group()
    inputs.add_argument('source', nargs='?', type=Path, help='Source file (default: stdin)')
    inputs.add_argument('--pif', type=Path, help='Lab 3/5 PIF CSV with lexeme values')
    cli.add_argument('--grammar', action='store_true', help='Print numbered grammar and exit')
    cli.add_argument('--output', type=Path, help='Save productions.txt and pif.csv on success')
    args = cli.parse_args(argv)
    parser = Parser()
    if args.grammar:
        print('\n'.join(parser.grammar_lines()))
        return 0
    try:
        if args.pif:
            source = None
            parser.parse(pif=args.pif)
        else:
            source = args.source.read_text(encoding='utf-8') if args.source else sys.stdin.read()
            parser.parse(source=source)
        print('1. INPUT PART A: GRAMMAR RULES (CFG)')
        print('\n'.join(parser.grammar_lines()))
        print('\n2. INPUT PART B: PROGRAM INTERNAL FORM (PIF)')
        if source is not None:
            print('Source Code:\n' + source.rstrip() + '\n')
        print_pif(parser.lexer.rows)
        print('\n3. OUTPUT: STRING OF PRODUCTIONS (BOTTOM-UP REDUCTION TRACE)')
        print(parser.trace())
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / 'productions.txt').write_text(parser.trace() + '\n', encoding='utf-8')
            with (args.output / 'pif.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream)
                writer.writerow(PIF_HEADERS)
                writer.writerows(parser.lexer.rows)
        print('\nParsing completed successfully with 0 lexical errors and 0 syntax errors!')
        return 0
    except (AnalysisError, OSError, UnicodeError, csv.Error) as error:
        print(str(error), file=sys.stderr)
        print('Parsing failed. No complete production string was produced.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
