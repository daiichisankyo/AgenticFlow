# AF - Agentic Flow Framework

**Call-Spec Discipline for LLM Agent Workflows**

---

## See the Difference

Writing multi-agent flows with the Pure SDK requires significant boilerplate.
The agentic flow pattern eliminates it.

??? example "Pure SDK + ChatKit — ~126 lines of ceremony :material-arrow-down:"

    ```python
    --8<-- "docs/examples/pure_sdk_chatkit.py"
    ```

    **Problems:**

    - [x] Manual `emit_phase_label()` + `close_workflow()` for every phase
    - [x] `async for event in stream_agent_response()` repeated everywhere
    - [x] `try/finally` blocks to ensure `close_workflow()` on errors
    - [x] Event queue management boilerplate
    - [x] Business logic buried in infrastructure code

**The same workflow using the agentic flow approach:**

=== "Flow — 43 lines :material-check:"

    ```python
    --8<-- "docs/examples/agenticflow_flow.py"
    ```

=== "ChatKit Server — 20 lines"

    ```python
    --8<-- "docs/examples/agenticflow_chatkit.py"
    ```

=== "CLI — 16 lines"

    ```python
    --8<-- "docs/examples/agenticflow_cli.py"
    ```

<div class="grid" markdown>

| Aspect | Pure SDK | AF |
|:-------|:--------:|:-----------:|
| Lines of code | ~126 | ~43 |
| Phase management | Manual | Automatic |
| Error handling | try/finally | Automatic |
| Adding streaming | Rewrite | `.stream()` |

</div>

---

## How It Works: Call-Spec Discipline

The secret is simple: **separate declaration from execution**.

```python
import agentic_flow as af

assistant = af.Agent(name="assistant", instructions="Help the user.", model="gpt-5.2")

# Declaration — creates a specification, NOT executed
spec = assistant("Hello")

# Execution — happens here, and ONLY here
result = await spec
```

| Expression | What it does | Executes? |
|:-----------|:-------------|:---------:|
| `agent(prompt)` | Creates `ExecutionSpec[T]` | :material-close: No |
| `.stream()` / `.silent()` / `.isolated()` | Adds modifiers | :material-close: No |
| `await spec` | Runs the agent | :material-check: **Yes** |

This makes your code:

- **Readable** — Execution points visible by scanning for `await`
- **Debuggable** — Set breakpoints at the single execution trigger
- **Maintainable** — Adding streaming is one modifier, not a structural rewrite

[:octicons-arrow-right-24: Learn more about Call-Spec Discipline](concepts/index.md)

---

## Quick Start

```python
import agentic_flow as af
from agents import SQLiteSession

researcher = af.Agent(name="researcher", instructions="Research topics.", model="gpt-5.2")
responder = af.Agent(name="responder", instructions="Respond to user.", model="gpt-5.2")

async def my_flow(user_message: str) -> str:
    # Internal thinking - not saved to session
    async with af.phase("Research"):
        research = await researcher(user_message).stream()

    # persist=True saves the final response to session
    async with af.phase("Response", persist=True):
        return await responder(f"Based on: {research}").stream()

runner = af.Runner(flow=my_flow, session=SQLiteSession("chat.db"))
result = await runner("What is Python?")
```

---

## Installation

```bash
# With uv (recommended)
uv add ds-agentic-flow

# With pip
pip install ds-agentic-flow
```

---

## Next Steps

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Install and run your first agent in 5 minutes

    [:octicons-arrow-right-24: Quickstart](getting-started/quickstart.md)

-   :material-book-open-variant:{ .lg .middle } **Concepts**

    ---

    Deep dive into Call-Spec discipline

    [:octicons-arrow-right-24: Concepts](concepts/index.md)

-   :material-code-braces:{ .lg .middle } **Examples**

    ---

    Multi-agent workflows, review loops, and more

    [:octicons-arrow-right-24: Examples](examples/multi-agent.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation

    [:octicons-arrow-right-24: Reference](reference/api.md)

</div>

---

## Links

- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [ChatKit](https://platform.openai.com/docs/guides/chatkit)

