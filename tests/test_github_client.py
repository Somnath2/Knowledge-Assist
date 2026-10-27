import unittest

from review_agent.github_client import GitHubAPIError, _parse_repo_url


class GitHubClientTest(unittest.TestCase):
    def test_parses_repository_url(self):
        self.assertEqual(
            _parse_repo_url("https://github.com/example/project.git"),
            ("example", "project"),
        )

    def test_rejects_non_github_url(self):
        with self.assertRaises(GitHubAPIError):
            _parse_repo_url("https://example.com/owner/repo")

    def test_rejects_missing_repository(self):
        with self.assertRaises(GitHubAPIError):
            _parse_repo_url("https://github.com/owner")


if __name__ == "__main__":
    unittest.main()