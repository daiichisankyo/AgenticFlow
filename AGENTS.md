# Design-Doc Loop (DDL)

This project follows [**Design-Doc Loop (DDL)**](https://github.com/SnowLightPath/DDL) — a methodology where Human and LLM share design principles across sessions via a living document.

**Core idea:** `README.md` + `docs/en/` are the design documents — shared memory that bridges session discontinuity. They are the living specification until design is reflected in code. Code is the ultimate source of truth.

**The Loop:** Draft (experience first) → Realize (design → code) → Reflect (code → design). Realize and Reflect are inverse functions. Skip any phase when work flows naturally — the only rule is to Reflect after changes.

Read the [DDL design philosophy](https://github.com/SnowLightPath/DDL/blob/main/docs/en/design_philosophy.md) to understand the intent behind this project's workflow.

## Commands

| Command | Intent |
|---------|--------|
| `/draft` | Write ideal experience before implementation |
| `/realize` | Design document → Code |
| `/reflect` | Code → Design document |
| `/commit` | Record verified changes to git |
| `/refactoring` | Improve code quality (code-only) |
| `/docs` | Keep docs (README, API reference) accurate |
| `/validate` | Run quality checks and fix failures |

## Structure

- `README.md` — Public-facing design document. Library identity, usage patterns, API surface.
- `docs/en/` — Detailed design philosophy. Concepts, guides, API reference.
- `docs/en/guides/development-workflow.md` — Project workflow, scopes, validation, and review discipline.

## Detection Targets

| ID | Category | What to Detect |
|----|----------|----------------|
| D1 | Blind Start | Acting without reading `README.md` and `docs/en/` first |
| D2 | Silent Violation | Changing code that contradicts a design principle without flagging |
| D3 | Sequential Waste | Running tasks sequentially when they could be parallelized |
| D4 | Skipped Validation | Finishing work without running ruff, mypy, or pytest |
| D5 | Leaked Specifics | Project-specific rules outside `README.md`/`docs/en/` |
| D6 | Gate Skip | Proceeding past a command's STOP gate without human approval |
| D7 | Orphan Work | Making changes not traceable to a design principle or user request |
| D8 | AI Leakage | Any AI attribution in GitHub artifacts — commits, PRs, comments, branches |

## Behavior

### On session start

1. Read `README.md`, `docs/en/concepts/`, and `docs/en/guides/development-workflow.md` — understand principles, patterns, API surface, and project workflow
2. If they are missing, inform the user and suggest `/draft`

### On any task

1. Check if the task relates to a design principle (detect D7)
2. Choose the appropriate command or work directly
3. Follow the command's Phase/Gate structure — never skip a STOP gate (detect D6)
4. Follow `docs/en/guides/development-workflow.md` for scopes, parallelization, and validation (detect D3/D4)

### On completion

1. Run the validation appropriate to the changed scope
2. If design principles were discovered or violated, suggest `/reflect`

## Constraints

- `README.md` + `docs/en/` are always read before work begins — no exceptions
- STOP gates in commands are mandatory — never auto-proceed
- Parallelize independent reads, checks, and scoped work when the active runtime supports it
- No project-specific knowledge in this file — it belongs in `README.md` or `docs/en/`
