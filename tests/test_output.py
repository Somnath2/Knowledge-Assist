import json
import unittest

from review_agent.output import validate_review_response


class OutputTest(unittest.TestCase):
    def test_accepts_valid_review(self):
        review = {
            "summary": "One finding.",
            "findings": [
                {
                    "title": "Unsafe call",
                    "severity": "high",
                    "path": "app.py",
                    "line": 1,
                    "evidence": "eval(value)",
                    "recommendation": "Avoid dynamic execution.",
                }
            ],
            "limitations": ["Static checks only."],
        }

        self.assertEqual(validate_review_response(json.dumps(review), {"app.py": "eval(value)"}), review)

    def test_rejects_finding_outside_snapshot(self):
        review = {
            "summary": "Finding.",
            "findings": [
                {
                    "title": "Issue",
                    "severity": "medium",
                    "path": "other.py",
                    "line": 1,
                    "evidence": "evidence",
                    "recommendation": "fix it",
                }
            ],
            "limitations": [],
        }

        with self.assertRaisesRegex(ValueError, "outside the fetched snapshot"):
            validate_review_response(json.dumps(review), {"app.py": "x = 1"})

    def test_rejects_invalid_line(self):
        review = {
            "summary": "Finding.",
            "findings": [
                {
                    "title": "Issue",
                    "severity": "medium",
                    "path": "app.py",
                    "line": 2,
                    "evidence": "evidence",
                    "recommendation": "fix it",
                }
            ],
            "limitations": [],
        }

        with self.assertRaisesRegex(ValueError, "invalid line number"):
            validate_review_response(json.dumps(review), {"app.py": "x = 1"})


if __name__ == "__main__":
    unittest.main()