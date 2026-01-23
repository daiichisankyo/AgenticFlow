"""AF v0.35 - Pythonic agent workflows.

agent(prompt) returns an ExecutionSpec[T].
Execution happens only when the resulting spec is awaited (returns T).

Modifiers (organized by axis):
- WHERE: .isolated() - No Session/PhaseSession
- HOW: .stream(), .silent() - Streaming, UI suppression
- LIMITS: .max_turns(n) - Execution constraints
- SDK: .run_config(), .context(), .run_kwarg() - SDK pass-through

Key concepts:
- Phase: Internal thinking space (inherits Session, shares between Agents,
         NOT written to Session unless persist=True)
- Session: User conversation history (persistent, SDK handles read/write)
- phase(persist=True): Write last pair to Session at phase end

Example:
    from agentic_flow import Agent, Runner, phase
    from agents import SQLiteSession

    researcher = Agent(
        name="Researcher", instructions="Research topics.", model="gpt-5.2"
    )
    responder = Agent(
        name="Responder", instructions="Respond to user.", model="gpt-5.2"
    )

    async def flow(user_message: str) -> str:
        # Phase with persist=True: last pair written to Session at phase end
        async with phase("Research", persist=True):
            r1 = await researcher(user_message).stream()  # PhaseSession only
            r2 = await researcher("more details").stream()  # PhaseSession only
            return await responder(f"Result: {r2}").stream()  # Session at phase end

    chat = Runner(flow=flow, session=SQLiteSession("conv_123"))
    result = await chat("hello")
    # Session: [user: "more details", assistant: result] (last pair only)
    # (Research phase internal thinking is NOT in Session)

Context behavior:
    # Outside phase: SDK handles Session read/write
    await agent("prompt")  # Session updated by SDK

    # Inside phase (default): PhaseSession created, Session inherited
    async with phase("Research"):
        await agent("prompt")  # PhaseSession only, Session NOT written

    # Inside phase with persist=True: Last pair written to Session at phase end
    async with phase("Research", persist=True):
        await agent("prompt")  # Last pair -> Session at phase end

    # isolated(): No context at all
    await agent("prompt").isolated()  # No Session, no PhaseSession
"""

from .agent import Agent, ExecutionSpec
from .phase import PhaseSession, phase
from .runner import RunHandle, Runner
from .types import AgentResult, Event, Handler, PhaseEnded, PhaseStarted
from .utils import reasoning

__all__ = [
    "Agent",
    "ExecutionSpec",
    "Runner",
    "RunHandle",
    "phase",
    "PhaseSession",
    "Handler",
    "Event",
    "PhaseStarted",
    "PhaseEnded",
    "AgentResult",
    "reasoning",
]
