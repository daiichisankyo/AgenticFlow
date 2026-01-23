"""Agent definitions for Chat Agent.

Transformed from AgentBuilder:
- Agent with reasoning support
- model="gpt-5.2" as standard
"""

from agentic_flow import Agent, reasoning

chat_agent = Agent(
    name="chat",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
    model_settings=reasoning("low"),
)
