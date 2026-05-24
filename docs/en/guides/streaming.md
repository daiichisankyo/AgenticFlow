# Streaming

`.stream()` controls the internal execution mode — it uses the streaming API for faster first-token latency. Display is always full-text-at-once regardless of execution mode.

## Basic Streaming

Add `.stream()` to use the streaming API internally:

```python
result = await assistant("Hello").stream()
```

Both `.stream()` and non-streaming paths deliver the same result. The difference is internal: `.stream()` uses `Runner.run_streamed` for faster first-token, while non-streaming uses `Runner.run`.

## Display Model

AF uses a full-text-at-once display model. When an agent completes, the result is delivered through a fallback chain:

```
ChatKit > Handler > print()
```

- **ChatKit context active**: Result emitted to ChatKit UI
- **Handler set (no ChatKit)**: `AgentResult(content=output)` sent to handler
- **Neither**: `print(output)` to stdout

This applies to both `.stream()` and non-streaming execution.

## CLI Handler

For command-line output, create a handler that receives `AgentResult`:

```python
import agentic_flow as af

assistant = af.Agent(name="assistant", instructions="...", model="gpt-5.5")

def cli_handler(event):
    # Agent completed — display full result
    if isinstance(event, af.AgentResult):
        print(event.content)

async def my_flow(message: str) -> str:
    async with af.phase("Response"):
        return await assistant(message).stream()

runner = af.Runner(flow=my_flow, handler=cli_handler)
result = runner.run_sync("Hello!")
```

## Handler Event Types

Your handler receives three event types:

```python
import agentic_flow as af

def full_handler(event):
    # Phase boundaries
    if isinstance(event, af.PhaseStarted):
        print(f"\n[{event.label}]")
        return

    if isinstance(event, af.PhaseEnded):
        print(f"\n[/{event.label}] ({event.elapsed_ms}ms)")
        return

    # Agent result (full text, emitted once per agent call)
    if isinstance(event, af.AgentResult):
        print(event.content)
        return
```

| Event Type | When Emitted | Key Attributes |
|:-----------|:-------------|:---------------|
| `af.PhaseStarted` | Entering a phase | `label` (str) |
| `af.PhaseEnded` | Exiting a phase | `label` (str), `elapsed_ms` (int) |
| `af.AgentResult` | Agent execution completes | `content` (Any — str or Pydantic model) |

!!! note "SDK StreamEvents are internal"
    SDK streaming events (text deltas, reasoning deltas, tool call events) are consumed internally by `ExecutionSpec` and are **not** forwarded to handlers. Handlers receive only `AgentResult` with the full output.

## Async Handlers

Handlers can be async:

```python
async def async_handler(event):
    if isinstance(event, af.AgentResult):
        await some_async_operation(event.content)
```

AF detects async handlers and awaits them.

## Without Handler

If no handler is set (and no ChatKit context), output is printed to stdout via `print()`:

```python
# No handler — output is printed to stdout
runner = af.Runner(flow=my_flow)
result = await runner("Hello")
# Each agent result is printed automatically
```

## Silent Mode

`.silent()` suppresses all display — no handler calls, no ChatKit events, no print output:

```python
async with af.phase("Background"):
    # Executes but produces no display output
    result = await agent("task").stream().silent()
```

!!! note "Phase label still displays"
    `.silent()` controls visibility at the agent call level. The `phase()` label itself is a UX boundary and still displays in ChatKit.

    ```python
    async with af.phase("Research"):  # Label appears in UI
        r = await agent(msg).silent().stream()  # Output hidden
    ```

## Reasoning with ChatKit

Reasoning display (step-by-step thinking) is available through ChatKit's workflow boundaries. Each `phase()` creates a workflow in ChatKit that can display reasoning separately from output:

```python
import agentic_flow as af

agent = af.Agent(
    name="thinker",
    instructions="Think step by step.",
    model="gpt-5.5",
    model_settings=af.reasoning("medium"),  # Helper for reasoning config
)

# In ChatKit mode, reasoning steps appear in workflow display
# In CLI mode, only the final AgentResult is delivered to handler
result = await agent("Complex problem").stream()
```

For CLI applications, the handler receives `AgentResult` with the final output only. Reasoning steps are consumed internally and not exposed to the handler.

## Complete Example

```python
import agentic_flow as af

researcher = af.Agent(
    name="researcher",
    instructions="Research thoroughly.",
    model="gpt-5.5",
    model_settings=af.reasoning("medium"),
)

responder = af.Agent(
    name="responder",
    instructions="Provide clear responses.",
    model="gpt-5.5",
)


def cli_handler(event):
    if isinstance(event, af.PhaseStarted):
        print(f"\n--- {event.label} ---")
        return

    if isinstance(event, af.PhaseEnded):
        print(f"\n--- /{event.label} ({event.elapsed_ms}ms) ---\n")
        return

    if isinstance(event, af.AgentResult):
        print(event.content)


async def research_flow(message: str) -> str:
    async with af.phase("Research"):
        findings = await researcher(message).stream()

    async with af.phase("Response", persist=True):
        return await responder(f"Based on: {findings}").stream()


runner = af.Runner(flow=research_flow, handler=cli_handler)

if __name__ == "__main__":
    result = runner.run_sync("Explain quantum entanglement")
    print(f"\nFinal: {result[:100]}...")
```

---

:material-arrow-right: **Next**: [CLI Display Patterns](cli-patterns.md) for advanced Rich/terminal UI

:material-arrow-right: **Or**: [ChatKit Integration](chatkit.md) for web UI
