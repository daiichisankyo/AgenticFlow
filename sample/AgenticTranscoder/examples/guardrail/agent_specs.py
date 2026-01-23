"""Chat agent with openai-guardrails integration."""

from pathlib import Path
from typing import Any

from agentic_flow import Agent, reasoning
from agents import (
    Agent as SDKAgent,
)
from agents import (
    GuardrailFunctionOutput,
    RunContextWrapper,
    input_guardrail,
)
from openai import AsyncOpenAI

from guardrails.runtime import (
    instantiate_guardrails,
    load_config_bundle,
    run_guardrails,
)

CONFIG_PATH = Path(__file__).parent / "guardrails_config.json"


@input_guardrail
async def guardrails_check(
    ctx: RunContextWrapper[Any], agent: SDKAgent, input: str | list
) -> GuardrailFunctionOutput:
    """Run configured guardrails and trigger tripwire if any fail."""
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
    instructions="""You are a helpful chat assistant.

Your responses should be helpful, safe, and concise.""",
    model="gpt-5.2",
    model_settings=reasoning("low"),
    input_guardrails=[guardrails_check],
)
