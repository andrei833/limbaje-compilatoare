"""Behavior checks for the grammar, Lex-Yacc integration, and PIF adapter."""

import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from parser import PIF_HEADERS, AnalysisError, analyze, main, production_string

ROOT = Path(__file__).resolve().parent


class ParserTests(unittest.TestCase):
    def parse(self, **kwargs):
        result = analyze(**kwargs)
        self.rows = result["pif"]
        return result["productions"]

    def write_pif(self, path, rows):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(PIF_HEADERS)
            writer.writerows(rows)

    def test_exact_minimal_bottom_up_trace(self):
        trace = self.parse(source="process net;")
        self.assertEqual(
            trace,
            [
                (31, "identifier -> id (net)"),
                (11, "process_body -> epsilon"),
                (9, "process_dec -> 'process' identifier process_body ';'"),
                (4, "statement -> process_dec"),
                (2, "statements -> statement"),
                (1, "program -> statements"),
            ],
        )

    def test_original_lab5_source_and_pif_have_identical_traces(self):
        examples = ROOT.parent / "L5/01_lexical_analysis/examples"
        for name in ("program-1", "program-2"):
            with self.subTest(name=name):
                source_trace = self.parse(
                    source=(examples / f"{name}.txt").read_text()
                )
                if name == "program-1":
                    self.assertEqual(
                        source_trace,
                        self.parse(pif=examples / f"{name}-output/pif.csv"),
                    )
                else:
                    self.assertEqual(source_trace[-1], (1, "program -> statements"))

    def test_every_grammar_production_is_exercised(self):
        source = (
            (ROOT / "examples/program.txt").read_text()
            + """
if (status(net) == RUNNING) { start(net); }
if (status(net) == STOPPED) { stop(net); }
if (autostart(net) == true) { enable(net); }
"""
        )
        applied = {number for number, _ in self.parse(source=source)}
        self.assertEqual(applied, set(range(1, 32)))

    def test_integrated_scanner_roundtrip_and_symbol_reuse(self):
        trace = self.parse(source="process net; start(net);")
        rows = self.rows
        references = [row[0] for row in rows if row[1] == "IDENTIFIER"]
        self.assertEqual(references, ["(0, 0)", "(0, 0)"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pif.csv"
            self.write_pif(path, rows)
            self.assertEqual(self.parse(pif=path), trace)

    def test_lexical_errors_have_locations_and_discard_trace(self):
        for source, location in (
            ("process net;\n@", "line 2, column 1"),
            ("process 9net;", "line 1, column 9"),
            ("process _net;", "line 1, column 9"),
            ("process n\u00e9t;", "line 1, column 10"),
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(
                    AnalysisError, "Lexical error.*" + location
                ):
                    self.parse(source=source)
                self.assertEqual(production_string, [])

    def test_syntax_errors(self):
        for source in (
            "",
            "process net",
            "process net start(net);",
            "group core = [];",
            "if (status(net) == true) { start(net); }",
            "if (autostart(net) == RUNNING) { start(net); }",
            "for (node in core) {}",
            "start(net); else { stop(net); }",
            "if (status(net) = ERROR) { stop(net); }",
            "if (status(net) == ERROR) { stop(net);",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(AnalysisError, "Syntax error"):
                    self.parse(source=source)
                self.assertEqual(production_string, [])
        self.assertTrue(self.parse(source="process valid;"))

    def test_pif_syntax_error_reports_csv_location(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pif.csv"
            self.write_pif(
                path, [["(-1, -1)", "start", "start"], ["(-1, -1)", ";", ";"]]
            )
            with self.assertRaisesRegex(AnalysisError, "PIF token 2 .*CSV row 3"):
                self.parse(pif=path)

    def test_invalid_pif_rows(self):
        for row in (
            ["(-1, -1)", "UNKNOWN", "x"],
            ["(0, 0)", "IDENTIFIER", "9x"],
            ["(0, 0)", "CONSTANT", "42"],
            ["(-1, -1)", "process", "start"],
            ["(0, 0)", "IDENTIFIER", "process"],
            ["(-1, -1)", "IDENTIFIER", "x"],
            ["(0, 0)", ";", ";"],
            ["bad", "IDENTIFIER", "x"],
            ["(True, 0)", "IDENTIFIER", "x"],
        ):
            with self.subTest(row=row), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "pif.csv"
                self.write_pif(path, [row])
                with self.assertRaisesRegex(AnalysisError, "PIF error"):
                    self.parse(pif=path)

    def test_conflicting_symbol_references(self):
        for final in (
            ["(0, 0)", "IDENTIFIER", "other"],
            ["(1, 0)", "IDENTIFIER", "net"],
        ):
            with self.subTest(final=final), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "pif.csv"
                self.write_pif(path, [["(0, 0)", "IDENTIFIER", "net"], final])
                with self.assertRaisesRegex(AnalysisError, "inconsistent ST reference"):
                    self.parse(pif=path)

    def test_cli_saves_trace_and_pif_only_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "success"
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [str(ROOT / "examples/minimal.txt"), "--output", str(output)]
                )
            self.assertEqual(code, 0, stderr.getvalue())
            self.assertIn("String of productions: 31 11 9 4 2 1", stdout.getvalue())
            self.assertIn("Parsing completed successfully", stdout.getvalue())
            self.assertTrue((output / "productions.txt").is_file())
            self.assertEqual(len(self.parse(pif=output / "pif.csv")), 6)
            failed = Path(directory) / "failure"
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [str(ROOT / "examples/syntax-error.txt"), "--output", str(failed)]
                )
            self.assertEqual(code, 1)
            self.assertFalse(failed.exists())


if __name__ == "__main__":
    unittest.main()
