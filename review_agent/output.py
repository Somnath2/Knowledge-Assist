"""Validation and normalization for model-produced review JSON."""

from __future__ import annotations

import json

SEVERITIES = {"critical", "high", "medium", "low"}
FINDING_FIELDS = {"title", "severity", "path", "line", "evidence", "recommendation"}
MAX_FINDINGS = 30
MAX_RESPONSE_BYTES = 30_000


def validate_review_response(response: str, files: dict[str, str]) -> dict:
    if len(response.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ValueError("The review response exceeded the configured output limit.")
    try:
        result = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError("The model returned invalid JSON; no review was emitted.") from error

    if not isinstance(result, dict) or not isinstance(result.get("summary"), str):
        raise ValueError("The review response is missing a string summary.")
    findings = result.get("findings")
    limitations = result.get("limitations")
    if not isinstance(findings, list) or not isinstance(limitations, list):
        raise ValueError("The review response is missing findings or limitations lists.")
    if len(findings) > MAX_FINDINGS:
        raise ValueError("The review response exceeded the configured finding limit.")
    if not all(isinstance(item, str) for item in limitations):
        raise ValueError("Every review limitation must be a string.")

    line_counts = {path: source.count("\n") + 1 for path, source in files.items()}
    for finding in findings:
        if not isinstance(finding, dict) or not FINDING_FIELDS.issubset(finding):
            raise ValueError("A finding is missing required fields.")
        if finding["severity"] not in SEVERITIES:
            raise ValueError("A finding has an invalid severity.")
        if not all(isinstance(finding[field], str) and finding[field] for field in FINDING_FIELDS - {"line"}):
            raise ValueError("Finding text fields must be non-empty strings.")
        path, line = finding["path"], finding["line"]
        if path not in line_counts:
            raise ValueError(f"A finding refers to a file outside the fetched snapshot: {path}.")
        if isinstance(line, bool) or not isinstance(line, int) or not 1 <= line <= line_counts[path]:
            raise ValueError(f"A finding has an invalid line number for {path}.")

    return {
        "summary": result["summary"],
        "findings": findings,
        "limitations": limitations,
    }