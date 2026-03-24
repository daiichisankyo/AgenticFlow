"""Multi-provider pass-through tests.

These tests verify AF passes model configuration to the SDK unchanged.
"""

from __future__ import annotations

from agents import RunConfig
from agents.models.multi_provider import MultiProvider

import agentic_flow as af


class TestMultiProviderPassThrough:
    """Verify AF passes model configuration to SDK unchanged."""

    def test_prefix_model_in_agent(self):
        """Agent accepts prefixed model names for LiteLLM routing."""
        agent = af.Agent(
            name="claude",
            instructions="Reply OK",
            model="litellm/anthropic/claude-sonnet-4-20250514",
        )
        spec = agent("test")
        assert spec.sdk_agent.model == "litellm/anthropic/claude-sonnet-4-20250514"

    def test_run_config_model_override(self):
        """RunConfig model override flows through .run_config() modifier."""
        agent = af.Agent(name="test", instructions="OK", model="gpt-5.2")
        config = RunConfig(model="gpt-5.2")

        spec = agent("test").run_config(config)

        assert spec.run_kwargs.get("run_config") is config
        assert config.model == "gpt-5.2"

    def test_run_config_model_provider(self):
        """RunConfig model_provider flows through .run_config() modifier."""
        agent = af.Agent(name="test", instructions="OK", model="gpt-5.2")
        config = RunConfig(model_provider=MultiProvider())

        spec = agent("test").run_config(config)

        assert spec.run_kwargs.get("run_config") is config
        assert isinstance(config.model_provider, MultiProvider)

    def test_different_models_coexist(self):
        """Agents with different model prefixes coexist in same scope."""
        openai_agent = af.Agent(name="a", instructions="OK", model="gpt-5.2")
        claude_agent = af.Agent(
            name="b",
            instructions="OK",
            model="litellm/anthropic/claude-sonnet-4-20250514",
        )

        spec_a = openai_agent("test")
        spec_b = claude_agent("test")

        assert spec_a.sdk_agent.model == "gpt-5.2"
        assert spec_b.sdk_agent.model == "litellm/anthropic/claude-sonnet-4-20250514"
