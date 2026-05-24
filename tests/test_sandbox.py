"""Tests for af.SandboxAgent (SDK 0.14 refresh).

Covers:
- Construction with base Agent kwargs and SandboxAgent-only kwargs
  (default_manifest, base_instructions, capabilities, run_as).
- sdk_agent type: agents.sandbox.SandboxAgent and IS-A agents.Agent.
- ExecutionSpec return shape (Call-Spec discipline preserved).
- All ExecutionSpec modifiers chain correctly off SandboxAgent.
- SandboxRunConfig travels via RunConfig(sandbox=...) and .run_config().
- output_type (Pydantic) works exactly like on af.Agent.
- Public API surface: af.SandboxAgent exists and is in __all__.

These tests do not perform any real LLM calls. They exercise construction
and spec-building only, mirroring the unit-test patterns in
tests/test_execution_spec_modifiers.py.
"""

from __future__ import annotations

import agents
import agents.sandbox
import pytest
from agents import RunConfig
from agents.sandbox import Manifest, SandboxRunConfig
from pydantic import BaseModel

import agentic_flow as af
from agentic_flow import ExecutionSpec, SandboxAgent


class Sentiment(BaseModel):
    """Pydantic output model for output_type tests."""

    mood: str
    confidence: float


def _minimal_manifest() -> Manifest:
    """Build a minimal valid Manifest for construction tests."""
    return Manifest(version=1, root="/work", entries={})


# =============================================================================
# Public API surface
# =============================================================================


class TestPublicApiSurface:
    """7. af.SandboxAgent is part of the public API."""

    def test_sandbox_agent_attribute_on_package(self):
        """`af.SandboxAgent` is accessible after `import agentic_flow as af`."""
        assert hasattr(af, "SandboxAgent")
        assert af.SandboxAgent is SandboxAgent

    def test_sandbox_agent_in_dunder_all(self):
        """`SandboxAgent` is exported via __all__."""
        assert "SandboxAgent" in af.__all__


# =============================================================================
# Construction
# =============================================================================


class TestSandboxAgentConstruction:
    """1. Instantiation with base Agent kwargs and SandboxAgent-only kwargs."""

    def test_construction_with_base_agent_kwargs(self):
        """Basic Agent kwargs (name, instructions, model) are accepted."""
        agent = SandboxAgent(
            name="coder",
            instructions="Implement the spec.",
            model="gpt-5.5",
        )

        assert agent.sdk_kwargs.get("name") == "coder"
        assert agent.sdk_kwargs.get("instructions") == "Implement the spec."
        assert agent.sdk_kwargs.get("model") == "gpt-5.5"

    def test_construction_with_default_manifest(self):
        """SandboxAgent-only kwarg `default_manifest` is accepted."""
        manifest = _minimal_manifest()
        agent = SandboxAgent(
            name="coder",
            instructions="Implement the spec.",
            model="gpt-5.5",
            default_manifest=manifest,
        )

        assert agent.sdk_kwargs.get("default_manifest") is manifest

    def test_construction_with_base_instructions(self):
        """SandboxAgent-only kwarg `base_instructions` is accepted."""
        agent = SandboxAgent(
            name="coder",
            instructions="Implement the spec.",
            model="gpt-5.5",
            base_instructions="You are a sandboxed coding agent.",
        )

        assert agent.sdk_kwargs.get("base_instructions") == ("You are a sandboxed coding agent.")

    def test_construction_with_capabilities(self):
        """SandboxAgent-only kwarg `capabilities` is accepted (empty sequence)."""
        agent = SandboxAgent(
            name="coder",
            instructions="Implement the spec.",
            model="gpt-5.5",
            capabilities=[],
        )

        assert agent.sdk_kwargs.get("capabilities") == []

    def test_construction_with_run_as(self):
        """SandboxAgent-only kwarg `run_as` is accepted (string form)."""
        agent = SandboxAgent(
            name="coder",
            instructions="Implement the spec.",
            model="gpt-5.5",
            run_as="root",
        )

        assert agent.sdk_kwargs.get("run_as") == "root"

    def test_construction_with_all_sandbox_kwargs(self):
        """All four SandboxAgent-only kwargs accepted together."""
        manifest = _minimal_manifest()
        agent = SandboxAgent(
            name="coder",
            instructions="Implement the spec.",
            model="gpt-5.5",
            default_manifest=manifest,
            base_instructions="Sandboxed coder.",
            capabilities=[],
            run_as="root",
        )

        assert agent.sdk_kwargs.get("default_manifest") is manifest
        assert agent.sdk_kwargs.get("base_instructions") == "Sandboxed coder."
        assert agent.sdk_kwargs.get("capabilities") == []
        assert agent.sdk_kwargs.get("run_as") == "root"


# =============================================================================
# sdk_agent type
# =============================================================================


class TestSdkAgentType:
    """2. sdk_agent is the SDK SandboxAgent and inherits agents.Agent."""

    def test_sdk_agent_is_sdk_sandbox_agent(self):
        """`sandbox_agent.sdk_agent` is an `agents.sandbox.SandboxAgent`."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")

        assert isinstance(agent.sdk_agent, agents.sandbox.SandboxAgent)

    def test_sdk_agent_is_also_sdk_agent(self):
        """SandboxAgent subclasses agents.Agent (IS-A relationship)."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")

        assert isinstance(agent.sdk_agent, agents.Agent)


# =============================================================================
# ExecutionSpec return (Call-Spec discipline)
# =============================================================================


class TestSandboxAgentReturnsExecutionSpec:
    """3. Calling a SandboxAgent returns an ExecutionSpec, not a result."""

    def test_call_returns_execution_spec(self):
        """`sandbox_agent('prompt')` returns an ExecutionSpec (not executed)."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")

        spec = agent("write hello.py")

        assert isinstance(spec, ExecutionSpec)
        assert spec.input == "write hello.py"
        assert spec.is_streaming is False

    def test_spec_sdk_agent_is_same_reference(self):
        """`spec.sdk_agent` is the same object as `sandbox_agent.sdk_agent`."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")

        spec = agent("write hello.py")

        assert spec.sdk_agent is agent.sdk_agent


# =============================================================================
# All existing modifiers chain through unchanged
# =============================================================================


class TestSandboxAgentModifierChain:
    """4. All ExecutionSpec modifiers work on SandboxAgent."""

    def _agent(self) -> SandboxAgent:
        return SandboxAgent(name="coder", instructions="...", model="gpt-5.5")

    def test_stream_modifier(self):
        spec = self._agent()("prompt").stream()

        assert isinstance(spec, ExecutionSpec)
        assert spec.is_streaming is True

    def test_silent_modifier(self):
        spec = self._agent()("prompt").silent()

        assert isinstance(spec, ExecutionSpec)
        assert spec.is_silent is True

    def test_snapshot_modifier(self):
        spec = self._agent()("prompt").snapshot()

        assert isinstance(spec, ExecutionSpec)
        assert spec.is_snapshot is True

    def test_isolated_modifier(self):
        spec = self._agent()("prompt").isolated()

        assert isinstance(spec, ExecutionSpec)
        assert spec.is_isolated is True

    def test_max_turns_modifier(self):
        spec = self._agent()("prompt").max_turns(5)

        assert isinstance(spec, ExecutionSpec)
        assert spec.max_turns_limit == 5

    def test_context_modifier(self):
        ctx = {"user_id": "u1"}
        spec = self._agent()("prompt").context(ctx)

        assert isinstance(spec, ExecutionSpec)
        assert spec.run_kwargs.get("context") is ctx

    def test_run_config_modifier(self):
        rc = RunConfig()
        spec = self._agent()("prompt").run_config(rc)

        assert isinstance(spec, ExecutionSpec)
        assert spec.run_kwargs.get("run_config") is rc

    def test_run_kwarg_modifier(self):
        spec = self._agent()("prompt").run_kwarg(previous_response_id="resp_abc")

        assert isinstance(spec, ExecutionSpec)
        assert spec.run_kwargs.get("previous_response_id") == "resp_abc"

    def test_full_modifier_chain(self):
        """All modifiers chain together; result is a single ExecutionSpec."""
        ctx = {"user_id": "u1"}
        rc = RunConfig()

        spec = (
            self._agent()("prompt")
            .stream()
            .silent()
            .snapshot()
            .isolated()
            .max_turns(5)
            .context(ctx)
            .run_config(rc)
            .run_kwarg(previous_response_id="resp_abc")
        )

        assert isinstance(spec, ExecutionSpec)
        assert spec.is_streaming is True
        assert spec.is_silent is True
        assert spec.is_snapshot is True
        assert spec.is_isolated is True
        assert spec.max_turns_limit == 5
        assert spec.run_kwargs.get("context") is ctx
        assert spec.run_kwargs.get("run_config") is rc
        assert spec.run_kwargs.get("previous_response_id") == "resp_abc"


# =============================================================================
# SandboxRunConfig pass-through
# =============================================================================


class TestSandboxRunConfigPassThrough:
    """5. SandboxRunConfig travels through RunConfig.sandbox via .run_config()."""

    def test_run_config_with_sandbox_run_config(self):
        """RunConfig(sandbox=SandboxRunConfig()) is accepted by .run_config()."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")
        sandbox_rc = SandboxRunConfig()

        spec = agent("prompt").run_config(RunConfig(sandbox=sandbox_rc))

        assert isinstance(spec, ExecutionSpec)
        assert "run_config" in spec.run_kwargs

    def test_sandbox_run_config_reachable_through_spec(self):
        """spec.run_kwargs['run_config'].sandbox is a SandboxRunConfig instance."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")

        spec = agent("prompt").run_config(RunConfig(sandbox=SandboxRunConfig()))

        run_config = spec.run_kwargs["run_config"]
        assert isinstance(run_config.sandbox, SandboxRunConfig)


# =============================================================================
# output_type (Pydantic) parity with af.Agent
# =============================================================================


class TestSandboxAgentOutputType:
    """6. output_type works on SandboxAgent the same as on Agent."""

    def test_default_output_type_is_none(self):
        """Without output_type, the attribute is None (T = str)."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")

        assert agent.output_type is None

    def test_pydantic_output_type_is_recorded(self):
        """output_type=SomePydanticModel is stored and forwarded to SDK."""
        agent = SandboxAgent(
            name="coder",
            instructions="Return sentiment.",
            model="gpt-5.5",
            output_type=Sentiment,
        )

        assert agent.output_type is Sentiment
        assert agent.sdk_agent.output_type is Sentiment

    def test_pydantic_output_type_call_returns_execution_spec(self):
        """SandboxAgent with output_type still returns an ExecutionSpec on call."""
        agent = SandboxAgent(
            name="coder",
            instructions="Return sentiment.",
            model="gpt-5.5",
            output_type=Sentiment,
        )

        spec = agent("Analyze this text")

        assert isinstance(spec, ExecutionSpec)
        assert spec.input == "Analyze this text"


# =============================================================================
# Runner-injected SandboxRunConfig (Plan B path)
# =============================================================================


class TestSandboxRunConfigViaRunnerInjection:
    """6. SandboxRunConfig can also travel via Runner(default_run_config=...).

    Plan B: Flow body does not need to repeat RunConfig(sandbox=...) on every
    call. Runner sets current_run_config contextvar; ExecutionSpec.build_run_kwargs
    resolves it when no .run_config() modifier is applied. Per-call modifier
    still wins when present.
    """

    @pytest.mark.asyncio
    async def test_sandbox_run_config_reaches_build_kwargs_via_runner_default(self):
        """Runner(default_run_config=RunConfig(sandbox=...)) flows into build_run_kwargs."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")
        sandbox_rc = SandboxRunConfig()
        run_config = RunConfig(sandbox=sandbox_rc)

        captured: dict = {}

        async def flow(msg: str) -> str:
            spec = agent(msg)
            captured.update(spec.build_run_kwargs(session=None))
            return "ok"

        runner = af.Runner(flow=flow, default_run_config=run_config)
        await runner("prompt")

        assert captured.get("run_config") is run_config
        assert captured["run_config"].sandbox is sandbox_rc

    @pytest.mark.asyncio
    async def test_per_call_run_config_overrides_runner_default_for_sandbox(self):
        """When call uses .run_config(...), it overrides Runner default."""
        agent = SandboxAgent(name="coder", instructions="...", model="gpt-5.5")

        runner_rc = RunConfig(sandbox=SandboxRunConfig())
        per_call_rc = RunConfig(sandbox=SandboxRunConfig())

        captured: dict = {}

        async def flow(msg: str) -> str:
            spec = agent(msg).run_config(per_call_rc)
            captured.update(spec.build_run_kwargs(session=None))
            return "ok"

        runner = af.Runner(flow=flow, default_run_config=runner_rc)
        await runner("prompt")

        assert captured.get("run_config") is per_call_rc
        assert captured.get("run_config") is not runner_rc


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
