"""ChatKit integration for AF.

Integration pattern:
    run_with_chatkit_context(runner, thread, store, context, user_message)
    - Use with ChatKitServer subclass
    - Session support via Runner
    - See sample/guide/server.py for complete example

Workflow Boundary Design:
    ChatKit's stream_agent_response continues a workflow if the last store
    item is a workflow. To ensure each agent gets its own reasoning display,
    we create "workflow boundaries" by saving non-workflow items to store.

    The boundary is created by emit_phase_label() which saves a message to store
    before each agent execution. This ensures stream_agent_response sees a
    message (not a workflow) as the last item and creates a new workflow.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from contextvars import ContextVar
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from chatkit.agents import AgentContext
    from chatkit.store import Store
    from chatkit.types import ThreadMetadata, ThreadStreamEvent

    from .agent import ExecutionSpec
    from .runner import Runner


current_chatkit_context: ContextVar[ChatKitExecutionContext | None] = ContextVar(
    "current_chatkit_context", default=None
)


class ChatKitExecutionContext:
    """Context for ChatKit Server execution with full-text display.

    Manages:
    - Event queue for full-text result delivery to frontend
    - Workflow boundaries for multi-agent flows
    - Agent execution with full-text-at-once output semantics
    """

    def __init__(self, agent_context: AgentContext, store: Store):
        self.agent_context = agent_context
        self.store = store
        self.event_queue: asyncio.Queue[ThreadStreamEvent] = asyncio.Queue()

    @property
    def thread(self):
        return self.agent_context.thread

    async def emit_message(self, text: str) -> None:
        """Emit a text message to ChatKit store and push events."""
        from chatkit.types import (
            AssistantMessageContent,
            AssistantMessageItem,
            ThreadItemAddedEvent,
            ThreadItemDoneEvent,
        )

        item_id = self.store.generate_item_id("message", self.thread, {})
        item = AssistantMessageItem(
            id=item_id,
            thread_id=self.thread.id,
            created_at=datetime.now(),
            content=[AssistantMessageContent(type="output_text", text=text, annotations=[])],
        )
        await self.store.add_thread_item(self.thread.id, item, self.agent_context.request_context)
        await self.push_event(ThreadItemAddedEvent(type="thread.item.added", item=item))
        await self.push_event(ThreadItemDoneEvent(type="thread.item.done", item=item))

    async def emit_phase_label(self, label: str) -> None:
        """Emit a phase label to create workflow boundary.

        Saves a message to store before agent execution. This ensures
        stream_agent_response sees a message (not workflow) as last item
        and creates a new workflow for reasoning display.
        """
        await self.emit_message(label)

    async def emit_agent_result(self, output: Any) -> None:
        """Emit agent result as full-text message for UI display.

        Used by both streaming and non-streaming paths. Display is always
        full-text-at-once regardless of execution mode.
        """
        from .utils import serialize_output

        await self.emit_message(serialize_output(output))

    async def close_workflow(self) -> None:
        """Close the current workflow after agent execution (best effort).

        Each agent creates a workflow for its reasoning display. This method
        closes it after execution so subsequent agents create their own
        workflows instead of continuing the previous one.

        If this fails, the next phase may have display issues (e.g., reasoning
        from previous phase appears to continue), but the flow continues.
        Data integrity is not affected.
        """
        try:
            if self.agent_context.workflow_item is None:
                return

            if self.agent_context.workflow_item.workflow.summary is not None:
                return

            await self.agent_context.end_workflow()
        except Exception:
            # Graceful degradation: workflow boundary failure is non-fatal
            # Worst case: UI display issues, not data loss
            pass

    async def execute_spec(self, spec: ExecutionSpec) -> Any:
        """Execute ExecutionSpec and emit full-text result to ChatKit.

        .stream() controls internal execution mode, not display.
        Runs streaming internally for performance, then emits the full
        result as a single message via emit_agent_result().

        Returns T (str or Pydantic model based on Agent's output_type).

        Session handling:
        - Outside phase: SDK handles Session read/write (str input)
        - Inside phase: PhaseSession only, no Session (list input)
        - phase(persist=True): last pair written to Session at phase end

        When is_silent=True, result is not emitted to ChatKit (no UI display).
        """
        from agents import Runner

        input_data, session = spec.resolve_input()

        run_kwargs = spec.build_run_kwargs(session)

        # ChatKit context overwrites .context() modifier (required for workflow display).
        # Limitation: .context() modifier is silently ignored in ChatKit mode because
        # AgentContext must be the context for workflow boundaries to function.
        # If you need dependency injection in ChatKit mode, use Agent hooks or
        # pass data through the flow function instead.
        run_kwargs["context"] = self.agent_context

        result = Runner.run_streamed(spec.sdk_agent, input_data, **run_kwargs)

        # Consume stream internally — delta events are NOT forwarded to ChatKit queue
        async for _event in result.stream_events():
            pass

        output = result.final_output

        # Emit full-text result as single message
        if not spec.is_silent:
            await self.emit_agent_result(output)

        return output

    async def push_event(self, event: ThreadStreamEvent) -> None:
        """Push event to queue."""
        await self.event_queue.put(event)


async def run_with_chatkit_context(
    runner: Runner,
    thread: ThreadMetadata,
    store: Store,
    context: dict[str, Any],
    user_message: str,
) -> AsyncIterator[ThreadStreamEvent]:
    """Execute Runner with ChatKit context (internal API).

    Full Flow execution with workflow boundary management.
    Each phase creates its own workflow for reasoning display.

    Args:
        runner: Runner instance with flow
        thread: ChatKit ThreadMetadata
        store: ChatKit Store instance
        context: Request context
        user_message: User message to process

    Yields:
        ThreadStreamEvent for ChatKit frontend
    """
    from chatkit.agents import AgentContext

    from .agent import current_session

    agent_context = AgentContext(thread=thread, store=store, request_context=context)
    ctx = ChatKitExecutionContext(agent_context, store)

    token = current_chatkit_context.set(ctx)
    session_token = None
    if runner.session is not None:
        session_token = current_session.set(runner.session)

    flow_task: asyncio.Task[Any] = asyncio.create_task(
        cast(Coroutine[Any, Any, Any], runner.flow(user_message))
    )

    async def get_next_event():
        return await ctx.event_queue.get()

    try:
        while not flow_task.done():
            event_task = asyncio.create_task(get_next_event())
            done, pending = await asyncio.wait(
                [flow_task, event_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if event_task in done:
                event = event_task.result()
                yield event
            else:
                event_task.cancel()
                try:
                    await event_task
                except asyncio.CancelledError:
                    pass

        while not ctx.event_queue.empty():
            event = await ctx.event_queue.get()
            yield event

        await flow_task

    except asyncio.CancelledError:
        # Client disconnected: cancel flow_task to prevent task leak
        flow_task.cancel()
        try:
            await flow_task
        except (asyncio.CancelledError, Exception):
            pass
        raise

    except Exception as e:
        from chatkit.types import (
            AssistantMessageContent,
            AssistantMessageItem,
            ThreadItemAddedEvent,
            ThreadItemDoneEvent,
        )

        error_item = AssistantMessageItem(
            id=ctx.store.generate_item_id("message", ctx.thread, {}),
            thread_id=ctx.thread.id,
            created_at=datetime.now(),
            content=[
                AssistantMessageContent(
                    type="output_text",
                    text=f"Error: {type(e).__name__}: {e}",
                    annotations=[],
                )
            ],
        )
        await ctx.store.add_thread_item(
            ctx.thread.id, error_item, ctx.agent_context.request_context
        )
        yield ThreadItemAddedEvent(type="thread.item.added", item=error_item)
        yield ThreadItemDoneEvent(type="thread.item.done", item=error_item)
        raise

    finally:
        current_chatkit_context.reset(token)
        if session_token is not None:
            current_session.reset(session_token)
