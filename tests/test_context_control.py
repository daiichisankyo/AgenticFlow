"""Section 4: Context Control Tests - Real API calls.

Tests for:
- 4.1 Default context (Session usage)
- 4.2 isolated() - Complete isolation
- 4.3 Context priority (phase > Runner Session)

All tests use real GPT API calls. No mocks.
"""

from __future__ import annotations

import pytest
from agents import SQLiteSession

from agentic_flow import Agent, Runner, phase


class TestDefaultContext:
    """4.1 Default context behavior."""

    @pytest.mark.asyncio
    async def test_runner_session_used_by_default(self):
        """Agent uses Runner's Session by default."""
        agent = Agent(
            name="session_user",
            instructions="Remember what the user tells you.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            return await agent(msg).stream()

        session = SQLiteSession(session_id="default_ctx_test", db_path=":memory:")
        chat = Runner(flow=flow, session=session)

        await chat("My favorite color is blue")
        result = await chat("What is my favorite color?")

        assert "blue" in result.lower()
        print(f"Session memory result: {result}")

    @pytest.mark.asyncio
    async def test_phase_session_used_when_share_context(self):
        """When share_context=True, PhaseSession is used."""
        agent = Agent(
            name="phase_ctx_user",
            instructions="Answer based on conversation history.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            async with phase("Research", share_context=True) as p:
                await p.add_items([{"role": "user", "content": "My favorite fruit is mango"}])
                await p.add_items([{"role": "assistant", "content": "Got it, mango!"}])

                result = await agent("What is my favorite fruit?").stream()
                return result

        chat = Runner(flow=flow)
        result = await chat("test")

        assert "mango" in result.lower()
        print(f"PhaseSession result: {result}")


class TestIsolated:
    """4.2 isolated() - Complete isolation."""

    @pytest.mark.asyncio
    async def test_isolated_does_not_read_session(self):
        """isolated() does not read from Session."""
        agent = Agent(
            name="isolated_reader",
            instructions="If you know a color, say it. Otherwise say 'UNKNOWN'.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            return await agent(msg).isolated().stream()

        session = SQLiteSession(session_id="isolated_read_test", db_path=":memory:")
        chat = Runner(flow=flow, session=session)

        await chat("My favorite color is purple")
        result = await chat("What color did I mention?")

        assert "UNKNOWN" in result.upper() or "purple" not in result.lower()
        print(f"Isolated read test: {result}")

    @pytest.mark.asyncio
    async def test_isolated_does_not_accumulate_in_session(self):
        """isolated() calls don't accumulate internal conversation in Session.

        Design note:
        - isolated() means Agent doesn't read/write Session during execution
        - Runner still writes Flow's final return value to Session (by design)
        - This test verifies that multiple isolated() calls in same Flow
          don't see each other's context (each is stateless)
        """
        agent = Agent(
            name="isolated_multi",
            instructions="If you see a number in history, add 1. Else start with 1.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            r1 = await agent("Count").isolated().stream()
            r2 = await agent("Count").isolated().stream()
            r3 = await agent("Count").isolated().stream()
            return f"{r1}, {r2}, {r3}"

        chat = Runner(flow=flow)
        result = await chat("test")

        assert "1" in result
        assert "3" not in result
        print(f"Isolated multi-call test: {result}")

    @pytest.mark.asyncio
    async def test_isolated_ignores_phase_session(self):
        """isolated() ignores PhaseSession even with share_context=True."""
        agent = Agent(
            name="isolated_phase",
            instructions="If you see a city in history, say it. Otherwise say 'NONE'.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            async with phase("Test", share_context=True) as p:
                await p.add_items([{"role": "user", "content": "My favorite city is Tokyo"}])
                await p.add_items([{"role": "assistant", "content": "Got it, Tokyo!"}])

                result = await agent("What city did I mention?").isolated().stream()
                return result

        chat = Runner(flow=flow)
        result = await chat("test")

        assert "Tokyo" not in result or "NONE" in result.upper()
        print(f"Isolated ignores phase: {result}")


class TestContextPriority:
    """4.3 Context priority: phase > Runner Session."""

    @pytest.mark.asyncio
    async def test_phase_session_overrides_session(self):
        """PhaseSession overrides Session when share_context=True."""
        agent = Agent(
            name="phase_priority",
            instructions="Answer based on history.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            async with phase("Test", share_context=True) as p:
                await p.add_items([{"role": "user", "content": "Code is GAMMA"}])
                await p.add_items([{"role": "assistant", "content": "Noted: GAMMA"}])

                return await agent("What is the code?").stream()

        session = SQLiteSession(session_id="priority_test", db_path=":memory:")
        chat = Runner(flow=flow, session=session)

        await chat("Code is BETA")
        result = await chat("test")

        assert "GAMMA" in result
        print(f"Phase overrides session: {result}")

    @pytest.mark.asyncio
    async def test_isolated_overrides_all(self):
        """isolated() overrides everything - completely stateless."""
        agent = Agent(
            name="isolated_all",
            instructions="If you have context, summarize. Else say 'STATELESS'.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            async with phase("Test", share_context=True) as p:
                await p.add_items([{"role": "user", "content": "Remember Y"}])

                prompt = "What do you remember?"
                return await agent(prompt).isolated().stream()

        session = SQLiteSession(session_id="iso_all_test", db_path=":memory:")
        chat = Runner(flow=flow, session=session)

        await chat("Remember Z")
        result = await chat("test")

        is_stateless = "STATELESS" in result.upper()
        has_no_context = "Y" not in result and "Z" not in result
        assert is_stateless or has_no_context
        print(f"Isolated overrides all: {result}")


class TestPhasePersist:
    """4.4 phase(persist=True) - Session write on phase exit."""

    @pytest.mark.asyncio
    async def test_phase_persist_writes_to_session(self):
        """persist=True writes last assistant response to Session on phase exit."""
        agent = Agent(
            name="persist_agent",
            instructions="Answer the question directly.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            async with phase("Research", persist=True):
                return await agent(msg).stream()

        session = SQLiteSession(session_id="persist_test", db_path=":memory:")
        chat = Runner(flow=flow, session=session)

        await chat("My favorite animal is elephant")

        items = await session.get_items()
        assert len(items) == 1, "persist=True should write only last assistant response"
        assert items[0]["role"] == "assistant"
        print(f"Phase persist test: {len(items)} items in session")

    @pytest.mark.asyncio
    async def test_phase_persist_false_does_not_write(self):
        """persist=False (default) does not write to Session."""
        agent = Agent(
            name="no_persist_agent",
            instructions="Answer directly.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            async with phase("Research", persist=False):
                return await agent(msg).stream()

        session = SQLiteSession(session_id="no_persist_test", db_path=":memory:")
        chat = Runner(flow=flow, session=session)

        await chat("My favorite fruit is banana")

        items = await session.get_items()
        assert len(items) == 0
        print("Phase persist=False test: session is empty as expected")

    @pytest.mark.asyncio
    async def test_phase_persist_multi_agent(self):
        """persist=True writes only last assistant response."""
        agent1 = Agent(
            name="agent_first",
            instructions="Say 'FIRST_RESPONSE'.",
            model="gpt-5.2",
        )
        agent2 = Agent(
            name="agent_second",
            instructions="Say 'SECOND_RESPONSE'.",
            model="gpt-5.2",
        )

        async def flow(msg: str) -> str:
            async with phase("Multi", persist=True):
                r1 = await agent1(msg).stream()
                r2 = await agent2(r1).stream()
                return r2

        session = SQLiteSession(session_id="multi_persist_test", db_path=":memory:")
        chat = Runner(flow=flow, session=session)

        await chat("test")

        items = await session.get_items()
        assert len(items) == 1, "persist=True should write only last assistant response"
        assert items[0]["role"] == "assistant"
        # Verify it's the SECOND agent's response
        content = items[0].get("content", [])
        if isinstance(content, list) and content:
            text = content[0].get("text", "") if isinstance(content[0], dict) else ""
        else:
            text = str(content)
        assert "SECOND" in text.upper()
        print(f"Phase persist multi-agent: last assistant written, {len(items)} items")
