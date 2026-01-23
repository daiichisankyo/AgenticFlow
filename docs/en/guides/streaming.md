# Streaming

Streaming enables real-time output display. This guide covers CLI streaming with handlers.

## Basic Streaming

Add `.stream()` to enable streaming:

```python
result = await assistant("Hello").stream()
```

Without `.stream()`, you get only the final result. With `.stream()`, events are forwarded to your handler as they arrive.

## CLI Handler

For command-line output, create a handler:

```python
import agentic_flow as af

assistant = af.Agent(name="assistant", instructions="...", model="gpt-5.2")

def cli_handler(event):
    # Text delta from streaming
    if hasattr(event, "data") and hasattr(event.data, "delta"):
        print(event.data.delta, end="", flush=True)

async def my_flow(message: str) -> str:
    async with af.phase("Response"):
        return await assistant(message).stream()

runner = af.Runner(flow=my_flow, handler=cli_handler)
result = runner.run_sync("Hello!")
print()  # Newline after streaming
```

## Handler and Event Types

Your handler receives various event types:

```python
import agentic_flow as af, af.AgentResult

def full_handler(event):
    # Phase boundaries
    if isinstance(event, af.PhaseStarted):
        print(f"\n[{event.label}]")
        return

    if isinstance(event, af.PhaseEnded):
        print(f"\n[/{event.label}] ({event.elapsed_ms}ms)")
        return

    # Non-streaming agent result
    if isinstance(event, af.AgentResult):
        print(event.content)
        return

    # Streaming text delta
    if hasattr(event, "data") and hasattr(event.data, "delta"):
        print(event.data.delta, end="", flush=True)
```

## SDK StreamEvent

Most streaming events are SDK `StreamEvent` objects wrapped in `raw_response_event`. The `data.type` field identifies the specific event:

| Event Type | Description | Key Attributes |
|:-----------|:------------|:---------------|
| `response.output_text.delta` | Text output chunk | `data.delta` (str) |
| `response.reasoning_summary_text.delta` | Reasoning summary chunk | `data.delta` (str) |
| `response.function_call_arguments.delta` | Tool arguments chunk | `data.delta` (str, JSON fragment) |
| `response.output_item.added` | New output item started | `data.item` (type, name) |

```python
def inspect_handler(event):
    # Check for raw_response_event wrapper
    if getattr(event, "type", None) != "raw_response_event":
        return

    data = getattr(event, "data", None)
    if not data:
        return

    data_type = getattr(data, "type", "")

    # Text output
    if data_type == "response.output_text.delta":
        print(data.delta, end="", flush=True)

    # Reasoning (for separate display)
    elif data_type == "response.reasoning_summary_text.delta":
        print(f"[Reasoning] {data.delta}")

    # Tool call arguments (JSON streaming)
    elif data_type == "response.function_call_arguments.delta":
        print(f"[Tool Args] {data.delta}")

    # New tool call started
    elif data_type == "response.output_item.added":
        item = getattr(data, "item", None)
        if item and getattr(item, "type", "") == "function_call":
            print(f"[Tool] {getattr(item, 'name', 'unknown')}")
```

## Dual-Panel Display

For advanced CLI applications, separate reasoning from output:

```python
class DualPanelHandler:
    def __init__(self):
        self.reasoning_buffer = ""
        self.output_buffer = ""

    def __call__(self, event):
        if getattr(event, "type", None) != "raw_response_event":
            return

        data = getattr(event, "data", None)
        if not data:
            return

        data_type = getattr(data, "type", "")
        delta = getattr(data, "delta", "")

        if data_type == "response.reasoning_summary_text.delta":
            self.reasoning_buffer += delta
            self.refresh_display()
        elif data_type == "response.output_text.delta":
            self.output_buffer += delta
            self.refresh_display()

    def refresh_display(self):
        # Update your UI with separate panels
        pass
```

This pattern enables:

- **Reasoning Panel**: Shows LLM thinking process
- **Output Panel**: Shows final response
- **Tool Panel**: Shows tool calls and arguments

## Async Handlers

Handlers can be async:

```python
async def async_handler(event):
    if hasattr(event, "data") and hasattr(event.data, "delta"):
        await some_async_operation(event.data.delta)
```

AF detects async handlers and awaits them.

## Streaming Without Handler

If no handler is set, `.stream()` still works — it just doesn't output anywhere:

```python
# No handler — streaming happens internally but no display
runner = af.Runner(flow=my_flow)
result = await runner("Hello")
```

The agent still runs in streaming mode, which may affect behavior (e.g., reasoning display).

## Silent Streaming

Combine `.silent()` with `.stream()` for internal streaming without display:

```python
async with af.phase("Background"):
    # Streams internally but suppresses handler/UI output
    result = await agent("task").stream().silent()
```

## Reasoning Display

With `ModelSettings` containing reasoning, streaming emits `response.reasoning_summary_text.delta` events:

```python
import agentic_flow as af

agent = af.Agent(
    name="thinker",
    instructions="Think step by step.",
    model="gpt-5.2",
    model_settings=af.reasoning("medium"),  # Helper for reasoning config
)

# Reasoning steps appear as separate event type
result = await agent("Complex problem").stream()
```

To display reasoning separately from output:

```python
def reasoning_aware_handler(event):
    if getattr(event, "type", None) != "raw_response_event":
        return

    data = getattr(event, "data", None)
    if not data:
        return

    data_type = getattr(data, "type", "")
    delta = getattr(data, "delta", "")

    if data_type == "response.reasoning_summary_text.delta":
        # Display in reasoning panel (dimmed, separate area)
        print(f"\033[2m{delta}\033[0m", end="", flush=True)
    elif data_type == "response.output_text.delta":
        # Display in main output area
        print(delta, end="", flush=True)
```

## Complete Example

```python
import agentic_flow as af, af.PhaseStarted, af.PhaseEnded

researcher = af.Agent(
    name="researcher",
    instructions="Research thoroughly.",
    model="gpt-5.2",
    model_settings=af.reasoning("medium"),
)

responder = af.Agent(
    name="responder",
    instructions="Provide clear responses.",
    model="gpt-5.2",
)


def cli_handler(event):
    if isinstance(event, af.PhaseStarted):
        print(f"\n--- {event.label} ---")
        return

    if isinstance(event, af.PhaseEnded):
        print(f"\n--- /{event.label} ({event.elapsed_ms}ms) ---\n")
        return

    if hasattr(event, "data") and hasattr(event.data, "delta"):
        print(event.data.delta, end="", flush=True)


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
