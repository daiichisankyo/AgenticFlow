"""Classify and route to specialist agents."""

from agentic_flow import phase

from agent_specs import ClassifyResult, classify, cook, meteorologist


async def router_flow(user_message: str) -> str:
    async with phase("Classify"):
        classification: ClassifyResult = await classify(user_message).stream()

    if classification.category == "cook":
        async with phase("Response", persist=True):
            return await cook(user_message).stream()

    if classification.category == "meteorologist":
        async with phase("Response", persist=True):
            return await meteorologist(user_message).stream()

    return classification.model_dump_json()
