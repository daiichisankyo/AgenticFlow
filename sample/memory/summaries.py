"""Conversation summaries - Past conversation digests.

Stores lightweight summaries (max 15) in ChatGPT's format:
<timestamp>: <title>
|||| user message snippet ||||

Only user messages are summarized, not assistant responses.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from agentic_flow import Agent

from .types import ConversationSummary

MODEL = os.getenv("MODEL_NAME", "gpt-5.2")

summarizer = Agent(
    name="summarizer",
    instructions="""Summarize the conversation from user messages.

Create:
1. title: A short title (5 words max) capturing the main topic
2. user_snippets: Key user message snippets (2-4 items, brief phrases)

Focus on:
- User's main intent
- Topics discussed
- Key requests or statements

Do NOT include:
- Assistant responses
- Greetings or pleasantries
- Full sentences (use brief phrases)""",
    model=MODEL,
    output_type=ConversationSummary,
)


class ConversationStore:
    """Manages conversation summaries (max 15, like ChatGPT)."""

    def __init__(self, max_summaries: int = 15, storage_path: str | None = None):
        self.summaries: list[ConversationSummary] = []
        self.max_summaries = max_summaries
        self.storage_path = storage_path
        if storage_path:
            self.load()

    async def summarize_and_store(self, user_messages: list[str]) -> ConversationSummary | None:
        """Generate summary for completed conversation.

        Uses isolated() + silent() to avoid polluting context.
        """
        if not user_messages:
            return None

        messages_text = "\n".join(f"- {m}" for m in user_messages)

        summary: ConversationSummary = (
            await summarizer(f"User messages from this conversation:\n{messages_text}")
            .isolated()
            .silent()
        )

        summary.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        self.add_summary(summary)
        return summary

    def add_summary(self, summary: ConversationSummary) -> None:
        """Add summary, respecting max limit (FIFO)."""
        self.summaries.append(summary)
        if len(self.summaries) > self.max_summaries:
            self.summaries.pop(0)
        if self.storage_path:
            self.save()

    def to_prompt(self) -> str:
        """Format summaries for prompt injection (ChatGPT style)."""
        if not self.summaries:
            return ""
        lines = []
        for s in self.summaries:
            lines.append(f"{s.timestamp}: {s.title}")
            for snippet in s.user_snippets:
                lines.append(f"|||| {snippet} ||||")
        return "\n".join(lines)

    def load(self) -> None:
        """Load summaries from JSON file."""
        if not self.storage_path:
            return
        path = pathlib.Path(self.storage_path)
        if path.exists():
            data = json.loads(path.read_text())
            self.summaries = [ConversationSummary(**s) for s in data.get("summaries", [])]

    def save(self) -> None:
        """Save summaries to JSON file."""
        if not self.storage_path:
            return
        path = pathlib.Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"summaries": [s.model_dump() for s in self.summaries]}, indent=2)
        )
