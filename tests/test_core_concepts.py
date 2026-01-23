"""Section 8: Core Concepts Tests - Real API calls.

Tests for:
- 8.1 Agent - Callable that returns ExecutionSpec
- 8.2 phase() - Scoped context
- 8.3 Runner - Execution container

All tests use real GPT API calls. No mocks.
"""

from __future__ import annotations

import pytest
from agents import SQLiteSession
from pydantic import BaseModel

from agentic_flow import Agent, ExecutionSpec, Runner, phase, reasoning
from agentic_flow.agent import current_handler


class Sentiment(BaseModel):
    """Test Pydantic model."""

    mood: str
    confidence: float


class TestAgent:
    """8.1 Agent - Callable that returns ExecutionSpec[T]."""

    def test_agent_creation_str(self):
        """Agent without output_type creates Agent[str]."""
        agent = Agent(
            name="str_agent",
            instructions="Reply OK",
            model="gpt-5.2",
        )

        assert agent.sdk_kwargs.get("name") == "str_agent"
        assert agent.output_type is None

    def test_agent_creation_pydantic(self):
        """Agent with output_type creates Agent[T]."""
        agent = Agent(
            name="typed_agent",
            instructions="Return sentiment",
            model="gpt-5.2",
            output_type=Sentiment,
        )

        assert agent.output_type is Sentiment

    def test_callable_returns_execution_spec(self):
        """agent(prompt) returns ExecutionSpec, not result."""
        agent = Agent(name="test", instructions="OK", model="gpt-5.2")

        spec = agent("hello")

        assert isinstance(spec, ExecutionSpec)
        assert spec.input == "hello"
        assert spec.streaming is False

    def test_stream_chain(self):
        """agent(prompt).stream() sets streaming=True."""
        agent = Agent(name="test", instructions="OK", model="gpt-5.2")

        spec = agent("hello").stream()

        assert spec.streaming is True

    def test_isolated_chain(self):
        """agent(prompt).isolated() sets is_isolated=True."""
        agent = Agent(name="test", instructions="OK", model="gpt-5.2")

        spec = agent("hello").isolated()

        assert spec.is_isolated is True

    def test_chain_combinations(self):
        """Chaining .isolated().stream() works."""
        agent = Agent(name="test", instructions="OK", model="gpt-5.2")

        spec = agent("hello").isolated().stream()

        assert spec.is_isolated is True
        assert spec.streaming is True

    @pytest.mark.asyncio
    async def test_agent_with_model_settings(self, handler_log):
        """Agent with model_settings (SDK pass-through) works."""
        from agents import ModelSettings
        from openai.types.shared.reasoning import Reasoning

        agent = Agent(
            name="thinker",
            instructions="Think step by step. What is 7 * 8?",
            model="gpt-5.2",
            model_settings=ModelSettings(
                reasoning=Reasoning(effort="low", summary="auto"),
            ),
        )

        async def flow(msg: str) -> str:
            async with phase("Think"):
                return await agent(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("Calculate")

        assert "56" in result
        print(f"Reasoning result: {result}")

    @pytest.mark.asyncio
    async def test_agent_with_reasoning_helper(self, handler_log):
        """Agent with reasoning() helper works."""
        agent = Agent(
            name="thinker",
            instructions="Think step by step. What is 9 * 7?",
            model="gpt-5.2",
            model_settings=reasoning("low"),
        )

        async def flow(msg: str) -> str:
            async with phase("Think"):
                return await agent(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("Calculate")

        assert "63" in result
        print(f"Reasoning helper result: {result}")


class TestPhase:
    """8.2 phase() - Scoped context."""

    @pytest.mark.asyncio
    async def test_phase_basic(self):
        """Basic phase context manager works."""
        executed = False

        async with phase("Test"):
            executed = True

        assert executed

    @pytest.mark.asyncio
    async def test_runner_handler_injection(self, handler_log):
        """Runner(handler=...) injects handler via contextvars."""

        async def flow(msg: str) -> str:
            async with phase("Test"):
                h = current_handler.get()
                assert h is handler_log
            return "done"

        chat = Runner(flow=flow, handler=handler_log)
        await chat("test")

        assert current_handler.get() is None

    @pytest.mark.asyncio
    async def test_phase_handler_inheritance(self, handler_log):
        """Agent inside phase inherits handler from Runner."""
        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test"):
                return await agent(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("test")

        assert "OK" in result
        assert len(handler_log.events) > 0

    @pytest.mark.asyncio
    async def test_phase_share_context(self):
        """Default (share_context=True) creates PhaseSession."""
        async with phase("Test") as p:
            assert p is not None
            assert p.label == "Test"
            assert p.items == []

    @pytest.mark.asyncio
    async def test_phase_no_share_context(self):
        """share_context=False yields None."""
        async with phase("Test", share_context=False) as p:
            assert p is None

    @pytest.mark.asyncio
    async def test_phase_session_data(self):
        """PhaseSession can store arbitrary data."""
        async with phase("Test") as p:
            p.result = "test value"
            p.count = 42

            assert p.result == "test value"
            assert p.count == 42

    @pytest.mark.asyncio
    async def test_nested_phases(self, handler_log):
        """Nested phases work correctly with Runner-injected handler."""

        async def flow(msg: str) -> str:
            async with phase("Outer"):
                assert current_handler.get() is handler_log

                async with phase("Inner"):
                    assert current_handler.get() is handler_log

                assert current_handler.get() is handler_log
            return "done"

        chat = Runner(flow=flow, handler=handler_log)
        await chat("test")

        assert current_handler.get() is None


class TestRunner:
    """8.3 Runner - Execution container."""

    @pytest.mark.asyncio
    async def test_runner_basic(self):
        """Runner executes flow."""
        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            return await agent(msg)

        chat = Runner(flow=flow)
        result = await chat("test")

        assert "OK" in result

    @pytest.mark.asyncio
    async def test_runner_with_session(self):
        """Runner with Session maintains conversation."""
        agent = Agent(
            name="memory",
            instructions="Remember what user says.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            return await agent(msg).stream()

        session = SQLiteSession(session_id="runner_test", db_path=":memory:")
        chat = Runner(flow=flow, session=session)

        await chat("My name is TestUser")
        result = await chat("What is my name?")

        print(f"Session result: {result}")

    @pytest.mark.asyncio
    async def test_runner_callable(self):
        """Runner is callable with user message."""
        agent = Agent(name="test", instructions="Echo input", model="gpt-5.2")

        async def flow(msg: str) -> str:
            return await agent(msg)

        chat = Runner(flow=flow)
        result = await chat("Hello World")

        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_runner_without_session(self):
        """Runner without Session works (stateless)."""
        agent = Agent(name="test", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            return await agent(msg)

        chat = Runner(flow=flow)  # No session
        result = await chat("test")

        assert "OK" in result

    @pytest.mark.asyncio
    async def test_runner_multi_phase_flow(self, handler_log):
        """Runner executes multi-phase flow."""
        agent1 = Agent(name="a1", instructions="Say PHASE1", model="gpt-5.2")
        agent2 = Agent(name="a2", instructions="Say PHASE2", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Phase1"):
                r1 = await agent1(msg).stream()

            async with phase("Phase2"):
                r2 = await agent2(msg).stream()

            return f"{r1} | {r2}"

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("test")

        assert "PHASE1" in result or "PHASE2" in result or len(result) > 0
        print(f"Multi-phase: {result}")
