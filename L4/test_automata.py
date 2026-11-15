import itertools
import re
import unittest

from automata import (
    CONSTANTS, FiniteAutomaton, classify, constant_automaton, identifier_automaton,
)


class AutomataTests(unittest.TestCase):
    def test_identifiers(self):
        fa = identifier_automaton()
        for length in range(5):
            for chars in itertools.product('aZ0_!', repeat=length):
                word = ''.join(chars)
                expected = re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', word) is not None
                self.assertEqual(fa.accepts(word), expected, word)
                self.assertEqual(fa.to_grammar().accepts(word), expected, word)
        self.assertFalse(fa.accepts('éclair'))

    def test_constants(self):
        fa = constant_automaton()
        grammar = fa.to_grammar()
        words = {'', 'TRUE', 'running', '42', 'truefalse', 'ERROR_', 'true1'}
        for literal in CONSTANTS:
            words.update(literal[:i] for i in range(len(literal) + 1))
            words.update({literal + 'x', 'x' + literal, literal.lower()})
        for word in words:
            self.assertEqual(fa.accepts(word), word in CONSTANTS, word)
            self.assertEqual(grammar.accepts(word), word in CONSTANTS, word)

    def test_conversion_with_empty_word_cycle_and_unreachable_state(self):
        fa = FiniteAutomaton({'s', 't', 'u'}, {'a', 'b'},
                             {('s', 'a'): 't', ('t', 'b'): 's'},
                             's', {'s', 'u'})
        grammar = fa.to_grammar()
        self.assertIn(('', None), grammar.P['s'])
        self.assertIn(('a', 't'), grammar.P['s'])
        for length in range(7):
            for chars in itertools.product('ab', repeat=length):
                word = ''.join(chars)
                self.assertEqual(grammar.accepts(word), fa.accepts(word), word)

    def test_precedence(self):
        for word, expected in [('true', 'CONSTANT'), ('RUNNING', 'CONSTANT'),
                               ('process', 'KEYWORD'), ('depends_on', 'KEYWORD'),
                               ('process1', 'IDENTIFIER'), ('node_2', 'IDENTIFIER'),
                               ('_node', 'INVALID'), ('12', 'INVALID')]:
            self.assertEqual(classify(word), expected)



if __name__ == '__main__':
    unittest.main()
