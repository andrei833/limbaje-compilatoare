import unittest
from pathlib import Path

from lexer import analyze, load_tokens
from automata import identifier_automaton, constant_automaton

TOKENS = load_tokens(Path(__file__).with_name('tokens.txt'))


class ScannerTests(unittest.TestCase):
    def test_lab2_programs(self):
        for name in ('program-1.txt', 'program-2.txt'):
            source = (Path(__file__).parent / 'examples' / name).read_text()
            self.assertEqual(analyze(source, TOKENS)['errors'], [])

    def test_priority_and_word_boundaries(self):
        result = analyze('true false RUNNING STOPPED ERROR process trueValue RUNN', TOKENS)
        self.assertEqual([p['token'] for p in result['pif']], [1, 1, 1, 1, 1, 2, 0, 0])
        self.assertEqual(result['errors'], [])

    def test_errors_and_recovery(self):
        result = analyze('12abc _node @ é start(net);', TOKENS)
        self.assertEqual([(e['source_index'], e['lexeme']) for e in result['errors']],
                         [(0, '12abc'), (6, '_node'), (12, '@'), (14, 'é')])
        self.assertEqual([p['lexeme'] for p in result['pif']], ['start', '(', 'net', ')', ';'])

    def test_longest_symbol(self):
        result = analyze('net==RUNNING=net', TOKENS)
        self.assertEqual([p['lexeme'] for p in result['pif']], ['net', '==', 'RUNNING', '=', 'net'])

    def test_collision_and_repeated_reference(self):
        result = analyze('ab ba ab', TOKENS)
        self.assertEqual(len(result['st']), 2)
        refs = [(p['st'], p['bucket_position']) for p in result['pif']]
        self.assertEqual(refs[0], refs[2])
        self.assertEqual(refs[0][0], refs[1][0])
        self.assertNotEqual(refs[0][1], refs[1][1])

    def test_empty_input(self):
        self.assertEqual(analyze(' \n\t', TOKENS), {'pif': [], 'st': [], 'errors': []})

    def test_grammar_equivalence(self):
        words = ['', 'net', '_net', '12abc', 'node2', 'true', 'false', 'RUNNING', 'STOPPED', 'ERROR', 'RUNN', 'trueValue', 'é']
        for fa in (identifier_automaton(), constant_automaton()):
            grammar = fa.to_grammar()
            for word in words:
                self.assertEqual(fa.accepts(word), grammar.accepts(word), word)


if __name__ == '__main__':
    unittest.main()
