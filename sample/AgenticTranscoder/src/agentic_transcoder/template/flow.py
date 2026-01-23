"""Flow definition for Chat Agent.

Design:
- Single phase with persist=True for chat history
- Simple flow that wraps the agent call
- Runner handles Session injection
"""

from agent_specs import chat_agent
from agentic_flow import phase


async def chat_flow(user_message: str) -> str:
    """Chat flow with session persistence.

    Uses phase(persist=True) to write response to Session,
    enabling multi-turn conversation via ChatKit.
    """
    async with phase("Chat", persist=True):
        return await chat_agent(user_message).stream()
