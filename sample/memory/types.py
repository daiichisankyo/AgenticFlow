"""Data types for memory system."""

from __future__ import annotations

from pydantic import BaseModel


class MemoryDecision(BaseModel):
    """Decision on whether to save a fact to memory."""

    should_save: bool
    fact: str | None = None
    reason: str


class ConversationSummary(BaseModel):
    """Conversation summary (user messages only).

    Format follows ChatGPT's pattern:
    <timestamp>: <title>
    |||| user snippet ||||
    """

    timestamp: str
    title: str
    user_snippets: list[str]


class SessionMetadata(BaseModel):
    """Ephemeral session metadata.

    Not persisted. Injected at runtime.
    Based on ChatGPT's session metadata layer.
    """

    # Device environment
    timezone: str = "Asia/Tokyo"
    device: str = "desktop"
    browser: str = "unknown"
    os: str = "unknown"
    screen_size: str = "unknown"
    dark_mode: bool = False

    # User activity patterns
    account_age_weeks: int = 0
    active_days_last_7: int = 0
    avg_conversation_depth: float = 0.0

    # Subscription/model info
    subscription: str = "free"
    preferred_model: str = "gpt-5.2"
