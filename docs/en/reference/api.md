# API Reference

Complete API documentation for AF.

## Agent

```python
import agentic_flow as af
```

### Agent[T]

Wrapper around SDK Agent that enables callable form.

```python
class af.Agent(Generic[T]):
    def __init__(
        self,
        *,
        output_type: type[T] | None = None,
        **sdk_kwargs: Any,
    ) -> None: ...

    def __call__(self, input: str) -> af.ExecutionSpec[T]: ...
```

**Parameters:**

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `output_type` | `type[T] \| None` | Pydantic model for typed output. If `None`, `T = str`. |
| `**sdk_kwargs` | `Any` | All arguments passed to `agents.Agent` |

**Common sdk_kwargs:**

| Argument | Type | Description |
|:---------|:-----|:------------|
| `name` | `str` | Agent name (required) |
| `instructions` | `str` | System instructions |
| `model` | `str` | Model name (e.g., `"gpt-5.5"`) |
| `model_settings` | `ModelSettings` | Model configuration |
| `tools` | `list` | Tool functions |
| `handoffs` | `list` | Handoff agents |

**Example:**

```python
import agentic_flow as af
from pydantic import BaseModel

class Analysis(BaseModel):
    sentiment: str
    score: float

# str output
assistant = af.Agent(name="assistant", instructions="...", model="gpt-5.5")

# Typed output
analyzer = af.Agent(name="analyzer", instructions="...", output_type=Analysis, model="gpt-5.5")
```

---

## SandboxAgent

```python
import agentic_flow as af
```

### SandboxAgent[T]

Subclass of `Agent[T]` that wraps `agents.sandbox.SandboxAgent` (introduced in `openai-agents` 0.14). Returns the same `ExecutionSpec[T]` and supports the same modifier set as `Agent`. Use when an agent needs a persistent containerized workspace, snapshots, or sandbox memory.

```python
class af.SandboxAgent(af.Agent[T]):
    def __init__(
        self,
        *,
        output_type: type[T] | None = None,
        **sdk_kwargs: Any,
    ) -> None: ...
```

**Parameters:** Same as `Agent`. The constructor forwards `**sdk_kwargs` verbatim to `agents.sandbox.SandboxAgent`, which accepts every kwarg `agents.Agent` accepts plus four sandbox-specific ones.

**Sandbox-specific sdk_kwargs:**

| Argument | Type | Description |
|:---------|:-----|:------------|
| `default_manifest` | `agents.sandbox.Manifest \| None` | Workspace declaration (root, entries, environment, users, groups, path grants). |
| `base_instructions` | `str \| Callable \| None` | Instructions injected by the sandbox runtime, combined with `instructions`. |
| `capabilities` | `Sequence[Capability]` | Sandbox runtime capabilities the agent declares. |
| `run_as` | `User \| str \| None` | OS-level user the sandboxed processes run as. |

Sandbox runtime configuration (which sandbox client, snapshot to materialize, concurrency limits) lives in `RunConfig(sandbox=SandboxRunConfig(...))`. AF treats `RunConfig` as part of the **execution environment**, the same way it treats `Session` and `Handler`: the recommended path is to inject it on the `Runner` via `default_run_config`, and the per-call `.run_config()` modifier remains available as an override. No new modifier is added.

**Example (recommended — Runner injection):**

```python
import agentic_flow as af
from agents import RunConfig, SQLiteSession
from agents.sandbox import Manifest, SandboxRunConfig

coder = af.SandboxAgent(
    name="coder",
    instructions="Implement the spec in Python.",
    model="gpt-5.5",
    default_manifest=Manifest(version=1, root="/work", entries={}),
)

async def my_flow(spec: str) -> str:
    return await coder(spec).stream()

runner = af.Runner(
    flow=my_flow,
    session=SQLiteSession("chat.db"),
    default_run_config=RunConfig(sandbox=SandboxRunConfig()),
)
```

**Example (per-call override):**

```python
result = await coder("resume from snapshot").run_config(
    RunConfig(sandbox=SandboxRunConfig(snapshot=other_snapshot))
).stream()
```

Resolution order, most-specific first: `.run_config()` on the spec → `Runner(default_run_config=...)` via contextvar → SDK default.

See [Sandbox Agents](../concepts/sandbox.md) for the design rationale and the AF-vs-SDK boundary.

---

## ExecutionSpec

```python
import agentic_flow as af
```

### ExecutionSpec[T]

Awaitable execution specification. Created by `agent(prompt)`.

```python
@dataclass
class ExecutionSpec(Generic[T]):
    sdk_agent: SDKAgent
    input: str = ""
    is_streaming: bool = False
    is_isolated: bool = False
    is_snapshot: bool = False
    is_silent: bool = False
    max_turns_limit: int | None = None
    run_kwargs: dict[str, Any] = field(default_factory=dict)

    # WHERE axis
    def isolated(self) -> ExecutionSpec[T]: ...
    def snapshot(self) -> ExecutionSpec[T]: ...

    # HOW axis
    def stream(self) -> ExecutionSpec[T]: ...
    def silent(self) -> ExecutionSpec[T]: ...

    # LIMITS axis
    def max_turns(self, max_turns: int) -> ExecutionSpec[T]: ...

    # SDK pass-through
    def run_config(self, run_config: RunConfig) -> ExecutionSpec[T]: ...
    def context(self, context: Any) -> ExecutionSpec[T]: ...
    def run_kwarg(self, **kwargs: Any) -> ExecutionSpec[T]: ...

    def __await__(self): ...
```

**Methods:**

| Method | Returns | Axis | Description |
|:-------|:--------|:-----|:------------|
| `isolated()` | `ExecutionSpec[T]` | WHERE | Execute without context |
| `snapshot()` | `ExecutionSpec[T]` | WHERE | Read-only context snapshot |
| `stream()` | `ExecutionSpec[T]` | HOW | Enable streaming mode |
| `silent()` | `ExecutionSpec[T]` | HOW | Suppress UI display |
| `max_turns(n)` | `ExecutionSpec[T]` | LIMITS | Limit execution turns |
| `run_config(cfg)` | `ExecutionSpec[T]` | SDK | Set RunConfig |
| `context(ctx)` | `ExecutionSpec[T]` | SDK | Inject context (DI) |
| `run_kwarg(**kw)` | `ExecutionSpec[T]` | SDK | Set arbitrary SDK params |
| `__await__` | `T` | - | Execute and return result |

**Example:**

```python
spec = assistant("Hello")           # ExecutionSpec[str]
spec = spec.stream()                # ExecutionSpec[str] with is_streaming=True
result = await spec                 # str

# With SDK pass-through
result = await agent("task") \
    .max_turns(5) \
    .context(app_ctx) \
    .stream()
```

---

## Runner

```python
import agentic_flow as af
```

### Runner

Flow execution container with session, handler, and `default_run_config`
injection.

```python
class Runner:
    def __init__(
        self,
        flow: Callable[[str], Awaitable[T]],
        session: Session | None = None,
        handler: af.Handler | None = None,
        default_run_config: RunConfig | None = None,
    ) -> None: ...

    async def __call__(self, user_message: str) -> T: ...
    def run(self, user_message: str) -> af.RunHandle: ...
    def run_sync(self, user_message: str) -> T: ...
```

**Parameters:**

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `flow` | `Callable[[str], Awaitable[T]]` | Async function to execute |
| `session` | `Session \| None` | SDK Session for history |
| `handler` | `Handler \| None` | Event handler |
| `default_run_config` | `RunConfig \| None` | App-wide `RunConfig` (sandbox transport, tracing, model overrides) injected via `current_run_config` contextvar; per-call `.run_config()` modifier on `ExecutionSpec` overrides this |

**Methods:**

| Method | Returns | Description |
|:-------|:--------|:------------|
| `__call__(msg)` | `T` | Execute flow (async) |
| `run(msg)` | `RunHandle` | Create deferred handle |
| `run_sync(msg)` | `T` | Execute synchronously |

**Example:**

```python
import agentic_flow as af
from agents import SQLiteSession

runner = af.Runner(
    flow=my_flow,
    session=SQLiteSession("chat.db"),
    handler=my_handler,
)

# Async
result = await runner("Hello")

# Sync
result = runner.run_sync("Hello")

# Deferred
result = runner.run("Hello").sync()
```

---

## RunHandle

```python
import agentic_flow as af
```

### RunHandle

Deferred execution handle for synchronous contexts.

```python
class RunHandle:
    def sync(self) -> T: ...
    def __await__(self): ...
```

**Methods:**

| Method | Returns | Description |
|:-------|:--------|:------------|
| `sync()` | `T` | Execute synchronously |
| `__await__` | `T` | Execute asynchronously |

---

## phase

```python
import agentic_flow as af
```

### phase()

Context manager for workflow phases.

```python
@asynccontextmanager
async def phase(
    label: str,
    share_context: bool = True,
    persist: bool = False,
) -> AsyncIterator[PhaseSession | None]: ...
```

**Parameters:**

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `label` | `str` | (required) | Phase display name |
| `share_context` | `bool` | `True` | Create PhaseSession |
| `persist` | `bool` | `False` | Write to Session at end |

**Example:**

```python
async with af.phase("Research"):
    result = await agent(query).stream()

async with af.phase("Response", persist=True):
    return await agent(result).stream()
```

---

## PhaseSession

```python
import agentic_flow as af
```

### PhaseSession

SessionABC-compliant session for phase execution.

```python
class PhaseSession(SessionABC):
    session_id: str
    label: str
    data: dict
    inherited_history: list[TResponseInputItem]
    items: list[TResponseInputItem]

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]: ...
    async def add_items(self, items: list[TResponseInputItem]) -> None: ...
    async def pop_item(self) -> TResponseInputItem | None: ...
    async def clear_session(self) -> None: ...
```

**Attributes:**

| Attribute | Type | Description |
|:----------|:-----|:------------|
| `label` | `str` | Phase label |
| `inherited_history` | `list` | Session history at phase start (read-only) |
| `items` | `list` | Messages within phase (SDK-managed) |
| `data` | `dict` | Custom data storage |

**Methods:**

| Method | Returns | Description |
|:-------|:--------|:------------|
| `get_items(limit)` | `list` | `inherited_history + items` (async) |
| `add_items(items)` | `None` | Add items to `items` (called by SDK) |
| `pop_item()` | `item \| None` | Pop from `items` |
| `clear_session()` | `None` | Clear `items` |

**Example:**

```python
async with af.phase("Research") as ctx:
    await agent(query).stream()
    ctx.my_note = "important"
    print(ctx.my_note)
```

---

## Event Types

```python
import agentic_flow as af
```

### Event

Union type for all events:

```python
Event = PhaseStarted | PhaseEnded | AgentResult
```

### PhaseStarted

```python
@dataclass(frozen=True)
class PhaseStarted:
    type: Literal["phase.started"]
    label: str
    ts: float
```

### PhaseEnded

```python
@dataclass(frozen=True)
class PhaseEnded:
    type: Literal["phase.ended"]
    label: str
    elapsed_ms: int
    ts: float
```

### AgentResult

```python
@dataclass(frozen=True)
class AgentResult:
    type: Literal["agent.result"]
    content: Any
    ts: float
```

### Handler

```python
Handler = Callable[[Event], Any]
```

---

## Handler Events

Handler receives AF events only. SDK streaming deltas are consumed internally and **not** forwarded to the handler. Display is always full-text-at-once.

**Events the handler receives:**

| Event | When | Key Fields |
|:------|:-----|:-----------|
| `AgentResult` | After each agent execution | `content: Any` (full output) |
| `PhaseStarted` | On `phase()` entry | `label: str` |
| `PhaseEnded` | On `phase()` exit | `label: str`, `elapsed_ms: int` |

**Display fallback:** ChatKit > Handler > `print()` (mutually exclusive).

**Example: Handler**

```python
import agentic_flow as af

def handler(event):
    if isinstance(event, af.PhaseStarted):
        print(f"\n[{event.label}]")
    elif isinstance(event, af.PhaseEnded):
        print(f"  ({event.elapsed_ms}ms)")
    elif isinstance(event, af.AgentResult):
        print(event.content)
```

---

## Utilities

```python
import agentic_flow as af
```

### reasoning()

Create ModelSettings with reasoning enabled.

```python
def reasoning(
    effort: Literal["low", "medium", "high"] = "medium",
    summary: Literal["auto", "concise", "detailed"] = "auto",
    **model_settings_kwargs: Any,
) -> ModelSettings: ...
```

**Parameters:**

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `effort` | `str` | `"medium"` | Reasoning effort level |
| `summary` | `str` | `"auto"` | Summary style |
| `**kwargs` | `Any` | | Additional ModelSettings args |

**Example:**

```python
import agentic_flow as af

agent = af.Agent(
    name="thinker",
    instructions="Think step by step.",
    model="gpt-5.5",
    model_settings=af.reasoning("high"),
)
```

---

## ChatKit Integration

```python
from agentic_flow.chatkit import run_with_chatkit_context
```

### run_with_chatkit_context()

Execute Runner with ChatKit context.

```python
async def run_with_chatkit_context(
    runner: Runner,
    thread: ThreadMetadata,
    store: Store,
    context: dict[str, Any],
    user_message: str,
) -> AsyncIterator[ThreadStreamEvent]: ...
```

ChatKit mode preserves Runner's full injection contract: this function sets
`current_chatkit_context` and then delegates flow execution to
`Runner.__call__`, so `session`, `handler`, and `default_run_config` reach
every agent call exactly as in non-ChatKit mode. See
[Flow & Runner: ChatKit Mode](../concepts/flow-runner.md#chatkit-mode).

**Parameters:**

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `runner` | `Runner` | Runner instance |
| `thread` | `ThreadMetadata` | ChatKit thread |
| `store` | `Store` | ChatKit store |
| `context` | `dict` | Request context |
| `user_message` | `str` | User message |

**Yields:** `ThreadStreamEvent`

---

## Public Exports

```python
import agentic_flow as af

# Available exports:
# af.Agent, af.SandboxAgent, af.ExecutionSpec, af.Runner, af.RunHandle,
# af.phase, af.PhaseSession, af.Handler, af.Event, af.PhaseStarted,
# af.PhaseEnded, af.AgentResult, af.reasoning
```
