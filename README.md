# Code Evaluator Agent

A read-only GitHub code review starter built with the Google Agent Development Kit (ADK). It fetches bounded source text through GitHub's API, runs deterministic local checks, asks correctness and security specialists to review in parallel, and synthesizes one JSON response.

## Architecture

1. `github_client` reads an allowlisted set of repository blobs from GitHub. It does not clone or execute repository code.
2. `checks` parses Python syntax and flags a small set of security-sensitive Python patterns.
3. ADK's `ParallelAgent` runs the correctness and security reviewers; a `SequentialAgent` then invokes the synthesizer.
4. The CLI prints the result as JSON. It never writes to GitHub or changes source files.

Agent definitions are kept separate from orchestration:

```text
review_agent/
	agent.py                    # Stable ADK entrypoint exporting root_agent
	workflow.py                 # Parallel specialists, then sequential synthesis
	agents/
		code_validator/agent.py   # Correctness and maintainability review
		security_checker/agent.py # Security review
		synthesizer/agent.py      # Merges and prioritizes findings
```

The deterministic checks are intentionally limited. The agent can miss issues or raise false positives; validate findings with tests, a dedicated static analyzer, and human review.

## Run locally

Requires Python 3.10+ and a Google AI API key. `GH_TOKEN` is optional for public repositories; use a read-only token for private repositories or higher API limits.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export GOOGLE_API_KEY="your-key"
export GH_TOKEN="your-read-only-github-token"  # optional for public repositories
python -m review_agent.cli https://github.com/owner/repository --ref main
```

Set `GEMINI_MODEL` to override the default `gemini-2.5-flash` model. Output is JSON on stdout; errors go to stderr with a non-zero exit status.

## Data and safety

- Selected repository source and local check results are sent to the configured Google model. Only review repositories approved for that data processing; use an approved Vertex AI project and its data controls where required.
- The GitHub client uses a source-extension allowlist and caps file count and bytes. Add organization-specific exclusions, secret redaction, audit logging, rate limits, and explicit repository authorization before deployment.
- Repository content is untrusted input. The agents are instructed to treat it as data, and they have no tools that execute code or change a repository.
- Nothing is posted to GitHub or automatically fixed. Findings require human validation.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Production implementation path

1. Expand tests for GitHub API errors, repository limits, and each static rule.
2. Add a GitHub App webhook adapter. Verify `X-Hub-Signature-256`, accept only approved pull-request events, and fetch exact base/head commits. Use short-lived installation tokens with minimum permissions; grant `pull_requests:write` only when posting reviews.
3. Run reviews in a queue-backed worker with per-installation concurrency and rate limits, deadlines, retries, idempotency, and bounded model input/output.
4. Add durable audit records, metrics, tracing, retention controls, and repository/data-residency policy. Store secrets in a managed secret store.
5. Before posting a review, validate the model response against a schema and policy-check its findings. Keep code changes out of scope and require human approval.

This repository implements the local review core, not the webhook, queue, deployment, or GitHub comment integration.