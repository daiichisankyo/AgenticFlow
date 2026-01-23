"""Chat flow with guardrail tripwire handling."""

from agent_specs import chat_agent
from agentic_flow import phase
from agents import InputGuardrailTripwireTriggered


async def chat_flow(user_message: str) -> str:
    try:
        async with phase("Chat", persist=True):
            return await chat_agent(user_message).stream()
    except InputGuardrailTripwireTriggered:
        return "I cannot process that request due to safety guidelines."
