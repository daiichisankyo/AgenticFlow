"""Agentic Flow - Same complex flow, clean code."""

import agentic_flow as af

classifier = af.Agent(
    name="classifier",
    instructions="Classify as SIMPLE or COMPLEX.",
    model="gpt-5.2",
    model_settings=af.reasoning("medium"),
)
researcher = af.Agent(name="researcher", instructions="Research.", model="gpt-5.2")
reviewer = af.Agent(name="reviewer", instructions="Review. APPROVED or REJECTED.", model="gpt-5.2")
refiner = af.Agent(name="refiner", instructions="Refine based on feedback.", model="gpt-5.2")
responder = af.Agent(name="responder", instructions="Give final response.", model="gpt-5.2")


async def my_flow(user_message: str) -> str:
    # Internal classification - not saved to session
    async with af.phase("Classification"):
        classification = await classifier(user_message).stream()

    if "COMPLEX" in classification.upper():
        # Internal research - not saved to session
        async with af.phase("Research"):
            draft = await researcher(user_message).stream()
    else:
        draft = user_message

    for attempt in range(3):
        # Internal review - not saved to session
        async with af.phase(f"Review (attempt {attempt + 1})"):
            review = await reviewer(f"Review:\n{draft}").stream()

        if "APPROVED" in review.upper():
            break

        # Internal refinement - not saved to session
        async with af.phase(f"Refinement (attempt {attempt + 1})"):
            draft = await refiner(f"Draft:\n{draft}\n\nFeedback:\n{review}").stream()

    # persist=True saves the final response to session
    async with af.phase("Final Response", persist=True):
        return await responder(f"Based on:\n{draft}").stream()
