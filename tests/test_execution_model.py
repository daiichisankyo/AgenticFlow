"""Section 3: Execution Model Tests - Real API calls.

Tests for:
- 3.1 ExecutionSpec[T] - Declaration and execution separation
- 3.2 Execution triggers (await vs .stream())
- 3.3 Beautiful forms (allowed patterns)
- 3.4 Forbidden forms (not tested - they don't compile)

All tests use real GPT API calls. No mocks.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from agentic_flow import Agent, Runner, phase


class Analysis(BaseModel):
    """Test Pydantic model for typed output."""

    sentiment: str
    score: float


class Decision(BaseModel):
    """Test Pydantic model for control flow."""

    action: str
    reason: str


class TestExecutionSpecT:
    """3.1 ExecutionSpec[T] - Declaration and execution separation."""

    @pytest.mark.asyncio
    async def test_str_output_default(self):
        """Agent without output_type returns str."""
        agent = Agent(
            name="str_agent",
            instructions="Reply with exactly 'HELLO' and nothing else.",
            model="gpt-5.2",
        )

        result = await agent("Say hello")

        assert isinstance(result, str)
        assert "HELLO" in result.upper()

    @pytest.mark.asyncio
    async def test_pydantic_output(self):
        """Agent with output_type returns Pydantic model."""
        analyzer = Agent(
            name="analyzer",
            instructions="Analyze sentiment. Return positive/negative and score 0-1.",
            model="gpt-5.2",
            output_type=Analysis,
        )

        result = await analyzer("I love this product! It's amazing!")

        assert isinstance(result, Analysis)
        assert hasattr(result, "sentiment")
        assert hasattr(result, "score")
        assert isinstance(result.sentiment, str)
        assert isinstance(result.score, float)
        print(f"Analysis: sentiment={result.sentiment}, score={result.score}")

    @pytest.mark.asyncio
    async def test_execution_spec_not_executed_until_await(self):
        """agent(prompt) returns ExecutionSpec, not executed yet."""
        agent = Agent(
            name="lazy",
            instructions="Reply OK",
            model="gpt-5.2",
        )

        spec = agent("test")

        assert spec.input == "test"
        assert spec.streaming is False
        assert spec.is_isolated is False

        result = await spec
        assert "OK" in result


class TestExecutionTriggers:
    """3.2 Execution triggers - await vs .stream()."""

    @pytest.mark.asyncio
    async def test_await_returns_str(self):
        """await agent() returns str (non-streaming)."""
        agent = Agent(
            name="await_test",
            instructions="Reply with 'AWAIT OK'",
            model="gpt-5.2",
        )

        result = await agent("test")

        assert isinstance(result, str)
        assert "OK" in result

    @pytest.mark.asyncio
    async def test_await_returns_pydantic(self):
        """await agent() with output_type returns Pydantic."""
        agent = Agent(
            name="await_pydantic",
            instructions="Analyze sentiment as positive/negative with score 0-1.",
            model="gpt-5.2",
            output_type=Analysis,
        )

        result = await agent("This is great!")

        assert isinstance(result, Analysis)

    @pytest.mark.asyncio
    async def test_stream_returns_str(self, handler_log):
        """await agent().stream() returns str and streams events."""
        agent = Agent(
            name="stream_str",
            instructions="Reply with 'STREAM OK'",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            async with phase("Test"):
                return await agent(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("test")

        assert isinstance(result, str)
        assert "OK" in result
        assert len(handler_log.events) > 0, "Events should be captured"

    @pytest.mark.asyncio
    async def test_stream_returns_pydantic(self, handler_log):
        """await agent().stream() with output_type returns Pydantic and streams."""
        analyzer = Agent(
            name="stream_pydantic",
            instructions="Analyze sentiment as positive/negative with score 0-1.",
            model="gpt-5.2",
            output_type=Analysis,
        )

        async def flow(msg: str) -> Analysis:
            async with phase("Analyze"):
                return await analyzer(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("I absolutely love this!")

        assert isinstance(result, Analysis)
        assert len(handler_log.events) > 0, "Events should be captured"
        print(f"Streamed Analysis: {result}")


class TestBeautifulForms:
    """3.3 Beautiful forms - All allowed patterns work correctly."""

    @pytest.mark.asyncio
    async def test_normal_form(self):
        """out = await agent('prompt')"""
        agent = Agent(name="normal", instructions="Reply OK", model="gpt-5.2")

        out = await agent("test")

        assert "OK" in out

    @pytest.mark.asyncio
    async def test_isolated_form(self):
        """out = await agent('prompt').isolated()"""
        agent = Agent(name="isolated", instructions="Reply OK", model="gpt-5.2")

        out = await agent("test").isolated()

        assert "OK" in out

    @pytest.mark.asyncio
    async def test_streaming_form(self, handler_log):
        """out = await agent('prompt').stream()"""
        agent = Agent(name="streaming", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test"):
                return await agent(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        out = await chat("test")

        assert "OK" in out

    @pytest.mark.asyncio
    async def test_isolated_streaming_form(self, handler_log):
        """out = await agent('prompt').isolated().stream()"""
        agent = Agent(name="iso_stream", instructions="Reply OK", model="gpt-5.2")

        async def flow(msg: str) -> str:
            async with phase("Test"):
                return await agent(msg).isolated().stream()

        chat = Runner(flow=flow, handler=handler_log)
        out = await chat("test")

        assert "OK" in out

    @pytest.mark.asyncio
    async def test_all_forms_with_pydantic(self, handler_log):
        """All beautiful forms work with Pydantic output."""
        agent = Agent(
            name="pydantic_forms",
            instructions="Decide action as 'proceed' or 'stop' with reason.",
            model="gpt-5.2",
            output_type=Decision,
        )

        r1 = await agent("Should we continue?")
        assert isinstance(r1, Decision)

        r2 = await agent("Should we continue?").isolated()
        assert isinstance(r2, Decision)

        async def flow_stream(msg: str) -> Decision:
            async with phase("Stream"):
                return await agent(msg).stream()

        chat = Runner(flow=flow_stream, handler=handler_log)
        r3 = await chat("Should we continue?")
        assert isinstance(r3, Decision)

        async def flow_iso_stream(msg: str) -> Decision:
            async with phase("IsoStream"):
                return await agent(msg).isolated().stream()

        chat2 = Runner(flow=flow_iso_stream, handler=handler_log)
        r4 = await chat2("Should we continue?")
        assert isinstance(r4, Decision)
