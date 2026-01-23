# Quickstart

Get a multi-agent workflow running in 5 minutes.

## The Goal

We'll build a simple research-and-respond flow:

1. A **researcher** agent gathers information
2. A **responder** agent formulates a user-facing answer

## Step 1: Define Agents

```python
import agentic_flow as af

researcher = af.Agent(
    name="researcher",
    instructions="Research the given topic. Provide detailed findings.",
    model="gpt-5.2",
)

responder = af.Agent(
    name="responder",
    instructions="Based on research findings, provide a clear response to the user.",
    model="gpt-5.2",
)
```

Each `Agent` wraps the OpenAI Agents SDK. All SDK arguments (`model`, `instructions`, `tools`, etc.) pass through directly.

## Step 2: Define the Flow

```python
import agentic_flow as af

async def research_flow(user_message: str) -> str:
    # Phase 1: Research (internal thinking, not saved to session)
    async with af.phase("Research"):
        findings = await researcher(user_message).stream()

    # Phase 2: Response (persist=True saves to session)
    async with af.phase("Response", persist=True):
        return await responder(f"Research findings:\n{findings}").stream()
```

**Key points:**

- `phase()` creates a boundary — cleanup is automatic
- `.stream()` enables streaming output
- `persist=True` writes the final result to the session

## Step 3: Run with a Runner

```python
import agentic_flow as af
from agents import SQLiteSession

runner = af.Runner(
    flow=research_flow,
    session=SQLiteSession("conversation.db"),
)

# Async execution
result = await runner("What is quantum computing?")
print(result)

# Or synchronous (for scripts/Jupyter)
result = runner.run_sync("What is quantum computing?")
print(result)
```

## Full Example

```python
import agentic_flow as af
from agents import SQLiteSession

# Define agents
researcher = af.Agent(
    name="researcher",
    instructions="Research the given topic. Provide detailed findings.",
    model="gpt-5.2",
)

responder = af.Agent(
    name="responder",
    instructions="Based on research findings, provide a clear response to the user.",
    model="gpt-5.2",
)

# Define flow
async def research_flow(user_message: str) -> str:
    # Internal thinking - not saved to session
    async with af.phase("Research"):
        findings = await researcher(user_message).stream()

    # persist=True saves the final response to session
    async with af.phase("Response", persist=True):
        return await responder(f"Research findings:\n{findings}").stream()

# Run
runner = af.Runner(
    flow=research_flow,
    session=SQLiteSession("conversation.db"),
)

result = runner.run_sync("What is quantum computing?")
print(result)
```

## What Just Happened?

1. `researcher(user_message)` created an `ExecutionSpec` — no execution yet
2. `.stream()` added streaming mode — still no execution
3. `await` triggered the actual execution
4. `phase("Research")` wrapped the execution with automatic boundary management
5. The responder received the research findings and generated a response
6. `persist=True` saved the final exchange to the SQLite session

## Next Steps

- [Your First Flow](first-flow.md) — Deeper dive into flow structure
- [Concepts](../concepts/index.md) — Understand Call-Spec discipline
- [Streaming](../guides/streaming.md) — Add real-time output

---

Next: [Your First Flow](first-flow.md) :material-arrow-right:
