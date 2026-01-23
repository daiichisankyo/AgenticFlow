"""Agent - SDK Agent wrapper with callable form.

Design:
    agent(prompt) returns ExecutionSpec[T] (not executed yet)
    await executes -> T

    Modifiers (5-axis model):
    - WHERE: .isolated() - No Session/PhaseSession
    - HOW: .stream(), .silent() - Streaming, UI suppression
    - LIMITS: .max_turns(n) - Execution constraints
    - SDK: .run_config(), .context(), .run_kwarg() - Pass-through

    T is determined by Agent's output_type:
    - output_type=None -> T = str
    - output_type=SomeModel -> T = SomeModel (Pydantic)
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from agents import Agent as SDKAgent
from agents import Runner

if TYPE_CHECKING:
    from agents import Session

    from .phase import PhaseSession
    from .types import Handler

T = TypeVar("T")


current_handler: ContextVar[Handler | None] = ContextVar("current_handler", default=None)
current_session: ContextVar[Session | None] = ContextVar("current_session", default=None)
current_phase_session: ContextVar[PhaseSession | None] = ContextVar(
    "current_phase_session", default=None
)


@dataclass(eq=False)
class ExecutionSpec(Generic[T]):
    """Awaitable execution specification.

    agent(prompt) returns this. Not executed until awaited.
    Returns T where T is determined by Agent's output_type.

    Modifiers (5-axis model):
        WHERE: .isolated() - No Session/PhaseSession
        HOW: .stream(), .silent() - Streaming, UI suppression
        LIMITS: .max_turns(n) - Execution constraints
        SDK: .run_config(), .context(), .run_kwarg()

    Example:
        # Basic
        result = await agent("prompt")
        result = await agent("prompt").stream()

        # With modifiers
        result = await agent("prompt").max_turns(5).stream()
        result = await agent("prompt").run_config(RunConfig(...))
        result = await agent("prompt").context(my_context).stream()
    """

    sdk_agent: SDKAgent
    input: str = ""
    streaming: bool = False
    is_isolated: bool = False
    is_silent: bool = False
    max_turns_sdk: int | None = None
    run_kwargs: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash by object identity for asyncio.gather() compatibility."""
        return id(self)

    def stream(self) -> ExecutionSpec[T]:
        """Enable streaming mode. Execution occurs when this spec is awaited."""
        return replace(self, streaming=True)

    def max_turns(self, max_turns: int) -> ExecutionSpec[T]:
        """Set max_turns for this execution."""
        return replace(self, max_turns_sdk=max_turns)

    def silent(self) -> ExecutionSpec[T]:
        """Enable silent mode. Suppresses UI display only.

        This modifier ONLY affects UI/handler event forwarding.
        It does NOT change WHERE data is written - that is determined by
        the execution context (phase vs global) and .isolated().

        Suppresses:
        - Handler event forwarding (no UI callback)
        - ChatKit event queue (no frontend display)

        Does NOT affect (these are controlled by other factors):
        - PhaseSession write: always happens in phase (silent or not)
        - Session write: controlled by execution context
        - Execution itself: agent runs normally, just not displayed

        Important context rules (independent of silent):
        - In phase: writes to PhaseSession, NOT parent Session
        - In phase(persist=True): last pair written to Session at phase end
        - Outside phase: writes to Session

        Use cases:
        - Background processing that shouldn't appear in UI
        - Internal tool calls that are implementation details
        """
        return replace(self, is_silent=True)

    def isolated(self) -> ExecutionSpec[T]:
        """Enable isolated mode. No Session read/write, no PhaseSession."""
        return replace(self, is_isolated=True)

    def run_config(self, run_config: Any) -> ExecutionSpec[T]:
        """Set RunConfig for this execution.

        RunConfig allows overriding execution settings like model, tracing, guardrails.
        This is an SDK pass-through modifier.

        Example:
            from agents import RunConfig

            result = await agent("prompt").run_config(
                RunConfig(tracing_disabled=True)
            )
        """
        new_kwargs = {**self.run_kwargs, "run_config": run_config}
        return replace(self, run_kwargs=new_kwargs)

    def context(self, context: Any) -> ExecutionSpec[T]:
        """Set context for dependency injection.

        Context is available in tools and hooks but NOT sent to the LLM.
        This is an SDK pass-through modifier.

        Example:
            @dataclass
            class AppContext:
                user_id: str
                db: Database

            ctx = AppContext(user_id="123", db=db)
            result = await agent("prompt").context(ctx)
        """
        new_kwargs = {**self.run_kwargs, "context": context}
        return replace(self, run_kwargs=new_kwargs)

    def run_kwarg(self, **kwargs: Any) -> ExecutionSpec[T]:
        """Set arbitrary SDK Runner.run() parameters.

        Use this for SDK parameters not covered by other modifiers.
        This is an SDK pass-through modifier.

        Example:
            result = await agent("prompt").run_kwarg(
                previous_response_id="resp_abc123",
                conversation_id="conv_xyz",
            )
        """
        new_kwargs = {**self.run_kwargs, **kwargs}
        return replace(self, run_kwargs=new_kwargs)

    def __await__(self):
        return self.execute().__await__()

    async def execute(self) -> T:
        """Execute the agent call. Returns T (str or Pydantic model)."""
        from .chatkit import current_chatkit_context

        input_data, session = self.resolve_input()

        if self.streaming:
            output = await self.execute_streaming(input_data, session)
        else:
            run_kwargs: dict = {"session": session, **self.run_kwargs}
            if self.max_turns_sdk is not None:
                run_kwargs["max_turns"] = self.max_turns_sdk
            result = await Runner.run(self.sdk_agent, input_data, **run_kwargs)
            output = result.final_output

            # Non-streaming UI: handler (CLI) and ChatKit are mutually exclusive in practice.
            # ChatKit mode uses run_with_chatkit_context() which ignores Runner.handler.
            if not self.is_silent:
                from .types import AgentResult

                handler = self.resolve_handler()
                event = AgentResult(content=output)

                if handler:
                    result = handler(event)
                    if hasattr(result, "__await__"):
                        await result

                chatkit_ctx = current_chatkit_context.get()
                if chatkit_ctx is not None:
                    await chatkit_ctx.emit_agent_result(output)

        # SDK handles session.add_items() automatically
        # No manual chat.append() needed

        return output

    async def execute_streaming(self, input_data: Any, session: Any) -> T:
        """Execute with streaming.

        When ChatKit context is active, uses ChatKitExecutionContext.execute_spec()
        to properly stream with workflow boundary management.
        Returns T (str or Pydantic model).

        When is_silent=True, events are not forwarded to handler.
        """
        from .chatkit import current_chatkit_context

        chatkit_ctx = current_chatkit_context.get()
        if chatkit_ctx is not None:
            return await chatkit_ctx.execute_spec(self)

        handler = self.resolve_handler() if not self.is_silent else None
        run_kwargs: dict = {"session": session, **self.run_kwargs}
        if self.max_turns_sdk is not None:
            run_kwargs["max_turns"] = self.max_turns_sdk
        stream = Runner.run_streamed(self.sdk_agent, input_data, **run_kwargs)

        async for event in stream.stream_events():
            if handler:
                result = handler(event)
                if hasattr(result, "__await__"):
                    await result

        return stream.final_output

    def resolve_input(self) -> tuple[Any, Any]:
        """Resolve input and session.

        Returns:
            (input_data, session) tuple

        Priority:
            1. isolated=True -> (input, None)
            2. PhaseSession -> (input, phase_session)
            3. share_context=False -> (list, None)
            4. Default -> (input, session)
        """
        if self.is_isolated:
            return self.input, None

        # Check for PhaseSession (share_context=True)
        phase_session = current_phase_session.get()
        if phase_session is not None:
            return self.input, phase_session

        # Check if we're inside a phase with share_context=False
        from .phase import current_in_phase, current_phase_session_history

        if current_in_phase.get():
            # share_context=False: read cached Session history, no write
            # Return as list (no session) to prevent SDK from writing
            cached_history = current_phase_session_history.get()
            if cached_history is not None:
                user_message = {
                    "role": "user",
                    "content": [{"type": "input_text", "text": self.input}],
                }
                messages = list(cached_history)
                messages.append(user_message)
                return messages, None
            return self.input, None

        # Default: use Runner's global Session
        session = current_session.get()
        return self.input, session

    def resolve_handler(self) -> Handler | None:
        """Resolve handler from current context."""
        return current_handler.get()


class Agent(Generic[T]):
    """AF Agent - callable SDK Agent wrapper.

    SDK Pass-through Design:
        All arguments are passed verbatim to agents.Agent.
        AF does NOT redefine, alias, or normalize SDK arguments.
        This ensures future SDK arguments work without AF changes.

    AF adds only:
        - Callable form: agent(prompt) -> ExecutionSpec[T]
        - Modifiers on ExecutionSpec (not on Agent):
          - WHERE: .isolated()
          - HOW: .stream(), .silent()
          - LIMITS: .max_turns(n)
          - SDK: .run_config(), .context(), .run_kwarg()

    Example:
        # Basic usage
        assistant = Agent(name="assistant", instructions="...", model="gpt-5.2")
        result: str = await assistant("Hello")

        # With modifiers
        result = await assistant("Hello").stream()
        result = await assistant("Hello").max_turns(5).stream()
        result = await assistant("Hello").run_config(RunConfig(...))

        # Pydantic output
        analyzer = Agent(name="analyzer", instructions="...", output_type=Analysis)
        result: Analysis = await analyzer("text")
    """

    @overload
    def __init__(
        self: Agent[str],
        *,
        output_type: None = None,
        **sdk_kwargs: Any,
    ) -> None: ...

    @overload
    def __init__(
        self: Agent[T],
        *,
        output_type: type[T],
        **sdk_kwargs: Any,
    ) -> None: ...

    def __init__(
        self,
        *,
        output_type: type[T] | None = None,
        **sdk_kwargs: Any,
    ) -> None:
        """Initialize Agent with SDK pass-through.

        Args:
            output_type: Pydantic model for structured output (determines T).
                         If None, T = str.
            **sdk_kwargs: All arguments passed verbatim to agents.Agent.
                          Common: name, instructions, model, model_settings,
                          tools, handoffs, etc.

        Note:
            AgenticFlow does NOT provide default values for SDK arguments.
            Use SDK defaults or specify explicitly.
        """
        self.output_type = output_type
        self.sdk_kwargs = sdk_kwargs
        self.sdk_agent = self.build_sdk_agent()

    def build_sdk_agent(self) -> SDKAgent:
        """Create SDK Agent with pass-through kwargs."""
        kwargs = dict(self.sdk_kwargs)
        if self.output_type is not None:
            kwargs["output_type"] = self.output_type
        return SDKAgent(**kwargs)

    def __call__(
        self,
        input: str,
    ) -> ExecutionSpec[T]:
        """Create ExecutionSpec[T] - callable form. Not executed yet."""
        return ExecutionSpec(
            sdk_agent=self.sdk_agent,
            input=input,
        )
