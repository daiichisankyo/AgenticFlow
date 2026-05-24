# Flow & Runner

AF separates **what** your workflow does (Flow) from **how** it's executed (Runner).

## Flow: Business Logic

A Flow is a regular async Python function:

```python
async def my_flow(user_message: str) -> str:
    async with af.phase("Research"):
        research = await researcher(user_message).stream()

    async with af.phase("Response", persist=True):
        return await responder(f"Based on: {research}").stream()
```

**Flow's responsibilities:**

| Responsibility | Example |
|:---------------|:--------|
| Agent call order | Which agents run in what sequence |
| Control flow | `if`, `for`, `while`, exception handling |
| Data transformation | Combining agent outputs |
| Phase structure | Where to put boundaries |

**Flow does NOT know about:**

- Sessions — Injected by Runner
- Handlers — Injected by Runner
- RunConfig (sandbox transport, tracing, model overrides) — Injected by Runner via `default_run_config`
- ChatKit — Integrated at Runner level

This separation keeps business logic clean.

## Runner: Execution Environment

A Runner wraps a Flow and provides the execution environment:

```python
import agentic_flow as af
from agents import RunConfig, SQLiteSession

runner = af.Runner(
    flow=my_flow,
    session=SQLiteSession("chat.db"),
    handler=my_handler,
    default_run_config=RunConfig(...),
)

result = await runner("Hello!")
```

**Runner's responsibilities:**

| Responsibility | How |
|:---------------|:----|
| Session injection | Via `contextvars` |
| Handler injection | Via `contextvars` |
| RunConfig injection (`default_run_config`) | Via `contextvars` (`current_run_config`) |
| Flow execution | Calls `await self.flow(user_message)` |

## How Injection Works

Runner uses Python's `contextvars` to inject dependencies:

```python
async def __call__(self, user_message: str) -> Any:
    # Inject session, handler, and default run_config
    session_token = current_session.set(self.session)
    handler_token = current_handler.set(self.handler)
    run_config_token = current_run_config.set(self.default_run_config)

    try:
        return await self.flow(user_message)
    finally:
        # Clean up (reverse order)
        current_run_config.reset(run_config_token)
        current_handler.reset(handler_token)
        current_session.reset(session_token)
```

This means:

- Flow code never sees `session` or `handler` directly
- `af.ExecutionSpec.execute()` reads them from context when needed
- Context is properly scoped and cleaned up

## ChatKit Mode

`af.chatkit.run_with_chatkit_context(runner, thread, store, context, msg)`
does **not** bypass `Runner`. It adds `current_chatkit_context` and then
delegates flow execution to `Runner.__call__`, so `session`, `handler`, and
`default_run_config` are injected exactly as in non-ChatKit mode. This is
why `Runner(default_run_config=RunConfig(sandbox=SandboxRunConfig(...)))` —
required by `af.SandboxAgent` — works identically through ChatKit.

## Synchronous Execution

Runner provides synchronous execution for scripts and Jupyter:

```python
# Option 1: run_sync()
result = runner.run_sync("Hello")

# Option 2: run().sync()
result = runner.run("Hello").sync()
```

Both methods handle event loop creation appropriately:

- **No running loop**: Uses `asyncio.run()`
- **Running loop (Jupyter)**: Uses a thread pool

!!! warning "sync() is a Runner adapter"
    `sync()` is NOT a third execution trigger for `af.ExecutionSpec`. It's a Runner-level convenience that internally awaits the flow.

## Working Without Runner

You can use agents without Runner — they'll just lack session context:

```python
import agentic_flow as af

assistant = af.Agent(name="assistant", instructions="...", model="gpt-5.5")

# Works, but no session
result = await assistant("Hello")
```

Each call is independent with no conversation history.

## Handler Pattern

Handlers receive AF events (not SDK streaming deltas):

```python
import agentic_flow as af

def my_handler(event):
    if isinstance(event, af.PhaseStarted):
        print(f"\n[{event.label}]")
    elif isinstance(event, af.PhaseEnded):
        print(f"  ({event.elapsed_ms}ms)")
    elif isinstance(event, af.AgentResult):
        print(event.content)
```

Handlers are called for:

- `af.AgentResult` — Full-text agent output (both streaming and non-streaming paths)
- `af.PhaseStarted` / `af.PhaseEnded` — Phase boundary events

Display fallback priority: ChatKit > Handler > `print()` (mutually exclusive). When no handler or ChatKit is active, output is printed to stdout.

## Summary

| Concept | Role |
|:--------|:-----|
| **Flow** | Business logic — agent orchestration |
| **Runner** | Execution environment — session/handler injection |
| **Session** | Conversation history (from SDK) |
| **Handler** | Event receiver for streaming output |
| **contextvars** | Injection mechanism |

```mermaid
graph TB
    subgraph Flow["Flow (Business Logic)"]
        A(Agent Calls)
        B(phase Structure)
        C(Python Control Flow)
    end

    subgraph Runner["Runner (Execution Environment)"]
        D(Session Injection)
        E(Handler Injection)
        F(ChatKit Integration)
    end

    Flow -->|"injected into"| Runner
```

---

Next: [Phase](phase.md) :material-arrow-right:
