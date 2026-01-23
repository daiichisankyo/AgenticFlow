"""Agentic Flow Quickstart.

See how Agentic Flow simplifies multi-agent workflows.

Usage:
    cd sample
    uv run python quickstart.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env.local")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_flow import Agent, Runner, phase
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


assistant = Agent(
    name="assistant",
    instructions="You are a helpful assistant. Reply concisely in 1-2 sentences.",
    model="gpt-5.2",
)


class Review(BaseModel):
    approved: bool
    feedback: str


reviewer = Agent(
    name="reviewer",
    instructions="Review the explanation. Return approved=true if good, else feedback.",
    model="gpt-5.2",
    output_type=Review,
)


class Analysis(BaseModel):
    sentiment: str
    confidence: float
    keywords: list[str]


analyzer = Agent(
    name="analyzer",
    instructions="Analyze the sentiment of the given text.",
    model="gpt-5.2",
    output_type=Analysis,
)


def section(title: str) -> None:
    console.print(f"\n[bold cyan]── {title} ──[/bold cyan]\n")


def code(source: str) -> None:
    console.print(Syntax(source, "python", theme="monokai"))


def result(text: str) -> None:
    console.print(Panel(text, border_style="dim"))


async def demo_flow_and_runner() -> None:
    """1. Flow & Runner - The core value."""
    section("1. Flow & Runner")

    console.print("Flow is a pure async function. Runner executes it.\n")

    code(
        """\
async def explain_and_review(topic: str) -> str:
    async with phase("Explaining"):
        explanation = await assistant(f"Explain {topic}").stream()

    async with phase("Reviewing"):
        review: Review = await reviewer(f"Review: {explanation}")

    if review.approved:
        return explanation

    async with phase("Refining"):
        return await assistant(f"Improve: {review.feedback}").stream()

runner = Runner(flow=explain_and_review)
result = await runner("async/await")"""
    )

    async def explain_and_review(topic: str) -> str:
        async with phase("Explaining"):
            explanation = await assistant(f"Explain {topic} simply.").stream()

        async with phase("Reviewing"):
            review_result: Review = await reviewer(f"Review this:\n{explanation}")

        if review_result.approved:
            return explanation

        async with phase("Refining"):
            return await assistant(
                f"Improve based on feedback: {review_result.feedback}\n\n{explanation}"
            ).stream()

    console.print("\n[dim]Running...[/dim]")
    runner = Runner(flow=explain_and_review)
    output = await runner("async/await in Python")
    result(output)


async def demo_declaration_vs_execution() -> None:
    """2. Declaration vs Execution."""
    section("2. Declaration vs Execution")

    console.print("agent(prompt) returns ExecutionSpec. await executes it.\n")

    code(
        """\
spec = assistant("What is Python?")  # Not executed yet
result = await spec                   # Executed here"""
    )

    console.print("\n[dim]Running...[/dim]")
    spec = assistant("What is Python? One sentence.")
    console.print(f"  spec type: {type(spec).__name__}")
    output = await spec
    result(output)


async def demo_modifiers() -> None:
    """3. Modifiers."""
    section("3. Modifiers: .stream() / .isolated() / .silent()")

    console.print("Modifiers change HOW execution happens.\n")

    code(
        """\
await assistant("...").stream()    # Streaming
await assistant("...").isolated()  # No Session read/write
await assistant("...").silent()    # No UI output"""
    )

    console.print("\n[dim]Streaming demo...[/dim]")

    def streaming_handler(event) -> None:
        if hasattr(event, "data") and hasattr(event.data, "delta"):
            console.print(event.data.delta, end="")

    async def streaming_flow(msg: str) -> str:
        async with phase("Streaming"):
            return await assistant(msg).stream()

    runner = Runner(flow=streaming_flow, handler=streaming_handler)
    await runner("What is async/await? One sentence.")

    console.print()


async def demo_typed_output() -> None:
    """4. Typed Output."""
    section("4. Typed Output")

    console.print("output_type returns Pydantic models.\n")

    code(
        """\
class Analysis(BaseModel):
    sentiment: str
    confidence: float
    keywords: list[str]

analyzer = Agent(..., output_type=Analysis)
result: Analysis = await analyzer("I love this!")"""
    )

    console.print("\n[dim]Running...[/dim]")
    output: Analysis = await analyzer("I absolutely love this new feature!")
    result(
        f"sentiment: {output.sentiment}\n"
        f"confidence: {output.confidence}\n"
        f"keywords: {', '.join(output.keywords)}"
    )


async def main() -> None:
    console.print("\n[bold]Agentic Flow Quickstart[/bold]")

    await demo_flow_and_runner()
    await demo_declaration_vs_execution()
    await demo_modifiers()
    await demo_typed_output()

    console.print("\n[dim]Done.[/dim]\n")


if __name__ == "__main__":
    asyncio.run(main())
