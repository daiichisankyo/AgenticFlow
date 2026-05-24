"""Tests for ExecutionSpec modifiers.

Comprehensive tests for all ExecutionSpec modifiers organized by axis:
- ExecutionSpec[T] type parameter
- WHERE axis: .isolated(), .snapshot()
- HOW axis: .stream(), .silent()
- LIMITS axis: .max_turns(n)
- SDK pass-through: .run_config(), .context(), .run_kwarg()
- run_config resolution priority (modifier > Runner contextvar > none)

These tests verify modifier behavior without API calls.
No mocks required - pure unit tests.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass

import pytest

from agentic_flow import Agent, ExecutionSpec
from tests.conftest import Analysis


@dataclass
class MockRunConfig:
    """Shared stand-in for `agents.RunConfig` across modifier unit tests.

    Each field is Optional so individual tests can set just the field they
    care about (model / workflow_name / tracing_disabled) without redefining
    the dataclass per test. Identity-based assertions (`is` checks) and
    field-value assertions both work as expected.
    """

    model: str | None = None
    workflow_name: str | None = None
    tracing_disabled: bool | None = None


class TestExecutionSpecTypeParameter:
    """Tests for ExecutionSpec[T] type parameter - docs example."""

    def test_str_output_type_annotation(self):
        """ExecutionSpec[str] for agent without output_type."""
        assistant = Agent(name="assistant", instructions="...", model="gpt-5.5")

        spec: ExecutionSpec[str] = assistant("Hello")

        assert isinstance(spec, ExecutionSpec)
        assert spec.input == "Hello"

    def test_pydantic_output_type_annotation(self):
        """ExecutionSpec[Analysis] for agent with output_type=Analysis."""
        analyzer = Agent(
            name="analyzer",
            instructions="...",
            output_type=Analysis,
            model="gpt-5.5",
        )

        spec: ExecutionSpec[Analysis] = analyzer("Analyze this text")

        assert isinstance(spec, ExecutionSpec)
        assert spec.input == "Analyze this text"

    def test_type_parameter_preserves_through_modifiers(self):
        """Type parameter T is preserved through modifier chain."""
        analyzer = Agent(
            name="analyzer",
            instructions="...",
            output_type=Analysis,
            model="gpt-5.5",
        )

        spec1: ExecutionSpec[Analysis] = analyzer("text")
        spec2: ExecutionSpec[Analysis] = spec1.stream()
        spec3: ExecutionSpec[Analysis] = spec2.silent()
        spec4: ExecutionSpec[Analysis] = spec3.isolated()
        spec5: ExecutionSpec[Analysis] = spec4.max_turns(5)

        assert all(isinstance(s, ExecutionSpec) for s in [spec1, spec2, spec3, spec4, spec5])


# =============================================================================
# WHERE Axis: .isolated()
# =============================================================================


class TestIsolated:
    """Tests for .isolated() modifier - WHERE axis."""

    def test_isolated_returns_new_spec(self):
        """isolated() returns a new ExecutionSpec."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")
        isolated_spec = spec.isolated()

        assert spec is not isolated_spec
        assert spec.is_isolated is False
        assert isolated_spec.is_isolated is True

    def test_isolated_preserves_other_fields(self):
        """isolated() preserves all other fields."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").stream().silent()
        isolated_spec = spec.isolated()

        assert isolated_spec.input == spec.input
        assert isolated_spec.sdk_agent is spec.sdk_agent
        assert isolated_spec.is_streaming is True
        assert isolated_spec.is_silent is True


class TestSnapshot:
    """Tests for .snapshot() modifier - WHERE axis."""

    def test_snapshot_returns_new_spec(self):
        """snapshot() returns a new ExecutionSpec with is_snapshot=True."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")
        snapshot_spec = spec.snapshot()

        assert spec is not snapshot_spec
        assert spec.is_snapshot is False
        assert snapshot_spec.is_snapshot is True

    def test_snapshot_preserves_other_fields(self):
        """snapshot() preserves all other fields."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").stream().silent()
        snapshot_spec = spec.snapshot()

        assert snapshot_spec.input == spec.input
        assert snapshot_spec.sdk_agent is spec.sdk_agent
        assert snapshot_spec.is_streaming is True
        assert snapshot_spec.is_silent is True


# =============================================================================
# HOW Axis: .stream(), .silent()
# =============================================================================


class TestStream:
    """Tests for .stream() modifier - HOW axis."""

    def test_stream_returns_new_spec(self):
        """stream() returns a new ExecutionSpec."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")
        stream_spec = spec.stream()

        assert spec is not stream_spec
        assert spec.is_streaming is False
        assert stream_spec.is_streaming is True

    def test_stream_preserves_other_fields(self):
        """stream() preserves all other fields."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").isolated().silent()
        stream_spec = spec.stream()

        assert stream_spec.input == spec.input
        assert stream_spec.sdk_agent is spec.sdk_agent
        assert stream_spec.is_isolated is True
        assert stream_spec.is_silent is True


class TestSilent:
    """Tests for .silent() modifier - HOW axis."""

    def test_silent_returns_new_spec(self):
        """silent() returns a new ExecutionSpec."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")
        silent_spec = spec.silent()

        assert spec is not silent_spec
        assert spec.is_silent is False
        assert silent_spec.is_silent is True

    def test_silent_preserves_other_fields(self):
        """silent() preserves all other fields."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").stream().isolated()
        silent_spec = spec.silent()

        assert silent_spec.input == spec.input
        assert silent_spec.sdk_agent is spec.sdk_agent
        assert silent_spec.is_streaming is True
        assert silent_spec.is_isolated is True


# =============================================================================
# LIMITS Axis: .max_turns()
# =============================================================================


class TestMaxTurns:
    """Tests for .max_turns() modifier - LIMITS axis."""

    def test_max_turns_returns_new_spec(self):
        """max_turns() returns a new ExecutionSpec."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")
        limited_spec = spec.max_turns(5)

        assert spec is not limited_spec
        assert spec.max_turns_limit is None
        assert limited_spec.max_turns_limit == 5

    def test_max_turns_preserves_other_fields(self):
        """max_turns() preserves all other fields."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").stream().silent()
        limited_spec = spec.max_turns(10)

        assert limited_spec.input == spec.input
        assert limited_spec.sdk_agent is spec.sdk_agent
        assert limited_spec.is_streaming is True
        assert limited_spec.is_silent is True

    def test_max_turns_chain_with_stream(self):
        """max_turns().stream() works."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").max_turns(5).stream()

        assert spec.max_turns_limit == 5
        assert spec.is_streaming is True

    def test_max_turns_chain_with_isolated(self):
        """max_turns().isolated() works."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").max_turns(3).isolated()

        assert spec.max_turns_limit == 3
        assert spec.is_isolated is True

    def test_max_turns_override(self):
        """Subsequent max_turns() overrides previous value."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").max_turns(5).max_turns(10)

        assert spec.max_turns_limit == 10


# =============================================================================
# SDK Pass-Through: .run_config(), .context(), .run_kwarg()
# =============================================================================


class TestRunConfig:
    """Tests for .run_config() modifier - SDK pass-through."""

    def test_run_config_returns_new_spec(self):
        """run_config() returns a new ExecutionSpec."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")

        config = MockRunConfig(tracing_disabled=True)
        configured_spec = spec.run_config(config)

        assert spec is not configured_spec
        assert "run_config" not in spec.run_kwargs
        assert configured_spec.run_kwargs.get("run_config") is config

    def test_run_config_preserves_other_fields(self):
        """run_config() preserves all other fields."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").stream().max_turns(5)

        configured_spec = spec.run_config(MockRunConfig(workflow_name="test"))

        assert configured_spec.input == spec.input
        assert configured_spec.is_streaming is True
        assert configured_spec.max_turns_limit == 5

    def test_run_config_chain_with_stream(self):
        """run_config().stream() works."""
        agent = Agent(name="test", instructions="test")

        spec = agent("prompt").run_config(MockRunConfig(model="gpt-5.5-turbo")).stream()

        assert "run_config" in spec.run_kwargs
        assert spec.is_streaming is True


class TestContext:
    """Tests for .context() modifier - SDK pass-through (DI)."""

    def test_context_returns_new_spec(self):
        """context() returns a new ExecutionSpec."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")

        @dataclass
        class AppContext:
            user_id: str
            api_key: str

        ctx = AppContext(user_id="123", api_key="secret")
        context_spec = spec.context(ctx)

        assert spec is not context_spec
        assert "context" not in spec.run_kwargs
        assert context_spec.run_kwargs.get("context") is ctx

    def test_context_preserves_other_fields(self):
        """context() preserves all other fields."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").isolated().silent()

        @dataclass
        class AppContext:
            db: str

        context_spec = spec.context(AppContext(db="postgres"))

        assert context_spec.input == spec.input
        assert context_spec.is_isolated is True
        assert context_spec.is_silent is True

    def test_context_chain_with_modifiers(self):
        """context() chains with other modifiers."""
        agent = Agent(name="test", instructions="test")

        @dataclass
        class AppContext:
            user_id: str

        spec = agent("prompt").context(AppContext("u1")).max_turns(5).stream()

        assert "context" in spec.run_kwargs
        assert spec.max_turns_limit == 5
        assert spec.is_streaming is True


class TestRunKwarg:
    """Tests for .run_kwarg() modifier - SDK pass-through (arbitrary)."""

    def test_run_kwarg_returns_new_spec(self):
        """run_kwarg() returns a new ExecutionSpec."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")
        kwarg_spec = spec.run_kwarg(previous_response_id="resp_abc123")

        assert spec is not kwarg_spec
        assert "previous_response_id" not in spec.run_kwargs
        assert kwarg_spec.run_kwargs.get("previous_response_id") == "resp_abc123"

    def test_run_kwarg_multiple_params(self):
        """run_kwarg() accepts multiple parameters."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").run_kwarg(
            previous_response_id="resp_abc",
            conversation_id="conv_xyz",
        )

        assert spec.run_kwargs.get("previous_response_id") == "resp_abc"
        assert spec.run_kwargs.get("conversation_id") == "conv_xyz"

    def test_run_kwarg_chain(self):
        """Multiple run_kwarg() calls accumulate."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").run_kwarg(param1="value1").run_kwarg(param2="value2")

        assert spec.run_kwargs.get("param1") == "value1"
        assert spec.run_kwargs.get("param2") == "value2"

    def test_run_kwarg_override(self):
        """Later run_kwarg() overrides earlier values."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt").run_kwarg(key="first").run_kwarg(key="second")

        assert spec.run_kwargs.get("key") == "second"


class TestModifierCombinations:
    """Tests for combining all modifier types."""

    def test_all_modifiers_combined(self):
        """All modifiers can be combined."""
        agent = Agent(name="test", instructions="test")

        @dataclass
        class AppContext:
            user_id: str

        spec = (
            agent("complex task")
            .max_turns(10)
            .context(AppContext("u123"))
            .run_config(MockRunConfig(tracing_disabled=True))
            .run_kwarg(custom_param="value")
            .stream()
            .silent()
            .isolated()
            .snapshot()
        )

        assert spec.max_turns_limit == 10
        assert spec.is_streaming is True
        assert spec.is_silent is True
        assert spec.is_isolated is True
        assert spec.is_snapshot is True
        assert "context" in spec.run_kwargs
        assert "run_config" in spec.run_kwargs
        assert spec.run_kwargs.get("custom_param") == "value"

    def test_modifier_order_independence(self):
        """Modifier order doesn't matter for final state."""
        agent = Agent(name="test", instructions="test")

        # Order 1
        spec1 = agent("p").stream().max_turns(5).isolated()

        # Order 2 (reversed)
        spec2 = agent("p").isolated().max_turns(5).stream()

        assert spec1.is_streaming == spec2.is_streaming
        assert spec1.max_turns_limit == spec2.max_turns_limit
        assert spec1.is_isolated == spec2.is_isolated

    def test_run_kwargs_accumulation(self):
        """run_kwargs accumulates across different calls."""
        agent = Agent(name="test", instructions="test")

        @dataclass
        class AppContext:
            user: str

        spec = (
            agent("prompt")
            .run_config(MockRunConfig(model="test"))
            .context(AppContext("u1"))
            .run_kwarg(extra="value")
        )

        assert "run_config" in spec.run_kwargs
        assert "context" in spec.run_kwargs
        assert spec.run_kwargs.get("extra") == "value"


# =============================================================================
# Call-Spec Discipline: Forbidden Forms
# =============================================================================


class TestForbiddenForms:
    """Verify modifiers follow Call-Spec discipline.

    From docs:
    - WHAT: prompt, instructions, tools, output_type -> Agent(...), agent(prompt)
    - WHERE: session, phase context, isolated -> phase(), .isolated()
    - HOW: streaming, display, handler -> .stream(), .silent(), Runner(handler=...)
    - LIMITS: max_turns -> .max_turns()
    - SDK: run_config, context -> .run_config(), .context(), .run_kwarg()
    """

    # Agent should NOT have modifier methods
    def test_agent_has_no_stream_method(self):
        """Agent does not have a stream() method."""
        agent = Agent(name="test", instructions="test")
        assert not hasattr(agent, "stream") or not callable(getattr(agent, "stream", None))

    def test_agent_has_no_silent_method(self):
        """Agent does not have a silent() method."""
        agent = Agent(name="test", instructions="test")
        assert not hasattr(agent, "silent") or not callable(getattr(agent, "silent", None))

    def test_agent_has_no_isolated_method(self):
        """Agent does not have an isolated() method."""
        agent = Agent(name="test", instructions="test")
        assert not hasattr(agent, "isolated") or not callable(getattr(agent, "isolated", None))

    def test_agent_has_no_max_turns(self):
        """Agent does not have max_turns() method."""
        agent = Agent(name="test", instructions="test")
        assert not hasattr(agent, "max_turns") or not callable(getattr(agent, "max_turns", None))

    def test_agent_has_no_run_config(self):
        """Agent does not have run_config() method."""
        agent = Agent(name="test", instructions="test")
        assert not hasattr(agent, "run_config") or not callable(getattr(agent, "run_config", None))

    def test_agent_has_no_context(self):
        """Agent does not have context() method."""
        agent = Agent(name="test", instructions="test")
        assert not hasattr(agent, "context") or not callable(getattr(agent, "context", None))

    def test_agent_has_no_run_kwarg(self):
        """Agent does not have run_kwarg() method."""
        agent = Agent(name="test", instructions="test")
        assert not hasattr(agent, "run_kwarg") or not callable(getattr(agent, "run_kwarg", None))

    def test_agent_has_no_snapshot_method(self):
        """Agent does not have a snapshot() method."""
        agent = Agent(name="test", instructions="test")
        assert not hasattr(agent, "snapshot") or not callable(getattr(agent, "snapshot", None))

    # Agent.__call__ should NOT accept modifier params
    def test_agent_call_has_no_stream_param(self):
        """Agent.__call__ does not accept stream parameter."""
        agent = Agent(name="test", instructions="test")
        params = list(inspect.signature(agent.__call__).parameters.keys())
        assert "stream" not in params

    def test_agent_call_has_no_silent_param(self):
        """Agent.__call__ does not accept silent parameter."""
        agent = Agent(name="test", instructions="test")
        params = list(inspect.signature(agent.__call__).parameters.keys())
        assert "silent" not in params

    def test_agent_call_has_no_isolated_param(self):
        """Agent.__call__ does not accept isolated parameter."""
        agent = Agent(name="test", instructions="test")
        params = list(inspect.signature(agent.__call__).parameters.keys())
        assert "isolated" not in params

    # ExecutionSpec modifiers should only accept self
    def test_execution_spec_stream_signature(self):
        """ExecutionSpec.stream() only accepts self."""
        params = list(inspect.signature(ExecutionSpec.stream).parameters.keys())
        assert params == ["self"]

    def test_execution_spec_silent_signature(self):
        """ExecutionSpec.silent() only accepts self."""
        params = list(inspect.signature(ExecutionSpec.silent).parameters.keys())
        assert params == ["self"]

    def test_execution_spec_isolated_signature(self):
        """ExecutionSpec.isolated() only accepts self."""
        params = list(inspect.signature(ExecutionSpec.isolated).parameters.keys())
        assert params == ["self"]

    def test_execution_spec_snapshot_signature(self):
        """ExecutionSpec.snapshot() only accepts self."""
        params = list(inspect.signature(ExecutionSpec.snapshot).parameters.keys())
        assert params == ["self"]

    def test_execution_spec_max_turns_signature(self):
        """ExecutionSpec.max_turns() has correct signature."""
        params = list(inspect.signature(ExecutionSpec.max_turns).parameters.keys())
        assert params == ["self", "max_turns"]

    def test_execution_spec_run_config_signature(self):
        """ExecutionSpec.run_config() has correct signature."""
        params = list(inspect.signature(ExecutionSpec.run_config).parameters.keys())
        assert params == ["self", "run_config"]

    def test_execution_spec_context_signature(self):
        """ExecutionSpec.context() has correct signature."""
        params = list(inspect.signature(ExecutionSpec.context).parameters.keys())
        assert params == ["self", "context"]

    def test_execution_spec_run_kwarg_signature(self):
        """ExecutionSpec.run_kwarg() accepts **kwargs."""
        params = list(inspect.signature(ExecutionSpec.run_kwarg).parameters.keys())
        assert "self" in params
        assert "kwargs" in params


class TestAntiPatterns:
    """Verify anti-patterns from docs are correctly rejected."""

    def test_agent_call_rejects_stream_param(self):
        """agent('prompt', stream=True) raises TypeError."""
        agent = Agent(name="test", instructions="test")

        with pytest.raises(TypeError):
            agent("prompt", stream=True)  # type: ignore

    def test_agent_call_rejects_isolated_param(self):
        """agent('prompt', isolated=True) raises TypeError."""
        agent = Agent(name="test", instructions="test")

        with pytest.raises(TypeError):
            agent("prompt", isolated=True)  # type: ignore

    def test_agent_call_rejects_silent_param(self):
        """agent('prompt', silent=True) raises TypeError."""
        agent = Agent(name="test", instructions="test")

        with pytest.raises(TypeError):
            agent("prompt", silent=True)  # type: ignore

    def test_agent_call_rejects_max_turns_param(self):
        """agent('prompt', max_turns=5) raises TypeError."""
        agent = Agent(name="test", instructions="test")

        with pytest.raises(TypeError):
            agent("prompt", max_turns=5)  # type: ignore

    def test_agent_call_rejects_snapshot_param(self):
        """agent('prompt', snapshot=True) raises TypeError."""
        agent = Agent(name="test", instructions="test")

        with pytest.raises(TypeError):
            agent("prompt", snapshot=True)  # type: ignore


class TestRunConfigVariants:
    """Tests for various RunConfig use cases from docs."""

    def test_run_config_with_model_override(self):
        """RunConfig with model override works."""
        agent = Agent(name="test", instructions="test")

        spec = agent("prompt").run_config(MockRunConfig(model="gpt-5.5-turbo"))

        assert spec.run_kwargs["run_config"].model == "gpt-5.5-turbo"

    def test_run_config_with_workflow_name(self):
        """RunConfig with workflow_name works."""
        agent = Agent(name="test", instructions="test")

        spec = agent("prompt").run_config(MockRunConfig(workflow_name="my_workflow"))

        assert spec.run_kwargs["run_config"].workflow_name == "my_workflow"

    def test_run_config_with_tracing_disabled(self):
        """RunConfig with tracing_disabled works."""
        agent = Agent(name="test", instructions="test")

        spec = agent("prompt").run_config(MockRunConfig(tracing_disabled=True))

        assert spec.run_kwargs["run_config"].tracing_disabled is True


class TestContextWithStream:
    """Tests for context() chained with stream()."""

    def test_context_then_stream(self):
        """context().stream() works."""
        agent = Agent(name="test", instructions="test")

        @dataclass
        class AppContext:
            user_id: str
            api_key: str
            logger: str  # Simplified for test

        ctx = AppContext(user_id="123", api_key="secret", logger="mock_logger")
        spec = agent("prompt").context(ctx).stream()

        assert spec.run_kwargs.get("context") is ctx
        assert spec.is_streaming is True

    def test_stream_then_context(self):
        """stream().context() works (order independence)."""
        agent = Agent(name="test", instructions="test")

        @dataclass
        class AppContext:
            user_id: str

        ctx = AppContext(user_id="456")
        spec = agent("prompt").stream().context(ctx)

        assert spec.run_kwargs.get("context") is ctx
        assert spec.is_streaming is True


class TestRunConfigResolution:
    """build_run_kwargs() resolves run_config in priority order:
    1. .run_config(...) modifier on this spec
    2. Runner-injected current_run_config contextvar
    3. SDK default (no run_config kwarg passed at all)
    """

    def test_modifier_run_config_used_when_present(self):
        """When .run_config() is set on spec, it is used as-is."""
        agent = Agent(name="test", instructions="test")

        rc = MockRunConfig(workflow_name="modifier")
        spec = agent("prompt").run_config(rc)
        kwargs = spec.build_run_kwargs(session=None)

        assert kwargs.get("run_config") is rc

    def test_contextvar_used_when_modifier_absent(self):
        """When .run_config() is not set, contextvar value is injected."""
        from agentic_flow.agent import current_run_config

        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")

        rc = MockRunConfig(workflow_name="contextvar")
        token = current_run_config.set(rc)
        try:
            kwargs = spec.build_run_kwargs(session=None)
        finally:
            current_run_config.reset(token)

        assert kwargs.get("run_config") is rc

    def test_modifier_overrides_contextvar(self):
        """When both modifier and contextvar are set, modifier wins."""
        from agentic_flow.agent import current_run_config

        agent = Agent(name="test", instructions="test")
        rc_modifier = MockRunConfig(workflow_name="modifier")
        rc_contextvar = MockRunConfig(workflow_name="contextvar")

        spec = agent("prompt").run_config(rc_modifier)

        token = current_run_config.set(rc_contextvar)
        try:
            kwargs = spec.build_run_kwargs(session=None)
        finally:
            current_run_config.reset(token)

        assert kwargs.get("run_config") is rc_modifier
        assert kwargs.get("run_config") is not rc_contextvar

    def test_no_modifier_no_contextvar_omits_kwarg(self):
        """Without modifier or contextvar, run_config is NOT passed to SDK."""
        agent = Agent(name="test", instructions="test")
        spec = agent("prompt")
        kwargs = spec.build_run_kwargs(session=None)

        assert "run_config" not in kwargs
