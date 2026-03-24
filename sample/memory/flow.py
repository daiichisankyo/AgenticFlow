"""Memory-enabled chat flow.

Implements ChatGPT's 6-layer context injection:
[0] System Instructions     - Agent.instructions
[1] Developer Instructions  - Agent.instructions
[2] Session Metadata        - build_context()
[3] User Memory             - build_context()
[4] Conversation Summaries  - build_context()
[5] Current Session         - Session/PhaseSession
[6] Latest Message          - user_message
"""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from agentic_flow import Agent, phase, reasoning

from .summaries import ConversationStore
from .types import SessionMetadata
from .user_memory import UserMemory

MODEL = os.getenv("MODEL_NAME", "gpt-5.2")

MAX_SESSION_MESSAGES = 20


def create_assistant(context: str) -> Agent:
    """Create assistant with injected context in instructions."""
    return Agent(
        name="assistant",
        instructions=f"""You are a helpful assistant with memory capabilities.

{context}

Use this context naturally to personalize responses.
Reference known facts when relevant, but don't force them.
If user asks what you know about them, summarize their memory.
Always remember what the user said in this conversation.""",
        model=MODEL,
        model_settings=reasoning("medium"),
    )


def build_context(
    metadata: SessionMetadata,
    user_memory: UserMemory,
    conversation_store: ConversationStore,
) -> str:
    """Build layers [2]-[4] of the context."""
    sections = []

    sections.append(
        f"""<session_metadata>
device: {metadata.device} ({metadata.os}, {metadata.browser})
screen: {metadata.screen_size}
timezone: {metadata.timezone}
dark_mode: {metadata.dark_mode}
account_age: {metadata.account_age_weeks} weeks
activity: {metadata.active_days_last_7}/7 days active
avg_depth: {metadata.avg_conversation_depth:.1f} messages
subscription: {metadata.subscription}
</session_metadata>"""
    )

    memory_text = user_memory.to_prompt()
    if memory_text:
        sections.append(
            f"""<user_memory>
{memory_text}
</user_memory>"""
        )

    summaries_text = conversation_store.to_prompt()
    if summaries_text:
        sections.append(
            f"""<past_conversations>
{summaries_text}
</past_conversations>"""
        )

    return "\n\n".join(sections)


async def chat_with_memory(
    user_message: str,
    metadata: SessionMetadata,
    user_memory: UserMemory,
    conversation_store: ConversationStore,
) -> str:
    """Chat with ChatGPT-style 6-layer memory.

    1. Extract facts from user message (silent, isolated)
    2. Build layered context [2]-[4] into instructions
    3. Generate response (Session provides [5] current conversation)

    Uses phase(persist=True) to write final response to Session.
    """
    await user_memory.process(user_message)

    context = build_context(metadata, user_memory, conversation_store)

    assistant = create_assistant(context)

    async with phase("Response", persist=True):
        return await assistant(user_message).stream()
