# Modifiers

Modifiers configure execution behavior without triggering execution. They return a new `ExecutionSpec` with updated flags.

## Modifier Categories

| Axis | Modifiers | Purpose |
|:-----|:----------|:--------|
| WHERE | `.isolated()` | Ignore all context |
| HOW | `.stream()`, `.silent()` | Control display |
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
- Parallel execution (`asyncio.gather`)
- Temporary evaluation
- Stateless operations

```python
# Safe parallel execution
results = await asyncio.gather(
    search("topic A").isolated(),
    search("topic B").isolated(),
    search("topic C").isolated(),
)
```

---

## HOW Axis

### .stream()

Enables streaming mode. Events are forwarded to the handler as they arrive.

```python
result = await assistant("Hello").stream()
```

**What streaming enables:**

- Real-time text display in CLI or web UI
- Reasoning step visibility
- Tool call notifications
- Progress indication

**Without streaming:**

```python
result = await assistant("Hello")
# Handler receives only the final AgentResult
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
| `.stream()` | HOW | Streaming | Yes | Yes | Normal |
| `.silent()` | HOW | No | Yes | Yes | Normal |
| `.isolated()` | WHERE | No | No | No | Normal |
| `.max_turns(n)` | LIMITS | Yes | Yes | Yes | Limited |
| `.run_config(cfg)` | SDK | Yes | Yes | Yes | Configured |
| `.context(ctx)` | SDK | Yes | Yes | Yes | With DI |
| `.run_kwarg(**kw)` | SDK | Yes | Yes | Yes | Configured |

---

## Implementation

Modifiers use `dataclasses.replace` to create new specs:

```python
def stream(self) -> ExecutionSpec[T]:
    return replace(self, streaming=True)

def silent(self) -> ExecutionSpec[T]:
    return replace(self, is_silent=True)

def isolated(self) -> ExecutionSpec[T]:
    return replace(self, is_isolated=True)

def max_turns(self, max_turns: int) -> ExecutionSpec[T]:
    return replace(self, max_turns_sdk=max_turns)

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

# Correct
await agent("prompt").stream()
await agent("prompt").isolated()
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
