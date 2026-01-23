"""Utility helpers for AF.

These helpers create SDK objects without violating SDK pass-through principle.
They return standard SDK types that can be passed to Agent.
"""

from __future__ import annotations

from typing import Any, Literal

from agents import ModelSettings
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel

ReasoningEffort = Literal["low", "medium", "high"]


def serialize_output(output: Any) -> str:
    """Serialize agent output to string.

    Handles str, Pydantic models, and other types consistently.

    Args:
        output: Agent output (str, BaseModel, or other)

    Returns:
        String representation of the output
    """
    if isinstance(output, str):
        return output
    elif isinstance(output, BaseModel):
        return output.model_dump_json()
    else:
        return str(output)


def reasoning(
    effort: ReasoningEffort = "medium",
    summary: Literal["auto", "concise", "detailed"] = "auto",
    **model_settings_kwargs: Any,
) -> ModelSettings:
    """Create ModelSettings with reasoning enabled.

    Convenience helper that returns a standard SDK ModelSettings object.
    Does NOT violate SDK pass-through principle - Agent receives ModelSettings directly.

    Args:
        effort: Reasoning effort level ("low", "medium", "high")
        summary: Summary style ("auto", "concise", "detailed")
        **model_settings_kwargs: Additional ModelSettings parameters

    Returns:
        ModelSettings configured with reasoning

    Example:
        from agentic_flow import Agent, reasoning

        # Simple usage
        agent = Agent(
            name="thinker",
            instructions="Think step by step.",
            model="o3",
            model_settings=reasoning("high"),
        )

        # With additional settings
        agent = Agent(
            name="thinker",
            instructions="...",
            model_settings=reasoning("medium", store=True),
        )
    """
    return ModelSettings(
        reasoning=Reasoning(effort=effort, summary=summary),
        **model_settings_kwargs,
    )
