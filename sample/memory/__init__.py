"""ChatGPT-style memory system.

4-layer context injection:
[2] Session Metadata - ephemeral (device, timezone)
[3] User Memory - persistent facts (max 33)
[4] Conversation Summaries - persistent (max 15, user messages only)
[5-6] Current Session - managed by Session/PhaseSession
"""

from .flow import chat_with_memory
from .summaries import ConversationStore
from .types import ConversationSummary, MemoryDecision, SessionMetadata
from .user_memory import UserMemory

__all__ = [
    "chat_with_memory",
    "UserMemory",
    "ConversationStore",
    "SessionMetadata",
    "MemoryDecision",
    "ConversationSummary",
]
