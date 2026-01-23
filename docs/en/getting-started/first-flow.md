# Your First Flow

This guide walks through building a flow step by step, explaining each concept as we go.

## What is a Flow?

A Flow is just an async Python function that orchestrates agent calls:

```python
async def my_flow(user_message: str) -> str:
    # Your agent orchestration logic here
    return result
```

There's no special syntax or DSL. It's regular Python.

## Step 1: Create an Agent

```python
import agentic_flow as af

assistant = af.Agent(
    name="assistant",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
)
```

`Agent` is a thin wrapper around the OpenAI Agents SDK's `Agent`. All SDK arguments pass through unchanged.

## Step 2: Call the Agent

```python
# This creates an ExecutionSpec — NOT executed yet
spec = assistant("Hello, how are you?")
```

**This is the Call-Spec discipline in action.** Calling an agent returns a specification, not a result.

## Step 3: Execute with await

```python
# This executes the agent
result = await spec
```

**Only `await` triggers execution.** This makes it clear exactly where side effects occur.

## Step 4: Add Modifiers

Modifiers configure execution behavior without triggering it:

```python
# Streaming mode
result = await assistant("Hello").stream()

# Silent mode (no UI output)
result = await assistant("Hello").silent()

# Isolated mode (no session context)
result = await assistant("Hello").isolated()

# Limit execution turns
result = await assistant("Hello").max_turns(5)

# Combine them (order doesn't matter)
result = await assistant("Hello").stream().silent()
result = await assistant("Hello").stream().max_turns(10)
```

## Step 5: Add Phases

Phases group related agent calls and manage boundaries:

```python
import agentic_flow as af

async def my_flow(user_message: str) -> str:
    async with af.phase("Thinking"):
        thought = await assistant("Think about: " + user_message).stream()

    async with af.phase("Responding", persist=True):
        return await assistant(f"Based on: {thought}, respond").stream()
```

**What `phase()` does:**

- Creates a semantic boundary for UI display
- Manages a temporary context for agent calls within the phase
- Automatically cleans up when the phase ends
- With `persist=True`, saves the last exchange to the session

## Step 6: Add a Runner

The Runner provides session management and executes the flow:

```python
import agentic_flow as af
from agents import SQLiteSession

runner = af.Runner(
    flow=my_flow,
    session=SQLiteSession("chat.db"),
)

# Execute
result = await runner("Hello!")
```

## Step 7: Add a Handler (Optional)

For CLI or custom output, add a handler:

```python
def my_handler(event):
    # Handle streaming events
    if hasattr(event, "data") and hasattr(event.data, "delta"):
        print(event.data.delta, end="", flush=True)

runner = af.Runner(
    flow=my_flow,
    session=SQLiteSession("chat.db"),
    handler=my_handler,
)
```

## Complete Example

```python
import agentic_flow as af
from agents import SQLiteSession

# Agent
assistant = af.Agent(
    name="assistant",
    instructions="You are a thoughtful assistant.",
    model="gpt-5.2",
)

# Flow
async def thoughtful_flow(user_message: str) -> str:
    # Internal thinking (not persisted)
    async with af.phase("Thinking"):
        thought = await assistant(
            f"Think step by step about: {user_message}"
        ).stream()

    # User-facing response (persisted)
    async with af.phase("Response", persist=True):
        return await assistant(
            f"Based on your thinking:\n{thought}\n\nProvide a clear response."
        ).stream()

# Handler for CLI output
def print_handler(event):
    if hasattr(event, "data") and hasattr(event.data, "delta"):
        print(event.data.delta, end="", flush=True)

# Runner
runner = af.Runner(
    flow=thoughtful_flow,
    session=SQLiteSession("chat.db"),
    handler=print_handler,
)

# Run
if __name__ == "__main__":
    result = runner.run_sync("Explain why the sky is blue.")
    print()  # Newline after streaming output
```

## Summary

| Concept | Purpose |
|:--------|:--------|
| `Agent` | Wraps SDK Agent, makes it callable |
| `agent(prompt)` | Creates `ExecutionSpec` (no execution) |
| `await spec` | Executes the agent |
| `.stream()` / `.silent()` / `.isolated()` | Modifiers (no execution) |
| `phase()` | Semantic boundary with automatic cleanup |
| `Runner` | Executes flows with session injection |

---

Next: [Call-Spec Discipline](../concepts/index.md) :material-arrow-right:
