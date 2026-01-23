"""AgentBuilder source code for Basic Chat Agent.

This is the BEFORE (input) format that Transcoder transforms.
See flow.py and builder_agents.py for the AFTER (output) format.

Pattern: single-agent-chat
- Single Agent definition
- No conditional routing
- Simple request-response flow
"""

from pydantic import BaseModel

from agents import Agent, ModelSettings, Runner, RunConfig, TResponseInputItem, trace
from openai.types.shared.reasoning import Reasoning


chat_agent = Agent(
    name="Chat",
    instructions="""You are a helpful assistant.

- Answer questions clearly and concisely.
- Be friendly and professional.
- If you don't know something, say so honestly.""",
    model="gpt-5.2",
    model_settings=ModelSettings(
        store=True,
        reasoning=Reasoning(effort="low", summary="auto"),
    ),
)


class WorkflowInput(BaseModel):
    input_as_text: str


async def run_workflow(workflow_input: WorkflowInput):
    with trace("Chat workflow"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": workflow["input_as_text"]}],
            }
        ]

        result = await Runner.run(
            chat_agent,
            input=[*conversation_history],
            run_config=RunConfig(
                trace_metadata={
                    "__trace_source__": "agent-builder",
                }
            ),
        )

        conversation_history.extend(
            [item.to_input_item() for item in result.new_items]
        )

        return {"output_text": result.final_output_as(str)}
