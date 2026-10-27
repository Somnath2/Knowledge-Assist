import unittest

from review_agent.checks import scan_python_security_patterns, validate_python_syntax


class ChecksTest(unittest.TestCase):
    def test_reports_python_syntax_error(self):
        findings = validate_python_syntax({"broken.py": "def broken(:\n    pass\n"})

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "python-syntax-error")
        self.assertEqual(findings[0]["path"], "broken.py")

    def test_detects_risky_constructs_without_running_source(self):
        findings = scan_python_security_patterns(
            {"app.py": "import subprocess\nsubprocess.run(user_input, shell=True)\neval(value)\n"}
        )

        self.assertEqual({finding["rule_id"] for finding in findings}, {"shell-true", "dynamic-code-execution"})

    def test_skips_non_python_files(self):
        self.assertEqual(validate_python_syntax({"app.js": "function ("}), [])
        self.assertEqual(scan_python_security_patterns({"app.js": "eval(value)"}), [])


if __name__ == "__main__":
    unittest.main()