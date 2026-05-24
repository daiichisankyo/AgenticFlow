# Sandbox Agents

`af.SandboxAgent` runs an agent inside a containerized, persistent workspace. Files written by the agent live across calls; snapshots can be taken and resumed. AF wraps `agents.sandbox.SandboxAgent` (introduced in openai-agents 0.14) and lets you treat it just like `af.Agent`.

```python
import agentic_flow as af
from agents.sandbox import Manifest

coder = af.SandboxAgent(
    name="coder",
    instructions="Implement the spec in Python.",
    model="gpt-5.5",
    default_manifest=Manifest(version="1", root="/work", entries=[]),
)

result = await coder("Write a CLI that prints hello").stream()
```

## How it relates to `af.Agent`

`agents.sandbox.SandboxAgent` is a subclass of `agents.Agent` at the SDK level. AF mirrors that: `af.SandboxAgent` is a subclass of `af.Agent` that constructs the SDK's sandbox class instead of the plain one. Everything else carries over.

| Feature | `af.Agent` | `af.SandboxAgent` |
|:--------|:----------:|:-----------------:|
| Returns `ExecutionSpec[T]` from `agent(prompt)` | ✅ | ✅ |
| All modifiers (`.stream()`, `.silent()`, `.snapshot()`, `.isolated()`, `.max_turns()`, `.context()`, `.run_config()`, `.run_kwarg()`) | ✅ | ✅ |
| Pydantic `output_type` | ✅ | ✅ |
| Tools, handoffs, guardrails, hooks (SDK pass-through) | ✅ | ✅ |
| Persistent workspace, snapshots, sandbox memory | — | ✅ |

## Sandbox-specific constructor kwargs

These four are accepted by `agents.sandbox.SandboxAgent` in addition to all of `agents.Agent`'s kwargs. AF's pass-through forwards them unchanged:

| Kwarg | Type | Purpose |
|:------|:-----|:--------|
| `default_manifest` | `agents.sandbox.Manifest \| None` | Workspace declaration (root, entries, environment, users, groups, path grants) |
| `base_instructions` | `str \| Callable \| None` | Instructions injected by the sandbox runtime (combined with the agent's `instructions`) |
| `capabilities` | `Sequence[Capability]` | Sandbox runtime capabilities the agent declares |
| `run_as` | `User \| str \| None` | OS-level user the sandboxed processes run as |

All four come from `agents.sandbox`. AF does not wrap them — use the SDK types directly.

## Configuring the runtime

Sandbox runtime configuration (which sandbox client, which session, snapshot to materialize, concurrency limits) lives on `agents.sandbox.SandboxRunConfig`. The SDK threads it into a regular `RunConfig` via the `sandbox` field. AF treats `RunConfig` as part of the **execution environment**, the same way it treats `Session` and `Handler`: the Runner injects it via contextvars so the flow body never has to mention it.

### Recommended: inject through the Runner

```python
from agents import RunConfig, SQLiteSession
from agents.sandbox import SandboxRunConfig

async def my_flow(spec: str) -> str:
    return await coder(spec).stream()

runner = af.Runner(
    flow=my_flow,
    session=SQLiteSession("chat.db"),
    default_run_config=RunConfig(
        sandbox=SandboxRunConfig(
            manifest=...,
            concurrency_limits=...,
        )
    ),
)
```

The Runner sets `current_run_config` for the duration of the flow; `ExecutionSpec.execute()` resolves it when no explicit `.run_config()` is set on the call. The flow body stays focused on business logic.

### Per-call override: existing `.run_config()` modifier

When a single call needs a different `RunConfig` (resuming from a different snapshot, switching to another sandbox client temporarily, etc.), the existing modifier still wins:

```python
result = await coder("resume from snapshot").run_config(
    RunConfig(sandbox=SandboxRunConfig(snapshot=other_snapshot))
).stream()
```

Resolution order, most-specific first:

1. `.run_config(...)` on the `ExecutionSpec`
2. `Runner(default_run_config=...)` injected via contextvar
3. SDK default (no `run_config` kwarg passed)

No new modifier was added to AF — the sandbox configuration travels the same `RunConfig` path as any other execution-environment setting.

## What AF intentionally does *not* add

In line with the [SDK Compatibility](../reference/sdk-compatibility.md) principle of pass-through:

- No `af.Workspace` — use `agents.sandbox.Manifest`.
- No `af.SandboxMemory` — use `agents.sandbox.MemoryGenerateConfig` / `MemoryLayoutConfig` / `MemoryReadConfig`.
- No new `.checkpoint()` or `.workspace()` modifier — snapshot/resume is configured on `SandboxRunConfig`.
- No special wrapping of sandbox errors (`SandboxError`, `ExecTimeoutError`, etc.) — they raise as-is.

If the SDK adds further sandbox features in future minor releases, AF should normally pick them up without code changes, just like any other SDK pass-through.

## Choosing between `af.Agent` and `af.SandboxAgent`

Use **`af.Agent`** when:

- The agent only needs context (Session, PhaseSession) and tool calls.
- No filesystem state needs to persist across runs.

Use **`af.SandboxAgent`** when:

- The agent should write or modify files in a controlled workspace.
- You want to snapshot intermediate state and resume later.
- Long-running coding, data-processing, or build tasks benefit from a persistent root.

Inside a single flow you can mix both — the modifiers and `phase()` boundaries work the same for either.

## Verification

The structural guarantees above are covered by `tests/test_sandbox.py` (26 cases). Real `unix_local` sandbox + LLM round-trip is covered by `tests/integration/test_sandbox_e2e.py` (2 cases), opt-in via `AF_RUN_INTEGRATION=1`. Both layers pass.

## See also

- [`agents.sandbox` API reference](https://openai.github.io/openai-agents-python/) — full SDK surface (Manifest fields, sandbox providers, snapshot specs).
- [SDK Compatibility](../reference/sdk-compatibility.md) — version requirements and pass-through guarantees.
- [Modifiers](modifiers.md) — `.run_config()`, `.context()`, etc., that compose with `af.SandboxAgent`.
