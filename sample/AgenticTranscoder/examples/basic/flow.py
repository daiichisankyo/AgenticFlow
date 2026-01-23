"""Single-phase chat flow."""

from agentic_flow import phase

from agent_specs import chat_agent


async def chat_flow(user_message: str) -> str:
    async with phase("Chat", persist=True):
        return await chat_agent(user_message).stream()
