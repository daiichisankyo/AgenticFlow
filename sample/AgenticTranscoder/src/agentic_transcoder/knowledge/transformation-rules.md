# AgentBuilder → Agentic Flow Transformation Rules

This document defines rules for transforming AgentBuilder code to Agentic Flow.

---

## Import Transformation

| AgentBuilder | Agentic Flow |
|--------------|-------------|
| `from agents import Agent` | `from agentic_flow import Agent` |
| `from agents import Runner` | `from agentic_flow import Runner` |
| `from agents import trace` | Remove (not needed) |
| `from agents import ModelSettings` | `from agentic_flow import reasoning` |
| `from agents import TResponseInputItem` | Remove (not needed) |
| `from agents import RunConfig` | Remove (not needed) |

---

## Agent Definition

### Before (AgentBuilder)

```python
from agents import Agent, ModelSettings
from openai.types.shared.reasoning import Reasoning

my_agent = Agent(
    name="My agent",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
    model_settings=ModelSettings(
        store=True,
        reasoning=Reasoning(effort="low", summary="auto")
    ),
)
```

### After (Agentic Flow)

```python
# agent_specs.py
from agentic_flow import Agent, reasoning

chat_agent = Agent(
    name="chat",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
    model_settings=reasoning("low"),
)
```

**Note**: File name must be `agent_specs.py` (NOT `agents.py`)

### Rules

| Item | Transformation |
|------|----------------|
| `ModelSettings(reasoning=Reasoning(effort="X"))` | `reasoning("X")` |
| `store=True` | Remove (auto-managed by Session) |
| Agent name | Normalize to snake_case |

---

## Flow Definition

### Before (AgentBuilder)

```python
from agents import Runner, RunConfig, trace
from pydantic import BaseModel

class WorkflowInput(BaseModel):
    input_as_text: str

async def run_workflow(workflow_input: WorkflowInput):
    with trace("Agent builder workflow"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {"role": "user", "content": [{"type": "input_text", "text": workflow["input_as_text"]}]}
        ]
        result = await Runner.run(
            my_agent,
            input=[*conversation_history],
            run_config=RunConfig(trace_metadata={"__trace_source__": "agent-builder"}),
        )
        conversation_history.extend(
            [item.to_input_item() for item in result.new_items]
        )
```

### After (Agentic Flow)

```python
from agentic_flow import phase
from agent_specs import chat_agent

async def chat_flow(user_message: str) -> str:
    """Chat flow with session persistence."""
    async with phase("Chat", persist=True):
        return await chat_agent(user_message).stream()
```

### Rules

| AgentBuilder Pattern | Agentic Flow Pattern |
|---------------------|---------------------|
| `with trace(...)` | Remove |
| `WorkflowInput` Pydantic class | Direct `str` argument |
| `workflow_input.model_dump()` | Use argument directly |
| `conversation_history` manual management | Session auto-management |
| `Runner.run(agent, input=[...])` | `await agent(message).stream()` |
| `RunConfig(trace_metadata=...)` | Remove |
| `result.new_items` | Not needed (auto-saved to Session) |

---

## Runner Usage

### Before (AgentBuilder)

```python
result = await Runner.run(
    my_agent,
    input=[*conversation_history],
    run_config=RunConfig(trace_metadata={"__trace_source__": "agent-builder"}),
)
```

### After (Agentic Flow)

```python
# In flow definition
async with phase("Chat", persist=True):
    return await chat_agent(user_message).stream()

# Runner is used at server level, not in flow
runner = Runner(flow=chat_flow, session=session)
```

### Key Differences

| Aspect | AgentBuilder | Agentic Flow |
|--------|--------------|-------------|
| Runner location | Inside flow | Server/CLI |
| Input format | `input=[items...]` | `message: str` |
| Conversation history | Manual management | Session auto-management |
| Tracing | `trace()`, `trace_metadata` | Not needed |

---

## Conversation History

### Before (AgentBuilder)

```python
conversation_history: list[TResponseInputItem] = [
    {"role": "user", "content": [{"type": "input_text", "text": user_input}]}
]
result = await Runner.run(my_agent, input=[*conversation_history])
conversation_history.extend([item.to_input_item() for item in result.new_items])
```

### After (Agentic Flow)

```python
# No manual history management needed
# Session handles this automatically
session = SQLiteSession(session_id=thread.id, db_path="...")
runner = Runner(flow=chat_flow, session=session)
await runner(user_message)  # History stored in Session
```

---

## Model Settings

| AgentBuilder | Agentic Flow |
|--------------|-------------|
| `ModelSettings(reasoning=Reasoning(effort="low"))` | `reasoning("low")` |
| `ModelSettings(reasoning=Reasoning(effort="medium"))` | `reasoning("medium")` |
| `ModelSettings(reasoning=Reasoning(effort="high"))` | `reasoning("high")` |
| `ModelSettings(store=True)` | Remove (uses Session) |
| `ModelSettings(temperature=0.7)` | `ModelSettings(temperature=0.7)` |

---

## Patterns to Delete

The following patterns should be completely removed:

```python
# DELETE: trace
from agents import trace
with trace("..."):
    ...

# DELETE: trace_metadata
run_config=RunConfig(trace_metadata={"__trace_source__": "agent-builder"})

# DELETE: TResponseInputItem
from agents import TResponseInputItem
conversation_history: list[TResponseInputItem] = [...]

# DELETE: Manual history management
conversation_history.extend([item.to_input_item() for item in result.new_items])

# DELETE: WorkflowInput wrapper
class WorkflowInput(BaseModel):
    input_as_text: str
```

---

## Complete Transformation Example

### Input: AgentBuilder

```python
from agents import Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel

my_agent = Agent(
    name="My agent",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
    model_settings=ModelSettings(store=True, reasoning=Reasoning(effort="low", summary="auto")),
)

class WorkflowInput(BaseModel):
    input_as_text: str

async def run_workflow(workflow_input: WorkflowInput):
    with trace("Agent builder workflow"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {"role": "user", "content": [{"type": "input_text", "text": workflow["input_as_text"]}]}
        ]
        my_agent_result_temp = await Runner.run(
            my_agent,
            input=[*conversation_history],
            run_config=RunConfig(trace_metadata={"__trace_source__": "agent-builder"}),
        )
        conversation_history.extend(
            [item.to_input_item() for item in my_agent_result_temp.new_items]
        )
```

### Output: Agentic Flow

**agent_specs.py**
```python
from agentic_flow import Agent, reasoning

chat_agent = Agent(
    name="chat",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
    model_settings=reasoning("low"),
)
```

**flow.py**
```python
from agentic_flow import phase
from agent_specs import chat_agent

async def chat_flow(user_message: str) -> str:
    """Chat flow with session persistence."""
    async with phase("Chat", persist=True):
        return await chat_agent(user_message).stream()
```

---

## Guardrails Transformation

### Intent

Transform AgentBuilder guardrails to openai-guardrails + SDK `@input_guardrail` pattern.

**Important**: Delegate to openai-guardrails-python. Don't reimplement detection logic.

### Before (AgentBuilder)

```python
from guardrails.runtime import load_config_bundle, instantiate_guardrails, run_guardrails

guardrails_config = {
    "guardrails": [
        {"name": "Moderation", "config": {"categories": ["sexual/minors", "hate/threatening", ...]}},
        {"name": "Contains PII", "config": {"block": False, "entities": ["CREDIT_CARD", "US_SSN"]}},
        {"name": "Jailbreak", "config": {"model": "gpt-5.2", "confidence_threshold": 0.7}}
    ]
}

async def run_workflow(workflow_input):
    guardrails_result = await run_and_apply_guardrails(input_text, guardrails_config, ...)
    if guardrails_result["has_tripwire"]:
        return guardrails_result["fail_output"]
    # continue processing...
```

### After (Agentic Flow)

**guardrails_config.json** - Extract configuration to file:
```json
{
  "version": 1,
  "guardrails": [
    {"name": "Jailbreak", "config": {"model": "gpt-5.2", "confidence_threshold": 0.7}},
    {"name": "Moderation", "config": {"categories": ["sexual/minors", "hate/threatening", ...]}},
    {"name": "Contains PII", "config": {"block": false, "entities": ["CREDIT_CARD", "US_SSN"]}}
  ]
}
```

**agent_specs.py** - Single @input_guardrail wrapping openai-guardrails:
```python
from pathlib import Path
from typing import Any

from agents import Agent as SDKAgent, GuardrailFunctionOutput, RunContextWrapper, input_guardrail
from guardrails.runtime import instantiate_guardrails, load_config_bundle, run_guardrails
from openai import AsyncOpenAI

from agentic_flow import Agent, reasoning

CONFIG_PATH = Path(__file__).parent / "guardrails_config.json"


@input_guardrail
async def guardrails_check(
    ctx: RunContextWrapper[Any], agent: SDKAgent, input: str | list
) -> GuardrailFunctionOutput:
    """Run all configured guardrails via openai-guardrails."""
    text = input if isinstance(input, str) else str(input)

    config = load_config_bundle(CONFIG_PATH)
    guardrails = instantiate_guardrails(config)

    results = await run_guardrails(
        ctx={"guardrail_llm": AsyncOpenAI()},
        data=text,
        media_type="text/plain",
        guardrails=guardrails,
        suppress_tripwire=True,
    )

    tripwire = any(getattr(r, "tripwire_triggered", False) for r in results)

    return GuardrailFunctionOutput(
        output_info={"results": [getattr(r, "info", {}) for r in results]},
        tripwire_triggered=tripwire,
    )


chat_agent = Agent(
    name="chat",
    instructions="You are a helpful chat assistant.",
    model="gpt-5.2",
    model_settings=reasoning("low"),
    input_guardrails=[guardrails_check],
)
```

**flow.py** - Catch tripwire exception:
```python
from agents import InputGuardrailTripwireTriggered

from agentic_flow import phase

from agent_specs import chat_agent


async def chat_flow(user_message: str) -> str:
    """Chat flow with openai-guardrails integration."""
    try:
        async with phase("Chat", persist=True):
            return await chat_agent(user_message).stream()
    except InputGuardrailTripwireTriggered:
        return "I cannot process that request due to safety guidelines."
```

### Key Transformation Rules

| AgentBuilder Pattern | Agentic Flow Pattern |
|---------------------|---------------------|
| `guardrails_config = {...}` | `guardrails_config.json` file |
| `run_and_apply_guardrails()` | `@input_guardrail` + `run_guardrails()` |
| `if has_tripwire: return fail_output` | `try/except InputGuardrailTripwireTriggered` |
| Multiple inline guardrail functions | Single `guardrails_check` function |
| Custom detection logic (regex, keywords) | Delegate to openai-guardrails |

### Dependencies

Add to pyproject.toml:
```toml
dependencies = [
    "openai-guardrails>=0.1",
]
```

### Guardrails Placement

| Scenario | Where to Attach Guardrails |
|----------|---------------------------|
| Single agent | `input_guardrails` on that agent |
| Router pattern | `input_guardrails` on classify agent (first to receive input) |
| Multiple entry points | Consider separate guardrail phase or attach to all entry agents |

### Combined Patterns (Guardrails + Router)

When both guardrails and routing are present:

```python
# agent_specs.py
@input_guardrail
async def guardrails_check(ctx, agent, input): ...

classify = Agent(
    name="classify",
    instructions="...",
    input_guardrails=[guardrails_check],  # Attach here
    output_type=ClassifyResult,
)

cook = Agent(name="cook", ...)  # No guardrails needed
meteorologist = Agent(name="meteorologist", ...)  # No guardrails needed
```

```python
# flow.py
async def router_flow(user_message: str) -> str:
    try:
        async with phase("Classify"):
            classification = await classify(user_message).stream()

        if classification.category == "cook":
            async with phase("Response", persist=True):
                return await cook(user_message).stream()
        ...
    except InputGuardrailTripwireTriggered:
        return "I cannot process that request due to safety guidelines."
```

### Why This Works

- **Delegate to openai-guardrails**: Production-quality detection logic
- **Configuration-driven**: Change behavior via JSON, not code
- **Single guardrail function**: No redundant code
- **SDK manages lifecycle**: Execution, tripwire detection
- **Clean exception handling**: Flow catches and responds appropriately

---

## Verification Checklist

After transformation, verify:

### Basic Transformation
- [ ] `from agents import` → `from agentic_flow import`
- [ ] `trace()` is removed
- [ ] `RunConfig` is removed
- [ ] No manual `conversation_history` management
- [ ] Response wrapped in `phase(persist=True)`
- [ ] Agent names in snake_case
- [ ] Uses `reasoning("X")` format
- [ ] File name is `agent_specs.py` (NOT `agents.py`)

### Guardrails (if present in source)
- [ ] `guardrails_config` → `guardrails_config.json` file
- [ ] `openai-guardrails>=0.1` in pyproject.toml dependencies
- [ ] Single `@input_guardrail` function using `run_guardrails()`
- [ ] Agent has `input_guardrails=[guardrails_check]` parameter
- [ ] flow.py catches `InputGuardrailTripwireTriggered`
- [ ] No custom detection logic (regex, keywords) - delegate to openai-guardrails

### Router Pattern (if present in source)
- [ ] Classify phase without `persist=True`
- [ ] Response phase with `persist=True`
- [ ] Clean if/elif routing (no nested conditionals)
- [ ] Guardrails attached to classify agent (first entry point)
