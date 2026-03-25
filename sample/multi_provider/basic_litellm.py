"""AF + LiteLLM: Use Claude or Gemini in an AF flow.

Prerequisites:
    pip install "litellm>=1.82.6,!=1.82.7,!=1.82.8"
    export ANTHROPIC_API_KEY="sk-ant-..."

Security:
    litellm 1.82.7/1.82.8 were compromised on PyPI (credential exfiltration).
    Always pin to a verified version.

Usage:
    python sample/multi_provider/basic_litellm.py
"""

import asyncio
import agentic_flow as af

claude = af.Agent(
    name="claude",
    instructions="You are Claude, an AI assistant by Anthropic.",
    model="litellm/anthropic/claude-sonnet-4-20250514",
)


async def main() -> None:
    async def flow(query: str) -> str:
        async with af.phase("Answer", persist=True):
            return await claude(query).stream()

    runner = af.Runner(flow=flow)
    result = await runner("What makes you different from GPT?")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
