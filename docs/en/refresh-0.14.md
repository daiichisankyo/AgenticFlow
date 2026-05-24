# SDK 0.14.6 Refresh — Discovery Report

> Phase 0 outcome of the openai-agents 0.14 refresh effort. This report grounds all subsequent design in actual SDK API surface, not speculation. Captured against `openai-agents==0.14.6` and `openai-chatkit==1.6.3` in a throwaway venv at `/tmp/af-discovery-014`.

## Verdict

**PASS.** openai-agents 0.14.6 is fully backward-compatible with AF as currently written. All 203 existing test cases pass against 0.14.6 with zero AF code changes.

## Test Results

| Item | Value |
|---|---|
| Environment | `/tmp/af-discovery-014/.venv` (Python 3.12.9) |
| `agents` version | 0.14.6 |
| `chatkit` version | 1.6.3 |
| AF | editable install of this repo at v0.38-rc1 |
| Result | **203 / 203 PASSED** in 175.98s |
| Log | `/tmp/af-discovery-014/pytest-014.log` |
| Discovery JSON | `/tmp/af-discovery-014/discovery.json` |

### Real-LLM End-to-End Verification

`tests/integration/test_sandbox_e2e.py` (2 cases) exercises the full path AF → SDK → `unix_local` sandbox → host filesystem with `gpt-5.5`. Opt-in via `AF_RUN_INTEGRATION=1`; both cases PASS in ~11s when run.

| Case | What it proves |
|---|---|
| `test_sandbox_agent_writes_file_in_workspace` | The sandboxed agent uses shell access to create a file with the requested contents; the host observes it. |
| `test_sandbox_agent_reads_pre_seeded_file_round_trip` | A host-seeded file is readable from inside the sandbox and the agent can derive a new output file from it. |

These are gated to avoid surprise API cost; the default `uv run pytest` run deselects them via the `e2e` / `integration` marker filter (`addopts` in `pyproject.toml`). See [Testing guide — Real-LLM End-to-End Tests](guides/testing.md#real-llm-end-to-end-tests-marker-gated) for the opt-in commands.

## Anchor Compatibility

Each surface in `§3 Anchor` of the refresh plan was verified against 0.14.6 actuals.

| Anchor | Status | Evidence |
|---|---|---|
| `Runner.run` AF kwargs | PASS | `context`, `max_turns`, `run_config`, `session`, `previous_response_id`, `auto_previous_response_id`, `conversation_id` all preserved. New `error_handlers` kwarg is additive. |
| `Runner.run_streamed.stream_events()` / `.final_output` | PASS | Test cases exercising both pass. |
| `Agent` constructor passthrough | PASS | All AF-passed kwargs accepted on 0.14.6 Agent. |
| `agents.memory.session.SessionABC` inheritance | PASS | Abstract methods unchanged: `add_items`, `clear_session`, `get_items`, `pop_item`. A new `session_settings` attribute exists on `SessionABC` but defaults to `None` and is NOT abstract — AF `PhaseSession` instantiates and operates correctly. |
| `agents.items.TResponseInputItem` shape | PASS | Union expanded to 28 arms (was 26); AF dict-shape checks unaffected. |
| `RunConfig` passthrough | PASS | All previously-used fields preserved; 9 new fields are additive. |
| ChatKit `run_streamed(..., context=AgentContext, ...)` | PASS | Indirectly verified via `test_semantics::TestChatKit*` cases. |

## SDK Additions Since 0.6.9

### Sandbox Agents (the headline feature)

- New module: `agents.sandbox` (44 public symbols).
- Main class: `agents.sandbox.SandboxAgent` — **subclass of `agents.Agent`** (`MRO: SandboxAgent → Agent → AgentBase → Generic → object`).
  - Adds 4 SandboxAgent-only constructor kwargs on top of `Agent`: `default_manifest`, `base_instructions`, `capabilities`, `run_as`.
  - Everything else (tools, handoffs, model, model_settings, output_type, hooks, guardrails, …) is inherited.
- Run-time configuration: `agents.sandbox.SandboxRunConfig` — standalone dataclass (not a subclass of `RunConfig`).
  - Passing mechanism: **`RunConfig(sandbox=SandboxRunConfig(...))`** — `RunConfig` gained a new `sandbox: SandboxRunConfig | None` field.
- Workspace declaration: `agents.sandbox.Manifest` (Pydantic model). Fields: `version`, `root`, `entries`, `environment`, `users`, `groups`, `extra_path_grants`, `remote_mount_command_allowlist`.
- Snapshots: `LocalSnapshot`, `RemoteSnapshot`, `LocalSnapshotSpec`, `RemoteSnapshotSpec`, `SnapshotSpec`.
- Memory: `MemoryGenerateConfig`, `MemoryLayoutConfig`, `MemoryReadConfig`.
- Built-in sandbox providers: `agents.sandbox.sandboxes.docker`, `agents.sandbox.sandboxes.unix_local`. (Modal is not bundled in this version.)
- Errors: `SandboxError`, `ExecTimeoutError`, `ExecTransportError`, `ExposedPortUnavailableError`, `WorkspaceArchiveReadError`, `WorkspaceArchiveWriteError`, `WorkspaceReadNotFoundError`, `WorkspaceWriteTypeError`.

### New Session Backends

`agents.extensions.memory` (empty in 0.6.9) now contains:

- `advanced_sqlite_session.py`
- `async_sqlite_session.py`
- `dapr_session.py`
- `encrypt_session.py`
- `mongodb_session.py`
- `redis_session.py`
- `sqlalchemy_session.py`

Each is imported from its submodule, e.g. `from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession`. All satisfy `SessionABC`, so they slot into `af.Runner(session=...)` with no AF code changes.

### Other Additive Changes

- `agents.memory` gained `OpenAIConversationsSession`, `OpenAIResponsesCompactionSession`, `OpenAIResponsesCompactionAwareSession`, `SessionInputCallback`, `SessionSettings`.
- `Runner.run` / `run_streamed` accept `RunState[TContext]` as input (in addition to `str | list[TResponseInputItem]`).
- `Runner.run` / `run_streamed` gained `error_handlers: RunErrorHandlers[TContext] | None`.
- 9 new additive `RunConfig` fields: `call_model_input_filter`, `handoff_history_mapper`, `nest_handoff_history`, `reasoning_item_id_policy`, `sandbox`, `session_input_callback`, `session_settings`, `tool_error_formatter`, `tracing`.

No removals or signature breaks against AF's anchor surface.

## Implications for AF Design

The original refresh draft had speculative shapes for `af.SandboxAgent`, `af.Workspace`, `af.SandboxMemory`. With the actual SDK surface in hand, the AF additions can be **much smaller**.

### What AF Should Add

- **`af.SandboxAgent`** — wraps `agents.sandbox.SandboxAgent`. Returns the same `ExecutionSpec[T]` as `af.Agent`. Constructor accepts the SandboxAgent-only kwargs (`default_manifest`, `capabilities`, `run_as`, `base_instructions`) on top of all `af.Agent` kwargs.

That is the only required new symbol. `pyproject.toml` upper-bound bump (`openai-agents>=0.14.0,<0.15`) and a docs page complete the AF-side delta.

### What AF Should NOT Add

- **No `af.Workspace`** — the SDK already calls it `Manifest` (Pydantic, stable). Wrapping adds no value; users `from agents.sandbox import Manifest`.
- **No `af.SandboxMemory`** — `MemoryGenerateConfig` / `MemoryLayoutConfig` / `MemoryReadConfig` are SDK dataclasses. Pass through.
- **No new modifiers** (`.checkpoint()`, `.workspace()`, etc.) — sandbox runtime config travels via `RunConfig.sandbox`, which threads through the existing `.run_config(...)` modifier.
- **No new state-management surfaces** for `previous_response_id` / `conversation_id` — already accessible via `.run_kwarg(...)` if a user needs them.

### Confirmed Experience C (Sandbox)

```python
import agentic_flow as af
from agents import RunConfig
from agents.sandbox import SandboxRunConfig, Manifest

coder = af.SandboxAgent(
    name="coder",
    instructions="Implement the spec in Python.",
    model="gpt-5.5",
    default_manifest=Manifest(
        version="1",
        root="/work",
        entries=[...],
    ),
)

async def implement_flow(spec: str) -> str:
    async with af.phase("Plan"):
        plan = await planner(spec).stream()
    async with af.phase("Implement", persist=True):
        return await coder(plan).run_config(
            RunConfig(sandbox=SandboxRunConfig(manifest=..., concurrency_limits=...))
        ).stream()
```

All existing modifiers (`.stream()`, `.silent()`, `.snapshot()`, `.isolated()`, `.max_turns()`, `.context()`, `.run_config()`, `.run_kwarg()`) work on `af.SandboxAgent` exactly as on `af.Agent`.

### Confirmed Experience B (New Session Backends)

Zero AF code changes. User code:

```python
from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession

session = SQLAlchemySession.from_url(session_id="thread-42", url="postgresql://...")
runner = af.Runner(flow=flow, session=session)
```

Deliverable is documentation only.

## Plan Adjustments

| Plan section | Before discovery | After discovery |
|---|---|---|
| §6 Experience C sketch | `af.Workspace`, `af.SandboxMemory` proposed | Use SDK `Manifest` / memory configs directly via `RunConfig.sandbox` |
| §8 File impact | "src/agentic_flow/sandbox.py — 形は Discovery 依存" | One file with one wrapper class |
| §6 Experience A | "Discovery で fail が出た場合のみ最小修正" | Confirmed: zero AF code changes |
| Phase 2 design effort | Open-ended | Reduced to a single wrapper class + tests + docs |
| §12 risk: "SandboxAgent の正確なクラス名・コンストラクタ署名は未検証" | Open | Resolved (documented above) |

## Outcome

The plan above was executed in full and integrated into `develop` as commit `8cb30a3` (`feat: port openai-agents 0.14 refresh to develop`). Concretely:

- `src/agentic_flow/sandbox.py` and the four new docs/test files landed as planned.
- `tests/test_sandbox.py` carries the 26 structural cases; the optional `tests/test_session_backends.py` was implemented with 9 cases (skipped via `importorskip` when `sqlalchemy` / `aiosqlite` are absent).
- A separate marker-gated layer was added: `tests/integration/test_sandbox_e2e.py` (2 cases, opt-in via `AF_RUN_INTEGRATION=1`) covers the real `unix_local` sandbox + LLM round-trip.
- The `docs/en/guides/sessions.md` page was not created; the same information lives in `docs/en/concepts/sandbox.md` (`## Verification`) and `docs/en/guides/testing.md` (`## Real-LLM End-to-End Tests`).
- The `feature/sdk-0.14-refresh` branch was retired after the squash merge; `develop` is the integration branch.

## Follow-up: Runner-injected `default_run_config`

The original 0.14 refresh deliberately stayed within the SDK pass-through line: "no new modifiers, sandbox runtime config travels via `RunConfig.sandbox` through the existing `.run_config()` modifier." That decision is correct in the small (no new AF abstraction over SDK types) but it left a tension with AF's own Flow/Runner separation principle (see `docs/en/concepts/flow-runner.md`): `Session` and `Handler` are injected by the Runner so that the flow body stays free of execution-environment concerns, yet `RunConfig(sandbox=SandboxRunConfig(...))` still had to appear inline in the flow body on every sandboxed call.

`Runner.default_run_config` (added after 0.14 stabilized) closes that gap:

- `af.Runner(default_run_config=RunConfig(...))` now sets a `current_run_config` contextvar for the lifetime of the flow execution, in the same way `current_session` and `current_handler` are set.
- `ExecutionSpec.build_run_kwargs()` resolves `run_config` with the priority `.run_config()` modifier > `current_run_config` contextvar > SDK default.
- No new modifier was added; the `.run_config()` chain still works exactly as before for per-call overrides.

This is purely additive: existing flows that pass `RunConfig` per call continue to behave identically. The path through the SDK is unchanged — `RunConfig` is still the SDK type, and AF still does not wrap it.

The injection now reaches the ChatKit path as well. `af.chatkit.run_with_chatkit_context` delegates flow execution to `Runner.__call__`, so `Runner(default_run_config=RunConfig(sandbox=SandboxRunConfig(...)))` works identically through ChatKit, including for `af.SandboxAgent`. The 0.14 gap is fully closed.

Net effect on the canonical sandbox example: the flow body shrinks back to pure business logic, and the sandbox transport (`SandboxRunConfig`) sits next to `Session` on the Runner where execution-environment configuration belongs.
