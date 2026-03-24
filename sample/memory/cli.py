"""CLI demo for ChatGPT-style memory system.

Run:
    cd sample
    uv run python -m memory.cli

Features:
- Persistent user memory (facts)
- Conversation summaries
- 6-layer context injection
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent.parent / ".env.local")

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from agentic_flow import Runner
from agents import SQLiteSession
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from .flow import chat_with_memory
from .summaries import ConversationStore
from .types import SessionMetadata
from .user_memory import UserMemory

console = Console()
DATA_DIR = pathlib.Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def create_handler():
    """Create streaming handler that separates reasoning from response."""
    state = {"in_reasoning": False, "reasoning_shown": False}

    def handler(event):
        event_type = getattr(event, "type", "")

        if hasattr(event, "data") and hasattr(event.data, "delta"):
            delta = event.data.delta

            if "reasoning" in event_type:
                if not state["in_reasoning"]:
                    console.print("[dim]thinking...[/dim]", end="")
                    state["in_reasoning"] = True
            else:
                if state["in_reasoning"] and not state["reasoning_shown"]:
                    console.print()
                    state["in_reasoning"] = False
                    state["reasoning_shown"] = True
                console.print(delta, end="", highlight=False)

    def reset():
        state["in_reasoning"] = False
        state["reasoning_shown"] = False

    handler.reset = reset
    return handler


async def main():
    console.print(Rule("ChatGPT-style Memory Demo"))
    console.print()
    console.print("[dim]6-layer context: metadata, memory, summaries, session, message[/dim]")
    console.print("[dim]/memory = show stored data, Ctrl+C = exit[/dim]")
    console.print()

    metadata = SessionMetadata(
        timezone="Asia/Tokyo",
        device="desktop",
        os="macOS",
        browser="Terminal",
        screen_size="1920x1080",
        dark_mode=True,
        account_age_weeks=12,
        active_days_last_7=5,
        avg_conversation_depth=8.5,
        subscription="pro",
    )

    user_memory = UserMemory(
        max_facts=33,
        storage_path=str(DATA_DIR / "user_memory.json"),
    )

    conversation_store = ConversationStore(
        max_summaries=15,
        storage_path=str(DATA_DIR / "conversation_summaries.json"),
    )

    user_messages: list[str] = []
    handler = create_handler()

    async def memory_flow(user_message: str) -> str:
        return await chat_with_memory(
            user_message,
            metadata,
            user_memory,
            conversation_store,
        )

    runner = Runner(
        flow=memory_flow,
        session=SQLiteSession(
            session_id="memory_cli",
            db_path=str(DATA_DIR / "session.db"),
        ),
        handler=handler,
    )

    if user_memory.facts:
        console.print(f"[dim]Loaded {len(user_memory.facts)} facts[/dim]")

    if conversation_store.summaries:
        console.print(f"[dim]Loaded {len(conversation_store.summaries)} summaries[/dim]")

    while True:
        try:
            console.print()
            user_input = console.input("[bold]You:[/bold] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input.lower() == "/memory":
            console.print(
                Panel(
                    user_memory.to_prompt() or "(empty)",
                    title="User Memory",
                    border_style="dim",
                )
            )
            console.print(
                Panel(
                    conversation_store.to_prompt() or "(empty)",
                    title="Past Conversations",
                    border_style="dim",
                )
            )
            continue

        user_messages.append(user_input)
        handler.reset()

        console.print("[bold]Assistant:[/bold] ", end="")
        try:
            await runner(user_input)
            console.print()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    if user_messages:
        console.print("[dim]Saving summary...[/dim]")
        await conversation_store.summarize_and_store(user_messages)

    console.print("[dim]Goodbye![/dim]")


if __name__ == "__main__":
    asyncio.run(main())
