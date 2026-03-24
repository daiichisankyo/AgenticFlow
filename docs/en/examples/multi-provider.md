# Multi-Provider Examples

This page collects examples that demonstrate SDK multi-provider usage through AF.

## Quick Start (LiteLLM Prefix)

```python
import agentic_flow as af

agent = af.Agent(
    name="claude",
    instructions="You are a helpful assistant.",
    model="litellm/anthropic/claude-sonnet-4-20250514",
)
```

The SDK resolves the prefixed model via its default `MultiProvider`. AF passes the model string through unchanged.

## Mix Providers in One Flow

```python
import agentic_flow as af

openai_agent = af.Agent(
    name="openai",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
)

claude_agent = af.Agent(
    name="claude",
    instructions="You are a helpful assistant.",
    model="litellm/anthropic/claude-sonnet-4-20250514",
)

async def flow(query: str) -> str:
    async with af.phase("Research"):
        research = await claude_agent(query).stream()

    async with af.phase("Summarize", persist=True):
        return await openai_agent(f"Summarize: {research}").stream()
```

## Runtime Model Switch

```python
from agents import RunConfig

result = await agent("prompt").run_config(
    RunConfig(model="gpt-5.2")
).stream()
```

## Custom Provider (Skeleton)

```python
from agents import RunConfig
from agents.models.interface import Model, ModelProvider

class MyCompanyModel(Model):
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name

    async def get_response(self, system_instructions, input, model_settings,
                           tools, output_schema, handoffs, tracing, **kwargs):
        ...

    def stream_response(self, system_instructions, input, model_settings,
                        tools, output_schema, handoffs, tracing, **kwargs):
        ...

class MyCompanyProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        return MyCompanyModel(model_name)

config = RunConfig(model_provider=MyCompanyProvider())
result = await agent("prompt").run_config(config)
```

## Repository Samples

Run these from the repo root:

- `sample/multi_provider/basic_litellm.py`
- `sample/multi_provider/mixed_models_flow.py`
- `sample/multi_provider/runtime_model_switch.py`
- `sample/multi_provider/custom_provider.py`
