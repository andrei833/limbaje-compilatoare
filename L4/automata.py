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


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--grammar",
        choices=["identifier", "constant"],
        help="Print the generated right-linear grammar",
    )
    parser.add_argument("words", nargs="*", help="Whole lexemes to classify")
    args = parser.parse_args()
    if args.grammar:
        if args.grammar == "identifier":
            automaton = identifier_automaton()
        else:
            automaton = constant_automaton()
        print(automaton.to_grammar().format())
    for word in args.words:
        print(f"{word!r}: {classify(word)}")
    if not args.grammar and not args.words:
        parser.print_help()


if __name__ == "__main__":
    main()
