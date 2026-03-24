# Modifiers

Modifiers configure execution behavior without triggering execution. They return a new `ExecutionSpec` with updated flags.

## Modifier Categories

| Axis | Modifiers | Purpose |
|:-----|:----------|:--------|
| WHERE | `.isolated()`, `.snapshot()` | Context control |
| HOW | `.stream()`, `.silent()` | Control execution mode and display |
| LIMITS | `.max_turns(n)` | Limit execution |
| SDK | `.run_config()`, `.context()`, `.run_kwarg()` | SDK parameters |

---

## WHERE Axis

### .isolated()

Executes without any context — no Session, no PhaseSession.

```python
result = await translator("Hello").isolated()
```

**What isolated means:**

- Does NOT read from Session
- Does NOT write to Session
- Ignores PhaseSession entirely
- Completely stateless execution

**Use cases:**

- Pure transformations (translation, formatting)
- Temporary evaluation
- Stateless operations

```python
# Pure transformation — no context needed
result = await translator("Bonjour le monde").isolated()
```

!!! tip "For parallel execution, prefer `.snapshot()`"
    `.isolated()` is concurrent-safe but provides no context. For parallel agents that need conversation history, use [`.snapshot()`](#snapshot) instead.

### .snapshot()

Read-only context snapshot. Concurrent-safe for `asyncio.gather()`.

```python
result = await agent("Deep dive on aspect A").snapshot()
```

**What snapshot means:**

- Reads from PhaseSession (if inside phase) or Session (if outside)
- Does NOT write to PhaseSession or Session
- Returns `None` as session to SDK, preventing writes
- Concurrent-safe — multiple `.snapshot()` calls can run in parallel

**WHERE axis spectrum:**

```
.isolated()    .snapshot()     (default)
 ───────────────────────────────────────►
 No context    Read-only       Read + Write
```

| | Session Read | Session Write | PhaseSession Read | PhaseSession Write |
|---|:---:|:---:|:---:|:---:|
| (default) | Yes | Yes | Yes | Yes |
| `.snapshot()` | Yes | No | Yes | No |
| `.isolated()` | No | No | No | No |

**Use cases:**

- Parallel execution with shared context (`asyncio.gather`)
- Read-only analysis that shouldn't pollute conversation history
- Fan-out pattern where multiple agents read the same context

```python
async with af.phase("Research"):
    # First agent writes to PhaseSession normally
    overview = await researcher(query).stream()

    # Parallel deep-dives — each reads overview, doesn't write
    deep_a, deep_b = await asyncio.gather(
        specialist_a("Deep dive on aspect A").snapshot(),
        specialist_b("Deep dive on aspect B").snapshot(),
    )
```

!!! note "isolated() wins over snapshot()"
    If both `.isolated()` and `.snapshot()` are set, `.isolated()` takes precedence. The result is fully isolated execution with no context.

    ```python
    # isolated() wins — no context at all
    result = await agent("task").snapshot().isolated()  # = isolated()
    ```

---

## HOW Axis

### .stream()

Enables streaming execution mode. Uses the streaming API internally for faster first-token latency. The stream is consumed internally — delta events are **not** forwarded to the handler. Display is always full-text-at-once via `AgentResult`.

```python
result = await assistant("Hello").stream()
```

**What `.stream()` controls:**

- Internal execution mode (streaming API vs batch API)
- Faster first-token latency for long responses

**What `.stream()` does NOT change:**

- Display behavior — always full-text via `AgentResult`
- Handler events — receives `AgentResult`, not deltas

**With or without `.stream()`:**

```python
# Both paths emit AgentResult to handler with full text
result = await assistant("Hello").stream()  # Streaming API internally
result = await assistant("Hello")           # Batch API internally
```

### .silent()

Suppresses UI display. The agent still executes normally.

```python
result = await assistant("Background task").silent()
```

**What .silent() affects:**

- Handler event forwarding (disabled)
- ChatKit event queue (disabled)

**What .silent() does NOT affect:**

- PhaseSession writes (still happens)
- Execution itself (agent runs normally)
- Return value (still returns `T`)

**Use cases:**

- Background processing
- Internal tool calls
- Implementation details that shouldn't appear in UI

!!! note "Phase label still displays"
    `.silent()` controls visibility at the agent call level. The `phase()` label itself is a UX boundary and still displays in ChatKit.

    ```python
    async with af.phase("Research"):  # ← Label appears in UI
        r = await agent(msg).silent().stream()  # ← Output hidden
    ```

---

## LIMITS Axis

### .max_turns()

Limits the number of turns the agent can take during execution.

```python
result = await agent("Complex task").max_turns(5)
```

**What max_turns controls:**

- Maximum number of LLM invocations within a single agent run
- Tool call loops and handoff chains count toward this limit
- Once the limit is reached, execution stops

**Use cases:**

- Preventing runaway tool call loops
- Controlling costs in complex agent workflows
- Setting guardrails for autonomous agent behavior

```python
# Limit tool calls for safety
result = await researcher("Find information").max_turns(10).stream()

# Strict limit for simple tasks
result = await formatter("Format this text").max_turns(1)
```

!!! note "SDK Pass-through"
    This modifier maps directly to the `max_turns` parameter of `Runner.run()` in the OpenAI Agents SDK. It controls execution behavior at the SDK level.

---

## SDK Pass-Through Modifiers

These modifiers pass parameters directly to SDK's `Runner.run()`:

### .run_config()

Configure execution with RunConfig:

```python
from agents import RunConfig

# Disable tracing for this execution
result = await agent("prompt").run_config(
    RunConfig(tracing_disabled=True)
).stream()

# Override model for this execution
result = await agent("prompt").run_config(
    RunConfig(model="gpt-5.2-turbo")
)

# Set workflow name for tracing
result = await agent("prompt").run_config(
    RunConfig(workflow_name="my_workflow")
)
```

### .context()

Inject context for dependency injection:

```python
from dataclasses import dataclass

@dataclass
class AppContext:
    user_id: str
    api_key: str
    logger: Logger

ctx = AppContext(user_id="123", api_key="...", logger=logger)

# Context is available in tools and hooks
result = await agent("prompt").context(ctx).stream()
```

!!! note "Context is local, not sent to LLM"
    The context object is for local code only. It is not included in prompts.

!!! warning "Not supported in ChatKit mode"
    In ChatKit mode, `.context()` is silently overwritten by `AgentContext` (required for workflow boundaries). Use Agent hooks or pass data through the flow function for dependency injection in ChatKit.

### .run_kwarg()

Set arbitrary SDK parameters:

```python
# Conversation chaining
result = await agent("prompt").run_kwarg(
    previous_response_id="resp_abc123",
    conversation_id="conv_xyz",
)
```

---

## Combining Modifiers

Modifiers can be combined. **Order doesn't matter.**

```python
# All equivalent:
await agent("prompt").stream().silent()
await agent("prompt").silent().stream()

# All equivalent:
await agent("prompt").stream().isolated()
await agent("prompt").isolated().stream()

# snapshot + stream (WHERE + HOW)
result = await agent("task").snapshot().stream()

# snapshot + silent (WHERE + HOW)
result = await agent("task").snapshot().silent()

# snapshot + max_turns (WHERE + LIMITS)
result = await agent("task").snapshot().max_turns(3)

# Across axes:
await agent("prompt").stream().silent().isolated()

# With execution limit:
await agent("prompt").stream().max_turns(5)
await agent("prompt").max_turns(5).stream()  # Same result

# Full combination with SDK pass-through:
await agent("complex task") \
    .max_turns(10) \
    .context(app_ctx) \
    .run_config(RunConfig(tracing_disabled=True)) \
    .stream()
```

---

## Modifier Summary Table

| Modifier | Axis | UI Display | PhaseSession | Session | Execution |
|:---------|:-----|:----------:|:------------:|:-------:|:---------:|
| `.stream()` | HOW | Full-text | Yes | Yes | Streaming API |
| `.silent()` | HOW | No | Yes | Yes | Normal |
| `.snapshot()` | WHERE | Yes | Read-only | Read-only | Normal |
| `.isolated()` | WHERE | Yes | No | No | Normal |
| `.max_turns(n)` | LIMITS | Yes | Yes | Yes | Limited |
| `.run_config(cfg)` | SDK | Yes | Yes | Yes | Configured |
| `.context(ctx)` | SDK | Yes | Yes | Yes | With DI |
| `.run_kwarg(**kw)` | SDK | Yes | Yes | Yes | Configured |

---

## Implementation

Modifiers use `dataclasses.replace` to create new specs:

```python
def stream(self) -> ExecutionSpec[T]:
    return replace(self, is_streaming=True)

def silent(self) -> ExecutionSpec[T]:
    return replace(self, is_silent=True)

def isolated(self) -> ExecutionSpec[T]:
    return replace(self, is_isolated=True)

def snapshot(self) -> ExecutionSpec[T]:
    return replace(self, is_snapshot=True)

def max_turns(self, max_turns: int) -> ExecutionSpec[T]:
    return replace(self, max_turns_limit=max_turns)

def run_config(self, run_config: RunConfig) -> ExecutionSpec[T]:
    new_kwargs = {**self.run_kwargs, "run_config": run_config}
    return replace(self, run_kwargs=new_kwargs)

def context(self, context: Any) -> ExecutionSpec[T]:
    new_kwargs = {**self.run_kwargs, "context": context}
    return replace(self, run_kwargs=new_kwargs)

def run_kwarg(self, **kwargs: Any) -> ExecutionSpec[T]:
    new_kwargs = {**self.run_kwargs, **kwargs}
    return replace(self, run_kwargs=new_kwargs)
```

This ensures:

- Original spec is unchanged
- New spec is a separate object
- Specs can be reused

---

## Anti-Patterns

**Don't pass modifiers as arguments:**

```python
# Wrong — TypeError
await agent("prompt", stream=True)
await agent("prompt", isolated=True)
await agent("prompt", snapshot=True)

# Correct
await agent("prompt").stream()
await agent("prompt").isolated()
await agent("prompt").snapshot()
```

**Don't call modifiers on Agent directly:**

```python
# Wrong — TypeError
await agent.stream("prompt")

# Correct
await agent("prompt").stream()
```

These restrictions enforce the Call-Spec discipline: modifiers are on the spec, not the call.

---

Next: [Streaming Guide](../guides/streaming.md) :material-arrow-right:
