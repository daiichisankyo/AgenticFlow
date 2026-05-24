"""AF: Switch models at runtime with RunConfig.

Usage:
    python sample/multi_provider/runtime_model_switch.py
"""

import asyncio

import agentic_flow as af
from agents import RunConfig

agent = af.Agent(
    name="flexible",
    instructions="Analyze the data.",
    model="gpt-5.5",
)


async def main() -> None:
    async def flow(query: str) -> str:
        async with af.phase("Quick Check"):
            preview = await agent(query).run_config(
                RunConfig(model="gpt-5.5")
            ).stream()

        async with af.phase("Deep Analysis", persist=True):
            return await agent(f"Deep analysis of: {preview}").stream()

    runner = af.Runner(flow=flow)
    result = await runner("Summarize the risks in this dataset.")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
