"""AF: Mix OpenAI and Anthropic in a single flow.

Prerequisites:
    pip install litellm
    export ANTHROPIC_API_KEY="sk-ant-..."

Usage:
    python sample/multi_provider/mixed_models_flow.py
"""

import asyncio
import agentic_flow as af

openai_agent = af.Agent(
    name="openai",
    instructions="You are a helpful assistant.",
    model="gpt-5.2",
)

claude_agent = af.Agent(
    name="claude",
    instructions="You are a helpful assistant.",
    model="litellm/anthropic/claude-sonnet-4-20250514",
)


async def main() -> None:
    async def flow(query: str) -> str:
        async with af.phase("Research"):
            research = await claude_agent(query).stream()

        async with af.phase("Summarize", persist=True):
            return await openai_agent(f"Summarize: {research}").stream()

    runner = af.Runner(flow=flow)
    result = await runner("Explain quantum computing")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
