"""Regression tests for AF's boundary contracts in ChatKit and phase().

These tests cover three contracts that previously broke at the seams:

P1a — Runner injection through ChatKit:
    `Runner` injects `(session, handler, default_run_config)` via contextvars.
    `run_with_chatkit_context` must delegate to `Runner.__call__` so the full
    contract reaches the flow, not just `current_session`.

P1b — `.snapshot()` read-only semantics in ChatKit streaming:
    `ExecutionSpec.execute()` resolves snapshot input as `(history_list, None)`.
    The ChatKit streaming path must consume the resolved values, not re-resolve
    via `spec.resolve_input()` (which ignores `is_snapshot` and would pass a
    writable `PhaseSession`).

P2a — `phase()` cleanup wins over display failures:
    Even if the `PhaseStarted` handler emit (or ChatKit emit) raises, the
    contextvars `current_in_phase`, `current_phase_session`, and
    `current_phase_session_history` must reset before the exception
    propagates.

All tests are offline (no real LLM calls). They use unittest.mock fakes and
direct contextvar manipulation.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from agents import RunConfig

import agentic_flow as af
from agentic_flow import Agent, Runner, phase
from agentic_flow.agent import (
    current_handler,
    current_phase_session,
    current_run_config,
    current_session,
)
from agentic_flow.chatkit import (
    ChatKitExecutionContext,
    current_chatkit_context,
    run_with_chatkit_context,
)
from agentic_flow.phase import (
    PhaseSession,
    current_in_phase,
    current_phase_session_history,
)


def _make_thread():
    """Build a minimal ChatKit ThreadMetadata for tests."""
    from chatkit.types import ThreadMetadata

    return ThreadMetadata(id="thr_test", created_at=datetime.now())


def _make_store():
    """Build a fake Store with the methods exercised by ChatKit emission paths."""
    store = MagicMock()
    store.generate_item_id = MagicMock(return_value="item_test")
    store.add_thread_item = AsyncMock()
    return store


# =============================================================================
# P1a — Runner injection through ChatKit
# =============================================================================


class TestRunnerInjectionThroughChatKit:
    """run_with_chatkit_context must surface Runner's full injection contract."""

    @pytest.mark.asyncio
    async def test_chatkit_path_injects_handler_and_run_config(self):
        """Inside ChatKit, the flow sees current_handler and current_run_config
        from `Runner(handler=..., default_run_config=...)`, not just session."""
        captured: dict = {}

        def my_handler(event):
            return None

        my_run_config = RunConfig(tracing_disabled=True)
        my_session_obj = MagicMock(name="session")

        async def flow(msg: str) -> str:
            captured["handler"] = current_handler.get()
            captured["run_config"] = current_run_config.get()
            captured["session"] = current_session.get()
            captured["chatkit_ctx"] = current_chatkit_context.get()
            return "ok"

        runner = Runner(
            flow=flow,
            session=my_session_obj,
            handler=my_handler,
            default_run_config=my_run_config,
        )

        async for _event in run_with_chatkit_context(
            runner, _make_thread(), _make_store(), {}, "user message"
        ):
            pass

        assert captured["handler"] is my_handler, "Runner.handler must be injected in ChatKit path"
        assert captured["run_config"] is my_run_config, (
            "Runner.default_run_config must be injected in ChatKit path"
        )
        assert captured["session"] is my_session_obj, (
            "Runner.session must be injected in ChatKit path"
        )
        assert captured["chatkit_ctx"] is not None, (
            "ChatKit context must be set during ChatKit execution"
        )

    @pytest.mark.asyncio
    async def test_chatkit_path_resets_contextvars_on_exit(self):
        """After run_with_chatkit_context returns, only the ChatKit contextvar
        is touched at the outer level — Runner's contextvars are scoped inside
        Runner.__call__ and reset by it."""

        async def flow(msg: str) -> str:
            return "ok"

        runner = Runner(
            flow=flow,
            session=MagicMock(name="session"),
            handler=lambda e: None,
            default_run_config=RunConfig(tracing_disabled=True),
        )

        # Sanity: contextvars are unset before
        assert current_handler.get() is None
        assert current_run_config.get() is None
        assert current_session.get() is None
        assert current_chatkit_context.get() is None

        async for _event in run_with_chatkit_context(
            runner, _make_thread(), _make_store(), {}, "user message"
        ):
            pass

        # All contextvars are reset after the generator finishes
        assert current_handler.get() is None
        assert current_run_config.get() is None
        assert current_session.get() is None
        assert current_chatkit_context.get() is None


# =============================================================================
# P1b — .snapshot() in ChatKit streaming
# =============================================================================


class TestSnapshotInChatKitStreaming:
    """ExecutionSpec.execute_streaming must hand ChatKit the snapshot-resolved
    (input_data, session=None), not let ChatKit re-resolve via resolve_input."""

    @pytest.mark.asyncio
    async def test_chatkit_execute_spec_signature_accepts_resolved_pair(self):
        """ChatKitExecutionContext.execute_spec takes (spec, input_data, session)
        so the caller can inject snapshot-resolved values."""
        import inspect

        sig = inspect.signature(ChatKitExecutionContext.execute_spec)
        params = list(sig.parameters.keys())
        assert params == ["self", "spec", "input_data", "session"], (
            f"execute_spec must accept resolved (input_data, session); got {params}"
        )

    @pytest.mark.asyncio
    async def test_streaming_with_snapshot_passes_session_none_to_chatkit(self):
        """When ExecutionSpec.execute() runs with is_snapshot+is_streaming and
        ChatKit context is active, ChatKit receives session=None — preserving
        read-only semantics under concurrency."""
        captured: dict = {}

        # Stub ChatKit ctx that records what execute_spec receives.
        ctx = ChatKitExecutionContext.__new__(ChatKitExecutionContext)

        async def fake_execute_spec(spec, input_data, session):
            captured["input_data"] = input_data
            captured["session"] = session
            return "stub-output"

        ctx.execute_spec = fake_execute_spec  # type: ignore[method-assign]

        # Set up phase + ChatKit context manually (no real LLM).
        phase_session = PhaseSession(
            "test", inherited_history=[{"role": "user", "content": "history"}]
        )
        ps_token = current_phase_session.set(phase_session)
        in_phase_token = current_in_phase.set(True)
        chatkit_token = current_chatkit_context.set(ctx)

        try:
            agent = Agent(name="t", instructions="t", model="gpt-5.5")
            spec = agent("new prompt").snapshot().stream()

            result = await spec
            assert result == "stub-output"

            assert captured["session"] is None, (
                ".snapshot() must pass session=None to ChatKit (no writes back to PhaseSession)"
            )
            # input_data is a list of history + new user message
            assert isinstance(captured["input_data"], list)
            assert len(captured["input_data"]) == 2

            # PhaseSession.items must remain empty — snapshot wrote nothing.
            assert phase_session.items == [], (
                "PhaseSession.items must not be modified by snapshot+stream"
            )
        finally:
            current_chatkit_context.reset(chatkit_token)
            current_in_phase.reset(in_phase_token)
            current_phase_session.reset(ps_token)


# =============================================================================
# P2a — phase() cleanup wins over display failures
# =============================================================================


class TestPhaseCleanupWinsOverDisplayFailures:
    """phase() must reset contextvars even if PhaseStarted handler or ChatKit
    emit_phase_label raises."""

    @pytest.mark.asyncio
    async def test_handler_raises_on_phase_started_does_not_leak_contextvars(self):
        """If the handler raises while emitting PhaseStarted, the exception
        propagates but current_in_phase, current_phase_session, and
        current_phase_session_history are still reset."""

        def angry_handler(event):
            from agentic_flow.types import PhaseStarted

            if isinstance(event, PhaseStarted):
                raise RuntimeError("handler refused PhaseStarted")

        token = current_handler.set(angry_handler)
        try:
            assert current_in_phase.get() is False
            assert current_phase_session.get() is None

            with pytest.raises(RuntimeError, match="refused PhaseStarted"):
                async with phase("Risky"):
                    pytest.fail("phase body should not execute")  # pragma: no cover

            # Critical: contextvars are clean despite the raised emit.
            assert current_in_phase.get() is False, (
                "current_in_phase must reset even when PhaseStarted emit raises"
            )
            assert current_phase_session.get() is None, (
                "current_phase_session must reset even when PhaseStarted emit raises"
            )
            assert current_phase_session_history.get() is None, (
                "current_phase_session_history must reset for share_context=False too"
            )
        finally:
            current_handler.reset(token)

    @pytest.mark.asyncio
    async def test_share_context_false_handler_raise_resets_history_var(self):
        """share_context=False sets current_phase_session_history;
        it must reset even if PhaseStarted emit raises."""

        def angry_handler(event):
            from agentic_flow.types import PhaseStarted

            if isinstance(event, PhaseStarted):
                raise RuntimeError("boom")

        h_token = current_handler.set(angry_handler)
        try:
            with pytest.raises(RuntimeError, match="boom"):
                async with phase("X", share_context=False):
                    pytest.fail("phase body should not execute")  # pragma: no cover

            assert current_phase_session_history.get() is None
            assert current_in_phase.get() is False
        finally:
            current_handler.reset(h_token)

    @pytest.mark.asyncio
    async def test_chatkit_emit_phase_label_raise_does_not_leak_contextvars(self):
        """If ChatKit emit_phase_label raises, phase contextvars still reset."""

        ctx = ChatKitExecutionContext.__new__(ChatKitExecutionContext)
        ctx.emit_phase_label = AsyncMock(side_effect=RuntimeError("emit failed"))
        ctx.close_workflow = AsyncMock()

        ck_token = current_chatkit_context.set(ctx)
        try:
            with pytest.raises(RuntimeError, match="emit failed"):
                async with phase("Risky"):
                    pytest.fail("phase body should not execute")  # pragma: no cover

            assert current_in_phase.get() is False
            assert current_phase_session.get() is None
        finally:
            current_chatkit_context.reset(ck_token)

    @pytest.mark.asyncio
    async def test_user_exception_in_phase_body_still_resets(self):
        """Existing behavior: a user exception inside the phase body still
        resets contextvars and runs persist/PhaseEnded paths."""

        with pytest.raises(ValueError, match="user error"):
            async with phase("Body"):
                assert current_in_phase.get() is True
                raise ValueError("user error")

        assert current_in_phase.get() is False
        assert current_phase_session.get() is None


# =============================================================================
# Public API smoke
# =============================================================================


def test_run_with_chatkit_context_is_exposed_as_af_chatkit():
    """`af.chatkit.run_with_chatkit_context` is the documented entry point."""
    assert hasattr(af, "chatkit")
    assert af.chatkit.run_with_chatkit_context is run_with_chatkit_context
