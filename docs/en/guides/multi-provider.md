# Multi-Provider

AF supports multiple LLM providers through the OpenAI Agents SDK. AF does not add a separate provider abstraction; it passes SDK arguments through unchanged.

## Quick Start (Prefix Routing)

Use a prefixed model name to route to another provider via LiteLLM.

```python
import agentic_flow as af

claude = af.Agent(
    name="claude",
    instructions="You are a helpful assistant.",
    model="litellm/anthropic/claude-sonnet-4-20250514",
)
```

The SDK resolves the model via its default `MultiProvider`. No AF-specific configuration is required.

## How Prefix Routing Works

The SDK uses `ModelProvider` to resolve a model name to a `Model` implementation. By default, `RunConfig.model_provider` is a `MultiProvider`, which interprets prefixes such as:

- `gpt-5.2` (OpenAI default)
- `openai/gpt-5.2` (OpenAI explicit)
- `litellm/anthropic/claude-sonnet-4-20250514` (Anthropic via LiteLLM)

AF simply passes the `model` string through to the SDK.

## Runtime Overrides With RunConfig

Override the model at execution time without rebuilding the agent:

```python
from agents import RunConfig

result = await agent("prompt").run_config(
    RunConfig(model="gpt-5.2")
).stream()
```

You can also supply a custom `model_provider` to `RunConfig`.

## Custom Provider

Implement the SDK `ModelProvider` interface and pass it via `RunConfig`:

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

## Environment Variables

When using LiteLLM, provider API keys are read from environment variables. Refer to the LiteLLM documentation for provider-specific names and configuration.

## Troubleshooting

- `Unknown model prefix`: Ensure the model name starts with a supported prefix (for LiteLLM use `litellm/`).
- `ModuleNotFoundError: litellm`: Install LiteLLM with `pip install litellm`.
- `Authentication failed`: Check provider API keys in your environment.
