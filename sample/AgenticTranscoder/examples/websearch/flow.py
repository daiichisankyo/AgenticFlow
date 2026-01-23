"""Single-phase websearch flow."""

from agentic_flow import phase

from agent_specs import websearch


async def chat_flow(user_message: str) -> str:
    async with phase("WebSearch", persist=True):
        return await websearch(user_message).stream()
