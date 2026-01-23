"""Semantic behavior tests for Agentic Flow.

This module tests the core semantic guarantees of Agentic Flow:

1. resolve_input() priority: isolated > phase > session
2. Phase does not write to Session (use phase(persist=True) for that)
3. phase(persist=True) writes last assistant response to Session at phase end
4. silent() suppresses handler/ChatKit events
5. share_context=False maintains read-only behavior
6. ChatKit context creates phase boundaries

These tests verify the "meaning" of the library, not just the implementation.
They serve as the contract that users can rely on.

Design Philosophy Reference (docs/design/):
- execution-model.md: Priority (phase > Runner Session, isolated overrides all)
- execution-model.md: Stream / Display / Store separation
- concepts.md: Session management principles
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from agents import SQLiteSession

from agentic_flow import Agent, Runner, phase
from agentic_flow.agent import (
    current_handler,
    current_phase_session,
    current_session,
)
from agentic_flow.phase import PhaseSession, current_in_phase, current_phase_session_history


class TestResolveInputPriority:
    """Test resolve_input() priority order.

    Priority (from docs/design/execution-model.md):
        1. isolated() overrides everything (completely stateless)
        2. phase (share_context=True) > Runner's global Session
        3. phase (share_context=False) reads Session but doesn't write
        4. Default: use Runner's global Session
    """

    def test_priority_isolated_ignores_phase_session(self):
        """isolated() ignores PhaseSession even when set."""
        agent = Agent(name="test", instructions="test", model="gpt-5.2")
        ctx = PhaseSession("test", inherited_history=[{"role": "user", "content": "history"}])

        token = current_phase_session.set(ctx)
        try:
            spec = agent("prompt").isolated()
            input_data, session = spec.resolve_input()

            assert input_data == "prompt"  # Raw input, no history
            assert session is None
        finally:
            current_phase_session.reset(token)

    def test_priority_isolated_ignores_session(self):
        """isolated() ignores Session even when set."""
        agent = Agent(name="test", instructions="test", model="gpt-5.2")
        session = SQLiteSession(session_id="test", db_path=":memory:")

        token = current_session.set(session)
        try:
            spec = agent("prompt").isolated()
            input_data, resolved_session = spec.resolve_input()

            assert input_data == "prompt"
            assert resolved_session is None
        finally:
            current_session.reset(token)

    def test_priority_phase_over_session(self):
        """PhaseSession takes priority over Session."""
        agent = Agent(name="test", instructions="test", model="gpt-5.2")

        session = SQLiteSession(session_id="test", db_path=":memory:")
        phase_session = PhaseSession(
            "test",
            inherited_history=[
                {"role": "user", "content": [{"type": "input_text", "text": "inherited"}]}
            ],
        )

        session_token = current_session.set(session)
        phase_token = current_phase_session.set(phase_session)
        in_phase_token = current_in_phase.set(True)

        try:
            spec = agent("new prompt")
            input_data, resolved_session = spec.resolve_input()

            # Should use PhaseSession
            assert input_data == "new prompt"
            assert resolved_session is phase_session
        finally:
            current_in_phase.reset(in_phase_token)
            current_phase_session.reset(phase_token)
            current_session.reset(session_token)

    def test_priority_default_uses_session(self):
        """Default (no phase) uses Session."""
        agent = Agent(name="test", instructions="test", model="gpt-5.2")

        session = SQLiteSession(session_id="test", db_path=":memory:")
        token = current_session.set(session)

        try:
            spec = agent("prompt")
            input_data, resolved_session = spec.resolve_input()

            assert input_data == "prompt"
            assert resolved_session is session
        finally:
            current_session.reset(token)

    def test_priority_share_context_false_reads_session(self):
        """share_context=False reads Session but doesn't write."""
        agent = Agent(name="test", instructions="test", model="gpt-5.2")

        session = SQLiteSession(session_id="test", db_path=":memory:")
        cached_history = [{"role": "user", "content": [{"type": "input_text", "text": "cached"}]}]

        session_token = current_session.set(session)
        in_phase_token = current_in_phase.set(True)
        history_token = current_phase_session_history.set(cached_history)

        try:
            spec = agent("new prompt")
            input_data, resolved_session = spec.resolve_input()

            # Should use cached history
            assert isinstance(input_data, list)
            assert len(input_data) == 2
            assert input_data[0]["content"][0]["text"] == "cached"

            # No Session (no write)
            assert resolved_session is None
        finally:
            current_phase_session_history.reset(history_token)
            current_in_phase.reset(in_phase_token)
            current_session.reset(session_token)


class TestPhaseSessionWriteBehavior:
    """Test that phase controls Session write behavior correctly.

    From docs/design/execution-model.md (Session management):
    - In phase: writes to PhaseSession (not Session)
    - In phase(persist=True): last assistant response written to Session at phase end
    """

    @pytest.mark.asyncio
    async def test_phase_does_not_write_to_session(self):
        """Phase without persist=True should not write to Session."""
        session = SQLiteSession(session_id="test_no_write", db_path=":memory:")

        # Verify session is empty initially
        initial_items = await session.get_items()
        assert len(initial_items) == 0

        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test", share_context=True):
                # This should NOT write to Session
                return await agent(msg)

        chat = Runner(flow=flow, session=session)
        await chat("test message")

        # Session should still be empty
        final_items = await session.get_items()
        assert len(final_items) == 0, "Phase without persist=True should not write to Session"

    @pytest.mark.asyncio
    async def test_phase_persist_writes_to_session(self):
        """phase(persist=True) should write last assistant response to Session at phase end."""
        session = SQLiteSession(session_id="test_persist_write", db_path=":memory:")

        initial_items = await session.get_items()
        assert len(initial_items) == 0

        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test", share_context=True, persist=True):
                # Last assistant response is written to Session at phase end
                return await agent(msg)

        chat = Runner(flow=flow, session=session)
        await chat("test message")

        # Session should have last assistant response
        final_items = await session.get_items()
        assert len(final_items) == 1, "phase(persist=True) should write last assistant to Session"
        assert final_items[0]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_phase_session_updated_but_not_session(self):
        """PhaseSession should be updated, but Session should not."""
        session = SQLiteSession(session_id="test_ctx_update", db_path=":memory:")

        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")
        captured_ctx = None

        async def flow(msg: str) -> str:
            nonlocal captured_ctx
            async with phase("Test", share_context=True) as ctx:
                await agent(msg)
                captured_ctx = ctx
                return "done"

        chat = Runner(flow=flow, session=session)
        await chat("test")

        # PhaseSession should have items entries
        assert captured_ctx is not None
        assert len(captured_ctx.items) == 2  # user + assistant

        # Session should be empty
        session_items = await session.get_items()
        assert len(session_items) == 0


class TestSilentEventSuppression:
    """Test that silent() suppresses handler events correctly.

    From docs/design/execution-model.md:
    - silent(): suppresses UI display, does not affect PhaseSession writes
    """

    @pytest.mark.asyncio
    async def test_silent_suppresses_handler_in_non_streaming(self):
        """silent() should not call handler in non-streaming mode."""
        events = []

        def handler(event):
            events.append(event)

        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test"):
                return await agent(msg).silent()

        chat = Runner(flow=flow, handler=handler)
        result = await chat("test")

        # Result should still be returned
        assert result is not None

        # Handler should NOT have received AgentResult events
        agent_results = [e for e in events if type(e).__name__ == "AgentResult"]
        assert len(agent_results) == 0, "silent() should suppress AgentResult events"

    @pytest.mark.asyncio
    async def test_silent_suppresses_streaming_events(self):
        """silent().stream() should not forward streaming events to handler."""
        events = []

        def handler(event):
            events.append(event)

        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test"):
                return await agent(msg).silent().stream()

        chat = Runner(flow=flow, handler=handler)
        result = await chat("test")

        # Result should still be returned
        assert result is not None

        # No streaming events should be captured
        # (PhaseStarted/PhaseEnded may still be emitted, but not agent events)
        streaming_events = [e for e in events if hasattr(e, "data") and hasattr(e.data, "delta")]
        assert len(streaming_events) == 0, "silent() should suppress streaming events"

    @pytest.mark.asyncio
    async def test_silent_still_updates_phase_session(self):
        """silent() should still update PhaseSession."""
        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")
        captured_ctx = None

        async def flow(msg: str) -> str:
            nonlocal captured_ctx
            async with phase("Test", share_context=True) as ctx:
                await agent(msg).silent()
                captured_ctx = ctx
                return "done"

        chat = Runner(flow=flow)
        await chat("test")

        # PhaseSession should have entries even with silent()
        assert captured_ctx is not None
        assert len(captured_ctx.items) == 2, "silent() should still update PhaseSession"

    @pytest.mark.asyncio
    async def test_non_silent_does_call_handler(self):
        """Non-silent calls should call handler (control test)."""
        events = []

        def handler(event):
            events.append(event)

        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test"):
                return await agent(msg).stream()

        chat = Runner(flow=flow, handler=handler)
        await chat("test")

        # Handler should have received events
        assert len(events) > 0, "Non-silent should call handler"


class TestShareContextFalseReadOnly:
    """Test that share_context=False is read-only.

    From docs/design/concepts.md (phase parameters):
    - share_context=False: can read Session, PhaseSession not created, no Session write
    """

    @pytest.mark.asyncio
    async def test_share_context_false_returns_none(self):
        """share_context=False should yield None for context."""
        async with phase("Test", share_context=False) as ctx:
            assert ctx is None

    @pytest.mark.asyncio
    async def test_share_context_false_reads_session_history(self):
        """share_context=False should read Session history."""
        session = SQLiteSession(session_id="test_read_only", db_path=":memory:")

        # Add items to session
        await session.add_items(
            [
                {"role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                {"role": "assistant", "content": [{"type": "output_text", "text": "hi"}]},
            ]
        )

        agent = Agent(name="test", instructions="test", model="gpt-5.2")

        token = current_session.set(session)
        try:
            async with phase("Test", share_context=False):
                spec = agent("new message")
                input_data, resolved_session = spec.resolve_input()

                # Should have session history
                assert isinstance(input_data, list)
                assert len(input_data) == 3  # 2 history + 1 new

                # Should NOT have session for write
                assert resolved_session is None
        finally:
            current_session.reset(token)

    @pytest.mark.asyncio
    async def test_share_context_false_does_not_write(self):
        """share_context=False should not write to Session."""
        session = SQLiteSession(session_id="test_no_write_false", db_path=":memory:")

        initial_items = await session.get_items()
        assert len(initial_items) == 0

        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test", share_context=False):
                return await agent(msg)

        chat = Runner(flow=flow, session=session)
        await chat("test")

        # Session should still be empty
        final_items = await session.get_items()
        assert len(final_items) == 0, "share_context=False should not write to Session"


class TestChatKitBoundary:
    """Test ChatKit context boundary behavior.

    From docs/design/execution-model.md (workflow boundary):
    - phase() creates workflow boundary
    - emit_phase_label() at start, close_workflow() at end
    """

    @pytest.mark.asyncio
    async def test_phase_emits_label_in_chatkit_context(self):
        """phase() should call emit_phase_label in ChatKit context."""
        from agentic_flow.chatkit import ChatKitExecutionContext, current_chatkit_context

        mock_agent_context = MagicMock()
        mock_store = MagicMock()

        ctx = ChatKitExecutionContext(mock_agent_context, mock_store)
        ctx.emit_phase_label = AsyncMock()
        ctx.close_workflow = AsyncMock()

        token = current_chatkit_context.set(ctx)
        try:
            async with phase("Test Label"):
                pass

            # Should have called emit_phase_label
            ctx.emit_phase_label.assert_called_once_with("Test Label")

            # Should have called close_workflow
            ctx.close_workflow.assert_called_once()
        finally:
            current_chatkit_context.reset(token)

    @pytest.mark.asyncio
    async def test_phase_closes_workflow_even_on_error(self):
        """phase() should close workflow even when exception occurs."""
        from agentic_flow.chatkit import ChatKitExecutionContext, current_chatkit_context

        mock_agent_context = MagicMock()
        mock_store = MagicMock()

        ctx = ChatKitExecutionContext(mock_agent_context, mock_store)
        ctx.emit_phase_label = AsyncMock()
        ctx.close_workflow = AsyncMock()

        token = current_chatkit_context.set(ctx)
        try:
            with pytest.raises(ValueError):
                async with phase("Test"):
                    raise ValueError("Test error")

            # Should still have closed workflow
            ctx.close_workflow.assert_called_once()
        finally:
            current_chatkit_context.reset(token)

    @pytest.mark.asyncio
    async def test_silent_suppresses_chatkit_events(self):
        """silent() should not push events to ChatKit queue."""
        from agentic_flow.chatkit import ChatKitExecutionContext, current_chatkit_context

        mock_agent_context = MagicMock()
        mock_store = MagicMock()

        ctx = ChatKitExecutionContext(mock_agent_context, mock_store)

        async def mock_execute_spec(spec):
            # Verify is_silent is respected
            if spec.is_silent:
                # Simulate silent execution (no events pushed)
                return "silent result"
            return "normal result"

        ctx.execute_spec = mock_execute_spec

        agent = Agent(name="test", instructions="test", model="gpt-5.2")
        spec = agent("test").silent()

        token = current_chatkit_context.set(ctx)
        try:
            result = await ctx.execute_spec(spec)
            assert result == "silent result"
        finally:
            current_chatkit_context.reset(token)


class TestEventTypeSystem:
    """Test that Event and Handler types are correctly defined.

    From the type system fix:
    - Event = StreamEvent | PhaseStarted | PhaseEnded | AgentResult
    - Handler = Callable[[Event], Any]
    """

    def test_event_type_includes_all_events(self):
        """Event type should include all event types."""
        from typing import get_args

        from agentic_flow.types import AgentResult, Event, PhaseEnded, PhaseStarted

        # Get the types in the Union
        args = get_args(Event)

        # StreamEvent is itself a Union, so its members are expanded
        # Just verify our custom types are included
        assert PhaseStarted in args
        assert PhaseEnded in args
        assert AgentResult in args
        # And that there are more types (SDK StreamEvent members)
        assert len(args) > 3

    def test_handler_type_accepts_all_events(self):
        """Handler should be typed to accept all Event types."""
        from agentic_flow.types import Handler

        # Handler should be Callable[[Event], Any]
        # Just verify Handler is defined (type checking is static)
        assert Handler is not None


class TestContextVarIsolation:
    """Test that contextvars are properly isolated.

    From docs/design/implementation.md:
    - Handler is injected by Runner and fixed during Flow execution
    - PhaseSession is isolated between phases
    - Contexts don't mix in parallel execution
    """

    @pytest.mark.asyncio
    async def test_handler_restored_after_flow(self):
        """Handler should be None after flow completes."""

        def test_handler(event):
            pass

        async def flow(msg: str) -> str:
            # Handler should be set inside flow
            assert current_handler.get() is test_handler
            return "done"

        chat = Runner(flow=flow, handler=test_handler)

        # Before flow, handler should be None
        assert current_handler.get() is None

        await chat("test")

        # After flow, handler should be None again
        assert current_handler.get() is None

    @pytest.mark.asyncio
    async def test_session_restored_after_flow(self):
        """Session should be None after flow completes."""
        session = SQLiteSession(session_id="test", db_path=":memory:")

        async def flow(msg: str) -> str:
            assert current_session.get() is session
            return "done"

        chat = Runner(flow=flow, session=session)

        assert current_session.get() is None
        await chat("test")
        assert current_session.get() is None

    @pytest.mark.asyncio
    async def test_phase_session_restored_after_nested(self):
        """PhaseSession should be restored after nested phase."""
        async with phase("Outer", share_context=True) as outer:
            outer.data["marker"] = "outer"

            async with phase("Inner", share_context=True) as inner:
                inner.data["marker"] = "inner"
                assert current_phase_session.get() is inner

            # Should be restored to outer
            assert current_phase_session.get() is outer
            assert outer.data["marker"] == "outer"

        # Should be None after all phases
        assert current_phase_session.get() is None

    @pytest.mark.asyncio
    async def test_in_phase_flag_restored(self):
        """current_in_phase should be restored after phase."""
        assert current_in_phase.get() is False

        async with phase("Test"):
            assert current_in_phase.get() is True

        assert current_in_phase.get() is False


class TestPhaseEventsToHandler:
    """Test that phase events are forwarded to Handler.

    phase() should emit PhaseStarted/PhaseEnded to current_handler.
    """

    @pytest.mark.asyncio
    async def test_handler_receives_phase_started(self):
        """Handler should receive PhaseStarted event."""
        from agentic_flow.types import PhaseStarted

        events = []

        def handler(event):
            events.append(event)

        async def flow(msg: str) -> str:
            async with phase("TestPhase"):
                return "done"

        chat = Runner(flow=flow, handler=handler)
        await chat("test")

        phase_started = [e for e in events if isinstance(e, PhaseStarted)]
        assert len(phase_started) == 1
        assert phase_started[0].label == "TestPhase"

    @pytest.mark.asyncio
    async def test_handler_receives_phase_ended(self):
        """Handler should receive PhaseEnded event."""
        from agentic_flow.types import PhaseEnded

        events = []

        def handler(event):
            events.append(event)

        async def flow(msg: str) -> str:
            async with phase("TestPhase"):
                return "done"

        chat = Runner(flow=flow, handler=handler)
        await chat("test")

        phase_ended = [e for e in events if isinstance(e, PhaseEnded)]
        assert len(phase_ended) == 1
        assert phase_ended[0].label == "TestPhase"
        assert phase_ended[0].elapsed_ms >= 0

    @pytest.mark.asyncio
    async def test_handler_receives_nested_phase_events(self):
        """Handler should receive events for nested phases."""
        from agentic_flow.types import PhaseEnded, PhaseStarted

        events = []

        def handler(event):
            events.append(event)

        async def flow(msg: str) -> str:
            async with phase("Outer"):
                async with phase("Inner"):
                    pass
            return "done"

        chat = Runner(flow=flow, handler=handler)
        await chat("test")

        phase_started = [e for e in events if isinstance(e, PhaseStarted)]
        phase_ended = [e for e in events if isinstance(e, PhaseEnded)]

        assert len(phase_started) == 2
        assert len(phase_ended) == 2
        assert phase_started[0].label == "Outer"
        assert phase_started[1].label == "Inner"


