# Development Workflow

AF follows Design-Doc Loop (DDL): `README.md` and `docs/en/` are the design documents, and code is the final source of truth.

## Scope Matrix

Use the narrowest scope that covers the change.

| Scope | Path Pattern | Validation |
|-------|--------------|------------|
| library | `src/agentic_flow/**/*.py` | `uv run ruff check src/`, `uv run ruff format --check src/`, `uv run mypy src/` |
| tests | `tests/**/*.py` | `uv run ruff check tests/`, `uv run ruff format --check tests/`, `uv run pytest` |
| docs | `README.md`, `docs/en/**/*.md`, `mkdocs.yml` | `uv run mkdocs build --strict` |

The default `uv run pytest` is deterministic, offline, and cost-free
(`addopts` in `pyproject.toml` deselects `e2e` and `integration` markers).
Real-LLM tests are opt-in — see [Testing](testing.md) for opt-in commands.

When a change spans scopes, run every affected scope's validation. For broad or release-facing changes, run the full set:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
uv run mkdocs build --strict
```

## Parallel Work

Parallelization is a workflow preference, not an assumed runtime requirement. Use it when the work can be separated by ownership boundary and the active tool supports it.

Good candidates:

- Independent reads of `README.md`, `docs/en/`, `src/`, and `tests/`
- Library and tests changes owned by separate workers
- Independent validation commands after implementation

Do not claim that Codex has Claude Code Agent Teams. In Codex sessions, use the available Codex mechanisms only: parallel shell reads/checks, scoped local edits, or explicit sub-agent delegation when the user has requested agent delegation and ownership boundaries are disjoint.

## Ownership Rules

For parallel implementation, assign exclusive file ownership before editing.

| Owner | May Modify | Must Not Modify |
|-------|------------|-----------------|
| library | `src/agentic_flow/**/*.py` | `tests/**/*.py` unless explicitly reassigned |
| tests | `tests/**/*.py` | `src/agentic_flow/**/*.py` unless explicitly reassigned |
| docs | `README.md`, `docs/en/**/*.md`, `mkdocs.yml` | library and tests files unless explicitly reassigned |

Cross-scope changes require coordination by the lead session. Two workers must never edit the same file concurrently.

## Review Discipline

Review findings lead with behavioral risk, design contradiction, missing validation, or maintainability defects. Each finding should point to the smallest relevant file and line range.

When reviewing newly added comments or instructions, check for:

- Runtime claims that the active tool cannot execute
- Rules that contradict DDL's source-of-truth boundary
- Mandatory language that blocks narrow or docs-only changes
- AI attribution in commits, pull requests, comments, branches, or generated code

## Completion

Finish with the validation evidence for the changed scopes. If validation is skipped, record the operational reason.
