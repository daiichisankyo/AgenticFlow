"""Pure Agents SDK - Complex multi-agent with ChatKit streaming."""

import asyncio
from typing import Any

from agents import Agent, ModelSettings, Runner
from agents.extensions.chatkit import (
    AgentContext,
    close_workflow,
    emit_phase_label,
    stream_agent_response,
)
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from openai.types.shared.reasoning import Reasoning

app = FastAPI()


def create_agent(name: str, instructions: str) -> Agent:
    return Agent(
        name=name,
        instructions=instructions,
        model="gpt-5.2",
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="medium", summary="auto"),
        ),
    )


classifier = create_agent("classifier", "Classify as SIMPLE or COMPLEX.")
researcher = create_agent("researcher", "Research the topic.")
reviewer = create_agent("reviewer", "Review. Reply APPROVED or REJECTED.")
refiner = create_agent("refiner", "Refine based on feedback.")
responder = create_agent("responder", "Give final response.")


def to_messages(text: str) -> list[dict[str, Any]]:
    return [{"role": "user", "content": [{"type": "input_text", "text": text}]}]


@app.post("/chatkit")
async def chatkit_endpoint(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    user_input = messages[-1]["content"][0]["text"]

    agent_context = AgentContext()
    event_queue: asyncio.Queue = asyncio.Queue()

    async def flow_logic():
        try:
            # Phase 1: Classification
            emit_phase_label(agent_context, "Classification")
            result = Runner.run_streamed(classifier, to_messages(user_input), context=agent_context)
            async for event in stream_agent_response(agent_context, result):
                await event_queue.put(event)
            classification = result.final_output
            await close_workflow(agent_context)

            # Phase 2: Research (conditional)
            if "COMPLEX" in classification.upper():
                emit_phase_label(agent_context, "Research")
                result = Runner.run_streamed(
                    researcher, to_messages(user_input), context=agent_context
                )
                async for event in stream_agent_response(agent_context, result):
                    await event_queue.put(event)
                draft = result.final_output
                await close_workflow(agent_context)
            else:
                draft = user_input

            # Phase 3: Review loop
            for attempt in range(3):
                emit_phase_label(agent_context, f"Review (attempt {attempt + 1})")
                result = Runner.run_streamed(
                    reviewer, to_messages(f"Review:\n{draft}"), context=agent_context
                )
                async for event in stream_agent_response(agent_context, result):
                    await event_queue.put(event)
                review = result.final_output
                await close_workflow(agent_context)

                if "APPROVED" in review.upper():
                    break

                emit_phase_label(agent_context, f"Refinement (attempt {attempt + 1})")
                result = Runner.run_streamed(
                    refiner,
                    to_messages(f"Draft:\n{draft}\n\nFeedback:\n{review}"),
                    context=agent_context,
                )
                async for event in stream_agent_response(agent_context, result):
                    await event_queue.put(event)
                draft = result.final_output
                await close_workflow(agent_context)

            # Phase 4: Final response
            emit_phase_label(agent_context, "Final Response")
            result = Runner.run_streamed(
                responder, to_messages(f"Based on:\n{draft}"), context=agent_context
            )
            async for event in stream_agent_response(agent_context, result):
                await event_queue.put(event)
            await close_workflow(agent_context)

        except Exception:
            try:
                await close_workflow(agent_context)
            except Exception:
                pass
            raise
        finally:
            await event_queue.put(None)

    async def event_generator():
        asyncio.create_task(flow_logic())
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
