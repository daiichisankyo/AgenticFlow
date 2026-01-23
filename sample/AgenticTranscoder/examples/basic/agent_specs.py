"""Chat agent definition."""

from agentic_flow import Agent, reasoning

chat_agent = Agent(
    name="chat",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
    model_settings=reasoning("low"),
)
