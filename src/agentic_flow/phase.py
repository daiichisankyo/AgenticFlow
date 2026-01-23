"""phase() - Scope + UI label.

Design: async with phase("Label"): ...

Handler is injected by Runner, not by phase (UI dependency isolation).

ChatKit Integration:
    When running with ChatKitServer + run_with_chatkit_context(),
    phase() automatically creates workflow boundaries by:
    1. Calling emit_phase_label() at start - saves message to store
    2. Calling close_workflow() at end - ends the workflow
    This ensures each phase gets its own reasoning display.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from agents.items import TResponseInputItem
from agents.memory.session import SessionABC

from .agent import (
    current_handler,
    current_phase_session,
    current_session,
)
from .chatkit import current_chatkit_context
from .types import PhaseEnded, PhaseStarted

if TYPE_CHECKING:
    pass

# Indicates whether execution is inside a phase (regardless of share_context)
current_in_phase: ContextVar[bool] = ContextVar("current_in_phase", default=False)

# Cached Session history for share_context=False phases
# This is set at phase start and cleared at phase end
current_phase_session_history: ContextVar[list | None] = ContextVar(
    "current_phase_session_history", default=None
)


class PhaseSession(SessionABC):
    """SessionABC-compliant phase session.

    PhaseSession is a temporary thinking space within a Flow.
    It is destroyed when the phase ends.

    Two-layer structure:
        - inherited_history: Snapshot from parent Session (read-only)
        - items: Phase-local conversation (managed by SDK)

    Session Inheritance:
        PhaseSession inherits Session history at creation time.
        get_items() returns: inherited_history + items
        This allows Agents in phase to see past conversation while
        writing only to PhaseSession (not parent Session).

    Example:
        async with phase("Research", share_context=True) as p:
            result1 = await agent1(query).stream()
            result2 = await agent2(query).stream()  # Sees result1's context
            p.summary = result2
    """

    def __init__(self, label: str, inherited_history: list[TResponseInputItem] | None = None):
        self.session_id = f"phase_{label}_{id(self)}"
        self.label = label
        self.items: list[TResponseInputItem] = []
        self.data: dict[str, Any] = {}
        self.inherited_history: list[TResponseInputItem] = inherited_history or []

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        """Return inherited + phase-local items.

        This provides full conversation context to the LLM,
        including history inherited from parent Session.
        """
        full = list(self.inherited_history) + list(self.items)
        if limit is not None:
            return full[-limit:]
        return full

    async def add_items(self, new_items: list[TResponseInputItem]) -> None:
        """Add items to phase-local storage.

        Called by SDK. Does NOT modify inherited_history.
        """
        self.items.extend(new_items)

    async def pop_item(self) -> TResponseInputItem | None:
        """Pop from phase-local items only."""
        if self.items:
            return self.items.pop()
        return None

    async def clear_session(self) -> None:
        """Clear phase-local items only."""
        self.items.clear()

    def __getattr__(self, name: str) -> Any:
        """Dynamic attribute access via data dict."""
        try:
            data = object.__getattribute__(self, "data")
            if name in data:
                return data[name]
        except AttributeError:
            pass
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Dynamic attribute setting via data dict."""
        if name in ("session_id", "label", "items", "data", "inherited_history"):
            object.__setattr__(self, name, value)
        else:
            try:
                data = object.__getattribute__(self, "data")
                data[name] = value
            except AttributeError:
                object.__setattr__(self, name, value)


logger = logging.getLogger(__name__)


async def get_session_history() -> list[TResponseInputItem]:
    """Get history from current Session if available.

    Returns empty list if no Session is set.
    Session.get_items() is async, returns list of message dicts.
    """
    session = current_session.get()
    if session is None:
        return []
    try:
        return await session.get_items()
    except Exception as e:
        logger.warning("Failed to get session history: %s", e)
        return []


@asynccontextmanager
async def phase(
    label: str,
    share_context: bool = True,
    persist: bool = False,
) -> AsyncIterator[PhaseSession | None]:
    """Context manager for workflow phases.

    Args:
        label: Phase label for UI display
        share_context: Create PhaseSession with shared context (default: True)
        persist: Write last assistant response to Session on exit (default: False)

    Note:
        Handler is injected by Runner, not by phase.
        This keeps UI dependency out of Flow code.

    Example:
        async with phase("Research"):
            r1 = await agent1(query).stream()
            r2 = await agent2(query).stream()  # Sees r1's context

        # With persist=True, last assistant response is written to Session
        async with phase("Research", persist=True):
            r1 = await agent(msg).stream()
            r2 = await agent(r1).stream()
            # On exit: last assistant response -> Session
    """
    start = time.perf_counter()

    phase_session: PhaseSession | None = None
    session_history_token = None

    if share_context:
        inherited_history = await get_session_history()
        phase_session = PhaseSession(label, inherited_history=inherited_history)
    else:
        # share_context=False: snapshot Session history at phase start (read-only).
        # This snapshot is fixed for predictability; concurrent writes are not reflected.
        cached_history = await get_session_history()
        session_history_token = current_phase_session_history.set(cached_history)

    phase_session_token = None
    if phase_session is not None:
        phase_session_token = current_phase_session.set(phase_session)

    # Mark that we're inside a phase (for share_context=False handling)
    in_phase_token = current_in_phase.set(True)

    # Emit PhaseStarted to handler
    phase_started_event = PhaseStarted(label=label)
    handler = current_handler.get()
    if handler is not None:
        result = handler(phase_started_event)
        if hasattr(result, "__await__"):
            await result

    # ChatKit integration: emit phase label to create workflow boundary
    chatkit_ctx = current_chatkit_context.get()
    if chatkit_ctx is not None:
        await chatkit_ctx.emit_phase_label(label)

    try:
        yield phase_session
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # persist=True: write last assistant response to Session
        # Phase is "internal thinking space" - only the final result is persisted.
        # User message management is the programmer's responsibility.
        # Note: reasoning models return [reasoning, message] pairs that must stay together.
        if persist and phase_session is not None and phase_session.items:
            session = current_session.get()
            if session is not None:
                items = phase_session.items
                for i in range(len(items) - 1, -1, -1):
                    item = items[i]
                    if item.get("role") == "assistant" and item.get("content"):
                        # Check if preceding item is a reasoning item (required by API)
                        to_persist = []
                        if i > 0 and items[i - 1].get("type") == "reasoning":
                            to_persist.append(items[i - 1])
                        to_persist.append(item)
                        try:
                            await session.add_items(to_persist)
                        except Exception as e:
                            logger.warning("Failed to persist phase result to session: %s", e)
                        break

        # ChatKit integration: close workflow to allow next phase to create new one
        if chatkit_ctx is not None:
            await chatkit_ctx.close_workflow()

        # Emit PhaseEnded to handler
        phase_ended_event = PhaseEnded(label=label, elapsed_ms=elapsed_ms)
        if handler is not None:
            result = handler(phase_ended_event)
            if hasattr(result, "__await__"):
                await result

        # Reset in_phase flag
        current_in_phase.reset(in_phase_token)

        # Reset cached session history
        if session_history_token is not None:
            current_phase_session_history.reset(session_history_token)

        if phase_session_token is not None:
            current_phase_session.reset(phase_session_token)
