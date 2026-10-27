"""Deterministic, non-executing checks used as evidence for agent review."""

from __future__ import annotations

import ast


def validate_python_syntax(files: dict[str, str]) -> list[dict[str, str | int]]:
    findings: list[dict[str, str | int]] = []
    for path, source in files.items():
        if not path.endswith(".py"):
            continue
        try:
            ast.parse(source, filename=path)
        except SyntaxError as error:
            findings.append(
                {
                    "rule_id": "python-syntax-error",
                    "severity": "high",
                    "path": path,
                    "line": error.lineno or 1,
                    "message": error.msg,
                }
            )
    return findings


def scan_python_security_patterns(files: dict[str, str]) -> list[dict[str, str | int]]:
    """Flag a few risky Python constructs; results require manual validation."""
    findings: list[dict[str, str | int]] = []
    for path, source in files.items():
        if not path.endswith(".py"):
            continue
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func)
            rule_id = message = ""
            if name in {"eval", "exec"}:
                rule_id, message = "dynamic-code-execution", f"{name} executes dynamically supplied code."
            elif name in {"pickle.load", "pickle.loads"}:
                rule_id, message = "unsafe-deserialization", "Pickle can execute code when loading untrusted data."
            elif name in {"hashlib.md5", "hashlib.sha1"}:
                rule_id, message = "weak-hash", f"{name} is not suitable for security-sensitive hashing."
            elif name.startswith("subprocess.") and any(
                keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                for keyword in node.keywords
            ):
                rule_id, message = "shell-true", "subprocess is called with shell=True; review input handling."
            elif name in {"requests.get", "requests.post", "requests.put", "requests.delete"} and any(
                keyword.arg == "verify" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False
                for keyword in node.keywords
            ):
                rule_id, message = "tls-verification-disabled", "TLS certificate verification is disabled."

            if rule_id:
                findings.append(
                    {
                        "rule_id": rule_id,
                        "severity": "medium",
                        "path": path,
                        "line": node.lineno,
                        "message": message,
                    }
                )
    return findings


def _call_name(node: ast.expr) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))