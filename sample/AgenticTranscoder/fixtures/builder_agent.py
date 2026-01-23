from agents import Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel

my_agent = Agent(
    name="My agent",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
    model_settings=ModelSettings(store=True, reasoning=Reasoning(effort="low", summary="auto")),
)


class WorkflowInput(BaseModel):
    input_as_text: str


# Main code entrypoint
async def run_workflow(workflow_input: WorkflowInput):
    with trace("Agent builder workflow"):
        workflow = workflow_input.model_dump()
        conversation_history: list[TResponseInputItem] = [
            {"role": "user", "content": [{"type": "input_text", "text": workflow["input_as_text"]}]}
        ]
        my_agent_result_temp = await Runner.run(
            my_agent,
            input=[*conversation_history],
            run_config=RunConfig(trace_metadata={"__trace_source__": "agent-builder"}),
        )

        conversation_history.extend(
            [item.to_input_item() for item in my_agent_result_temp.new_items]
        )
