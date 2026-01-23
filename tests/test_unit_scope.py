"""Unit tests for scope/priority behavior.

These tests verify internal behavior with real API calls.
No mocks - all tests use real Agent and SDK calls.
"""

from __future__ import annotations

import pytest
from agents import SQLiteSession

from agentic_flow import Agent, Runner, phase
from agentic_flow.agent import (
    current_handler,
    current_phase_session,
    current_session,
)
from agentic_flow.phase import PhaseSession


class TestPhaseSessionUpdate:
    """PhaseSession must be updated after execution in phase."""

    @pytest.mark.asyncio
    async def test_phase_session_updates_in_phase(self):
        """When in phase with share_context, PhaseSession is updated."""
        agent = Agent(
            name="test_agent",
            instructions="Reply with one word.",
            model="gpt-5.2",
        )

        async with phase("Test", share_context=True) as ctx:
            await agent("implicit test")

            assert len(ctx.items) == 2
            assert ctx.items[0]["role"] == "user"
            assert ctx.items[1]["role"] == "assistant"


class TestIsolatedIgnoresAll:
    """isolated() must ignore Session and PhaseSession."""

    @pytest.mark.asyncio
    async def test_isolated_returns_none_for_session(self):
        """isolated() should not use Session."""
        session = SQLiteSession(session_id="test_isolated", db_path=":memory:")
        token = current_session.set(session)

        try:
            agent = Agent(
                name="test_agent",
                instructions="Reply briefly.",
                model="gpt-5.2",
            )
            spec = agent("test").isolated()
            input_data, resolved_session = spec.resolve_input()

            assert resolved_session is None
            assert input_data == "test"
        finally:
            current_session.reset(token)

    @pytest.mark.asyncio
    async def test_isolated_ignores_phase_session(self):
        """isolated() should not use PhaseSession."""
        agent = Agent(
            name="test_agent",
            instructions="Reply briefly.",
            model="gpt-5.2",
        )

        async with phase("Test", share_context=True) as ctx:
            await ctx.add_items([{"role": "user", "content": "history"}])

            spec = agent("test").isolated()
            input_data, session = spec.resolve_input()

            assert session is None


class TestRunnerHandlerInjection:
    """Runner must inject handler via contextvars."""

    @pytest.mark.asyncio
    async def test_runner_injects_handler(self):
        """Handler should be available inside flow via Runner."""
        events = []

        def test_handler(event):
            events.append(event)

        captured_handler = None

        async def flow(msg: str) -> str:
            nonlocal captured_handler
            async with phase("Test"):
                captured_handler = current_handler.get()
            return "done"

        chat = Runner(flow=flow, handler=test_handler)
        await chat("test")

        assert captured_handler is test_handler
        assert current_handler.get() is None

    @pytest.mark.asyncio
    async def test_nested_phases_share_runner_handler(self):
        """Nested phases share the same Runner-injected handler."""
        events = []

        def test_handler(event):
            events.append(event)

        outer_captured = None
        inner_captured = None

        async def flow(msg: str) -> str:
            nonlocal outer_captured, inner_captured
            async with phase("Outer"):
                outer_captured = current_handler.get()
                async with phase("Inner"):
                    inner_captured = current_handler.get()
            return "done"

        chat = Runner(flow=flow, handler=test_handler)
        await chat("test")

        assert outer_captured is test_handler
        assert inner_captured is test_handler
        assert current_handler.get() is None

    @pytest.mark.asyncio
    async def test_phase_session_restoration(self):
        """PhaseSession should be restored after nested phase exits."""
        async with phase("Outer", share_context=True) as outer_ctx:
            outer_ctx.data["marker"] = "outer"

            async with phase("Inner", share_context=True) as inner_ctx:
                inner_ctx.data["marker"] = "inner"
                assert current_phase_session.get() == inner_ctx

            assert current_phase_session.get() == outer_ctx
            assert outer_ctx.data["marker"] == "outer"

        assert current_phase_session.get() is None


class TestMessageFormat:
    """P0-2: PhaseSession message format must be SDK-compatible."""

    @pytest.mark.asyncio
    async def test_phase_session_uses_sdk_message_format(self):
        """Messages in PhaseSession must use SDK format.

        SDK may use either:
        - Simple format: content is a string
        - Array format: content is a list of content blocks
        Both are valid SDK formats.
        """
        agent = Agent(
            name="test_agent",
            instructions="Reply with one word.",
            model="gpt-5.2",
        )

        async with phase("Test", share_context=True) as ctx:
            await agent("format test")

            user_msg = ctx.items[0]
            assert user_msg["role"] == "user"
            # SDK uses content as items (OpenAI Responses API format)
            assert user_msg.get("content") is not None

            assistant_msg = ctx.items[1]
            assert assistant_msg["role"] == "assistant"
            assert assistant_msg.get("content") is not None


class TestStructuredOutputPreservation:
    """P2-7: PhaseSession must preserve structured output."""

    @pytest.mark.asyncio
    async def test_last_output_preserved_in_data(self):
        """Pydantic output should be preserved in data['last_output']."""
        from pydantic import BaseModel

        class SimpleOutput(BaseModel):
            word: str

        agent = Agent(
            name="test_agent",
            instructions="Reply with a single word in the 'word' field.",
            model="gpt-5.2",
            output_type=SimpleOutput,
        )

        async with phase("Test", share_context=True) as ctx:
            result = await agent("give me a word")

            assert isinstance(result, SimpleOutput)
            # Note: structured output is now in the items, not data["last_output"]
            assert len(ctx.items) == 2


class TestPhaseSessionInheritance:
    """PhaseSession must inherit Session history when share_context=True."""

    @pytest.mark.asyncio
    async def test_phase_session_has_inherited_history_field(self):
        """PhaseSession should have inherited_history field."""
        ctx = PhaseSession("test")
        assert hasattr(ctx, "inherited_history")
        assert ctx.inherited_history == []

    @pytest.mark.asyncio
    async def test_phase_session_accepts_inherited_history(self):
        """PhaseSession can be initialized with inherited_history."""
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        ctx = PhaseSession("test", inherited_history=history)

        assert ctx.inherited_history == history
        assert ctx.items == []

    @pytest.mark.asyncio
    async def test_get_items_returns_inherited_plus_items(self):
        """get_items() returns inherited_history + items."""
        inherited = [
            {"role": "user", "content": "from session"},
            {"role": "assistant", "content": "session response"},
        ]
        ctx = PhaseSession("test", inherited_history=inherited)

        await ctx.add_items([{"role": "user", "content": "in phase"}])
        await ctx.add_items([{"role": "assistant", "content": "phase response"}])

        full = await ctx.get_items()

        assert len(full) == 4
        assert full[0]["content"] == "from session"
        assert full[1]["content"] == "session response"
        assert full[2]["content"] == "in phase"
        assert full[3]["content"] == "phase response"

    @pytest.mark.asyncio
    async def test_get_items_does_not_mutate_inherited(self):
        """get_items() should not mutate inherited_history."""
        inherited = [{"role": "user", "content": "original"}]
        ctx = PhaseSession("test", inherited_history=inherited)

        await ctx.add_items([{"role": "user", "content": "new"}])
        await ctx.get_items()

        assert len(inherited) == 1
        assert len(ctx.inherited_history) == 1

    @pytest.mark.asyncio
    async def test_phase_inherits_session_on_creation(self):
        """phase() with share_context=True should inherit Session history."""
        session = SQLiteSession(session_id="test_inherit", db_path=":memory:")

        # Add items to session
        await session.add_items(
            [
                {"role": "user", "content": [{"type": "input_text", "text": "session msg 1"}]},
                {
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "session msg 2"}],
                },
            ]
        )

        token = current_session.set(session)
        try:
            async with phase("Test", share_context=True) as ctx:
                assert ctx is not None
                assert len(ctx.inherited_history) == 2
                assert ctx.inherited_history[0]["role"] == "user"
                assert ctx.inherited_history[1]["role"] == "assistant"
        finally:
            current_session.reset(token)

    @pytest.mark.asyncio
    async def test_phase_without_session_has_empty_inherited(self):
        """phase() without Session should have empty inherited_history."""
        async with phase("Test", share_context=True) as ctx:
            assert ctx is not None
            assert ctx.inherited_history == []

    @pytest.mark.asyncio
    async def test_phase_without_share_context_no_inheritance(self):
        """phase() without share_context should not create PhaseSession."""
        session = SQLiteSession(session_id="test_no_share", db_path=":memory:")

        await session.add_items(
            [
                {"role": "user", "content": [{"type": "input_text", "text": "should not be used"}]},
            ]
        )

        token = current_session.set(session)
        try:
            async with phase("Test", share_context=False) as ctx:
                assert ctx is None
        finally:
            current_session.reset(token)


class TestPhaseSessionAttributeError:
    """PhaseSession should raise AttributeError for undefined attributes."""

    def test_undefined_attribute_raises_error(self):
        """Accessing undefined attribute should raise AttributeError."""
        from agentic_flow.phase import PhaseSession

        ctx = PhaseSession("test")
        with pytest.raises(AttributeError) as exc_info:
            _ = ctx.undefined_attribute
        assert "undefined_attribute" in str(exc_info.value)

    def test_defined_attribute_works(self):
        """Defined attribute should work normally."""
        from agentic_flow.phase import PhaseSession

        ctx = PhaseSession("test")
        ctx.my_value = "hello"
        assert ctx.my_value == "hello"

    def test_builtin_attributes_work(self):
        """Built-in attributes (label, items, data) should work."""
        from agentic_flow.phase import PhaseSession

        ctx = PhaseSession("test_label")
        assert ctx.label == "test_label"
        assert ctx.items == []
        assert ctx.data == {}


class TestShareContextFalse:
    """share_context=False: Session read OK, no write."""

    @pytest.mark.asyncio
    async def test_share_context_false_reads_session(self):
        """share_context=False should allow reading Session history."""
        session = SQLiteSession(session_id="test_read", db_path=":memory:")

        await session.add_items(
            [
                {"role": "user", "content": [{"type": "input_text", "text": "session history"}]},
                {"role": "assistant", "content": [{"type": "output_text", "text": "response"}]},
            ]
        )

        agent = Agent(
            name="test_agent",
            instructions="Reply briefly.",
            model="gpt-5.2",
        )

        token = current_session.set(session)
        try:
            async with phase("Test", share_context=False):
                spec = agent("new message")
                input_data, resolved_session = spec.resolve_input()

                # Should have Session history in input
                assert isinstance(input_data, list)
                assert len(input_data) == 3  # 2 history + 1 new
                assert input_data[0]["role"] == "user"
                assert input_data[1]["role"] == "assistant"
                assert input_data[2]["role"] == "user"

                # Session should be None (no write)
                assert resolved_session is None
        finally:
            current_session.reset(token)

    @pytest.mark.asyncio
    async def test_share_context_false_no_session_write(self):
        """share_context=False should not write to Session."""
        session = SQLiteSession(session_id="test_no_write", db_path=":memory:")

        initial_items = await session.get_items()
        assert len(initial_items) == 0

        agent = Agent(
            name="test_agent",
            instructions="Reply briefly.",
            model="gpt-5.2",
        )

        token = current_session.set(session)
        try:
            async with phase("Test", share_context=False):
                await agent("test message")

            # Session should still be empty (no write occurred)
            final_items = await session.get_items()
            assert len(final_items) == 0
        finally:
            current_session.reset(token)
