"""Event types for AF v0.35."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from agents import StreamEvent

# Forward declaration for type alias (actual classes defined below)
# Event is the union of all possible events that a Handler may receive:
# - StreamEvent: SDK streaming events (delta, tool calls, etc.)
# - PhaseStarted: Emitted when entering a phase
# - PhaseEnded: Emitted when exiting a phase
# - AgentResult: Emitted when non-streaming agent execution completes


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
    """Emitted when agent execution completes (non-streaming).

    Streaming execution emits SDK events directly.
    Non-streaming execution emits this event to notify UI of the result.
    """

    type: Literal["agent.result"] = "agent.result"
    content: Any = None
    ts: float = field(default_factory=time.time)


# Event union type: all possible events that a Handler may receive
Event = StreamEvent | PhaseStarted | PhaseEnded | AgentResult

# Handler type: receives any Event type
# - StreamEvent: SDK streaming events (delta, tool calls, reasoning, etc.)
# - PhaseStarted/PhaseEnded: phase boundary events
# - AgentResult: non-streaming execution result
Handler = Callable[[Event], Any]
