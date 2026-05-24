"""Event types for AF."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class PhaseStarted:
    """Emitted when entering a phase."""

    type: Literal["phase.started"] = "phase.started"
    label: str = ""
    ts: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class PhaseEnded:
    """Emitted when exiting a phase."""

    type: Literal["phase.ended"] = "phase.ended"
    label: str = ""
    elapsed_ms: int = 0
    ts: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Emitted when agent execution completes (full text, once).

    Both streaming and non-streaming paths emit this event with the full output.
    Display is always full-text-at-once; .stream() controls internal execution mode only.
    """

    type: Literal["agent.result"] = "agent.result"
    content: Any = None
    ts: float = field(default_factory=time.time)


Event = PhaseStarted | PhaseEnded | AgentResult

# Handler type: callback for AF events
Handler = Callable[[Event], Any]
