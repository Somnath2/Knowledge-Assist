"""Bounded, read-only access to GitHub repository source files."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

MAX_FILES = 20
MAX_FILE_BYTES = 12_000
MAX_TOTAL_BYTES = 90_000
REQUEST_TIMEOUT_SECONDS = 15
ALLOWED_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js",
    ".jsx", ".kt", ".php", ".py", ".rb", ".rs", ".scala", ".sh", ".sql",
    ".swift", ".ts", ".tsx", ".vue", ".yaml", ".yml",
}
EXCLUDED_PARTS = {".git", "node_modules", "vendor", "dist", "build", "coverage"}


class GitHubAPIError(RuntimeError):
    """Raised when a repository cannot be read safely from GitHub."""


@dataclass(frozen=True)
class RepositorySnapshot:
    owner: str
    name: str
    ref: str
    files: dict[str, str]
    skipped_files: int


def _parse_repo_url(repo_url: str) -> tuple[str, str]:
    parsed = urlsplit(repo_url)
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username:
        raise GitHubAPIError("Use an HTTPS URL on github.com.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] in {"orgs", "users", "settings"}:
        raise GitHubAPIError("Expected a repository URL like https://github.com/owner/repo.")
    owner, name = parts[0], parts[1].removesuffix(".git")
    if not owner or not name:
        raise GitHubAPIError("The repository URL must include an owner and repository name.")
    return owner, name


def _api_get(path: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "code-evaluator-agent/0.1",
    }
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com{path}", headers=headers)
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except HTTPError as error:
        raise GitHubAPIError(f"GitHub API returned HTTP {error.code} for a read request.") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise GitHubAPIError("Could not read a valid response from the GitHub API.") from error


def fetch_repository(repo_url: str, ref: str | None = None) -> RepositorySnapshot:
    """Fetch bounded allowlisted text blobs; never checks out or executes code."""
    owner, name = _parse_repo_url(repo_url)
    encoded_owner = quote(owner, safe="")
    encoded_name = quote(name, safe="")
    repository = _api_get(f"/repos/{encoded_owner}/{encoded_name}")
    selected_ref = ref or repository.get("default_branch")
    if not isinstance(selected_ref, str) or not selected_ref:
        raise GitHubAPIError("GitHub did not provide a usable default branch; pass --ref.")

    tree = _api_get(
        f"/repos/{encoded_owner}/{encoded_name}/git/trees/{quote(selected_ref, safe='')}?recursive=1"
    )
    if tree.get("truncated"):
        raise GitHubAPIError("The repository tree is truncated; review a smaller repository or ref.")

    candidates = []
    skipped = 0
    for item in tree.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        parts = path.split("/")
        suffix = os.path.splitext(path)[1].lower()
        if any(part in EXCLUDED_PARTS for part in parts) or suffix not in ALLOWED_SUFFIXES:
            continue
        if item.get("size", MAX_FILE_BYTES + 1) > MAX_FILE_BYTES:
            skipped += 1
            continue
        candidates.append(item)

    files: dict[str, str] = {}
    total_bytes = 0
    for index, item in enumerate(sorted(candidates, key=lambda entry: entry["path"])):
        if len(files) >= MAX_FILES:
            skipped += len(candidates) - index
            break
        if total_bytes >= MAX_TOTAL_BYTES:
            skipped += 1
            continue
        blob = _api_get(f"/repos/{encoded_owner}/{encoded_name}/git/blobs/{quote(item['sha'], safe='')}")
        try:
            content = base64.b64decode(blob["content"], validate=False)
            if b"\x00" in content:
                skipped += 1
                continue
            text = content.decode("utf-8")
        except (KeyError, ValueError, UnicodeDecodeError):
            skipped += 1
            continue

        remaining = MAX_TOTAL_BYTES - total_bytes
        if len(content) > remaining:
            text = content[:remaining].decode("utf-8", errors="ignore")
            skipped += 1
        files[item["path"]] = text
        total_bytes += len(text.encode("utf-8"))

    if not files:
        raise GitHubAPIError("No eligible text source files were found within the configured limits.")
    return RepositorySnapshot(owner, name, selected_ref, files, skipped)