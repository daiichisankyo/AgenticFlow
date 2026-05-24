"""Agent definitions for Chat Agent.

Transformed from AgentBuilder:
- Agent with reasoning support
- model="gpt-5.5" as standard
"""

from agentic_flow import Agent, reasoning

chat_agent = Agent(
    name="chat",
    instructions="You are a helpful assistant.",
    model="gpt-5.5",
    model_settings=reasoning("low"),
)
