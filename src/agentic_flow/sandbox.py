"""SandboxAgent - SDK SandboxAgent wrapper with callable form.

Design:
    Thin subclass of ``af.Agent``. Overrides ``build_sdk_agent`` to construct
    ``agents.sandbox.SandboxAgent`` (a subclass of ``agents.Agent``) instead of
    ``agents.Agent``. Returns the same ``ExecutionSpec[T]`` and supports the
    same modifier set (.stream/.silent/.snapshot/.isolated/.max_turns/.context/
    .run_config/.run_kwarg) as ``af.Agent`` — sandbox runtime configuration
    travels through the existing ``.run_config(...)`` modifier via
    ``RunConfig(sandbox=SandboxRunConfig(...))``.

    SandboxAgent-only kwargs (``default_manifest``, ``base_instructions``,
    ``capabilities``, ``run_as``) are accepted via ``**sdk_kwargs`` and passed
    verbatim to the SDK constructor — AF does not redefine or wrap them.

Example:
    import agentic_flow as af
    from agents import RunConfig
    from agents.sandbox import Manifest, SandboxRunConfig

    coder = af.SandboxAgent(
        name="coder",
        instructions="Implement the spec in Python.",
        model="gpt-5.5",
        default_manifest=Manifest(version="1", root="/work", entries=[]),
    )

    result = await coder("write hello.py").run_config(
        RunConfig(sandbox=SandboxRunConfig(...))
    ).stream()
"""

from __future__ import annotations

from typing import TypeVar

from agents import Agent as SDKAgent
from agents.sandbox import SandboxAgent as SDKSandboxAgent

from .agent import Agent

T = TypeVar("T")


class SandboxAgent(Agent[T]):
    """AF SandboxAgent - callable SDK SandboxAgent wrapper.

    Identical surface to ``af.Agent`` except that the underlying SDK object is
    ``agents.sandbox.SandboxAgent``, which adds 4 sandbox-specific kwargs on
    top of ``agents.Agent``: ``default_manifest``, ``base_instructions``,
    ``capabilities``, ``run_as``. These are accepted via ``**sdk_kwargs`` and
    forwarded verbatim — AF adds no new abstractions.

    All ExecutionSpec modifiers work unchanged. Sandbox runtime configuration
    (``SandboxRunConfig``) is supplied through the existing ``.run_config(...)``
    modifier as ``RunConfig(sandbox=...)``.

    Example:
        coder = SandboxAgent(
            name="coder",
            instructions="...",
            model="gpt-5.5",
            default_manifest=Manifest(...),
        )
        result: str = await coder("prompt").stream()
    """

    def build_sdk_agent(self) -> SDKAgent:
        """Create SDK SandboxAgent with pass-through kwargs."""
        kwargs = dict(self.sdk_kwargs)
        if self.output_type is not None:
            kwargs["output_type"] = self.output_type
        return SDKSandboxAgent(**kwargs)
