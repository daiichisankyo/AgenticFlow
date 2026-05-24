"""Tests for new SDK 0.14 session backends (Experience B of the 0.14 refresh).

The SDK 0.14 line populated ``agents.extensions.memory`` with several new
session implementations (SQLAlchemy, MongoDB, Redis, Dapr, encrypted,
async/advanced SQLite). They all inherit from ``SessionABC`` — the same
contract AF's ``PhaseSession`` and ``af.Runner(session=...)`` already depend
on. Verifying the contract for ``SQLAlchemySession`` is sufficient by
substitutability; the remaining backends share the same surface.

Optional dependencies (``sqlalchemy``, ``aiosqlite``) are pulled in via
``pytest.importorskip`` so the file is a no-op in environments where they
are not installed.
"""

from __future__ import annotations

import pytest

# Skip the entire module if the optional backends are absent. This keeps
# AF's default dev install lean while still verifying the contract when the
# extras are present (e.g. via `uv run --with sqlalchemy --with aiosqlite`).
pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from agents.extensions.memory.sqlalchemy_session import (  # noqa: E402
    SQLAlchemySession,
)
from agents.memory.session import SessionABC  # noqa: E402

from agentic_flow import Runner  # noqa: E402
from agentic_flow.phase import PhaseSession  # noqa: E402


def _make_session(session_id: str = "test") -> SQLAlchemySession:
    """Build an in-memory SQLAlchemySession with tables auto-created."""
    return SQLAlchemySession.from_url(
        session_id,
        url="sqlite+aiosqlite:///:memory:",
        create_tables=True,
    )


class TestSqlalchemySessionContract:
    """SQLAlchemySession implements SessionABC, the contract AF relies on."""

    def test_is_session_abc_subclass(self):
        assert issubclass(SQLAlchemySession, SessionABC)

    def test_has_all_abstract_methods(self):
        for name in ("add_items", "clear_session", "get_items", "pop_item"):
            assert hasattr(SQLAlchemySession, name)


class TestSqlalchemySessionRoundTrip:
    """add_items / get_items round-trip via SessionABC methods."""

    @pytest.mark.asyncio
    async def test_empty_session_returns_empty_list(self):
        session = _make_session("empty")

        assert await session.get_items() == []

    @pytest.mark.asyncio
    async def test_add_then_get_returns_items(self):
        session = _make_session("roundtrip")

        items = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        await session.add_items(items)

        retrieved = await session.get_items()
        assert len(retrieved) == 2
        assert retrieved[0]["role"] == "user"
        assert retrieved[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_pop_item_removes_last(self):
        session = _make_session("pop")
        await session.add_items(
            [
                {"role": "user", "content": "first"},
                {"role": "user", "content": "second"},
            ]
        )

        popped = await session.pop_item()

        assert popped is not None
        assert popped["content"] == "second"
        remaining = await session.get_items()
        assert len(remaining) == 1
        assert remaining[0]["content"] == "first"

    @pytest.mark.asyncio
    async def test_clear_session_drops_all_items(self):
        session = _make_session("clear")
        await session.add_items([{"role": "user", "content": "to be cleared"}])

        await session.clear_session()

        assert await session.get_items() == []


class TestPhaseSessionInheritsFromSqlalchemy:
    """PhaseSession can inherit history loaded from SQLAlchemySession.

    This is the path AF takes inside `phase(share_context=True)`: it reads
    the parent Session's items via `get_items()` and seeds PhaseSession's
    `inherited_history`. The behaviour must be identical regardless of the
    Session backend.
    """

    @pytest.mark.asyncio
    async def test_phase_session_seeded_from_sqlalchemy_history(self):
        session = _make_session("inherit")
        seed = [
            {"role": "user", "content": "prior question"},
            {"role": "assistant", "content": "prior answer"},
        ]
        await session.add_items(seed)

        history = await session.get_items()
        ctx = PhaseSession("inherit-test", inherited_history=history)

        items = await ctx.get_items()
        assert len(items) == len(seed)
        assert items[0]["role"] == "user"
        assert items[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_phase_session_does_not_mutate_sqlalchemy_history(self):
        session = _make_session("no-mutate")
        await session.add_items([{"role": "user", "content": "stored"}])

        history = await session.get_items()
        ctx = PhaseSession("no-mutate-test", inherited_history=history)
        await ctx.add_items([{"role": "assistant", "content": "phase-only"}])

        # The underlying SQLAlchemy-backed Session must remain untouched.
        upstream = await session.get_items()
        assert len(upstream) == 1
        assert upstream[0]["content"] == "stored"


class TestRunnerAcceptsSqlalchemySession:
    """af.Runner accepts SQLAlchemySession in its `session=` injection slot."""

    @pytest.mark.asyncio
    async def test_runner_with_sqlalchemy_session_runs_flow(self):
        """A flow that doesn't invoke an agent still threads the session
        through Runner without raising — confirming the type is accepted.
        """
        session = _make_session("runner")

        async def flow(msg: str) -> str:
            return f"echo: {msg}"

        runner = Runner(flow=flow, session=session)
        result = await runner("hello")

        assert result == "echo: hello"
