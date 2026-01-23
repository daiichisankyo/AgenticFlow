"""Agentic Flow Quickstart - Basic example."""

from agents import SQLiteSession

import agentic_flow as af

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
# result = await runner("What is Python?")
