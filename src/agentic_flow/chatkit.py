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
    """Context for ChatKit Server execution with workflow boundary management.

    Manages:
    - Event queue for streaming to frontend
    - Workflow boundaries for multi-agent flows
    - Agent execution with stream_agent_response
    """

    def __init__(self, agent_context: AgentContext, store: Store):
        self.agent_context = agent_context
        self.store = store
        self.event_queue: asyncio.Queue[ThreadStreamEvent] = asyncio.Queue()

    @property
    def thread(self):
        return self.agent_context.thread

    async def emit_phase_label(self, label: str) -> None:
        """Emit a phase label to create workflow boundary.

        Saves a message to store before agent execution. This ensures
        stream_agent_response sees a message (not workflow) as last item
        and creates a new workflow for reasoning display.
        """
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
            content=[AssistantMessageContent(type="output_text", text=label, annotations=[])],
        )
        await self.store.add_thread_item(self.thread.id, item, self.agent_context.request_context)
        await self.push_event(ThreadItemAddedEvent(type="thread.item.added", item=item))
        await self.push_event(ThreadItemDoneEvent(type="thread.item.done", item=item))

    async def emit_agent_result(self, output: Any) -> None:
        """Emit agent result as message for UI display (non-streaming execution).

        For non-streaming agent calls, this method displays the result in the
        ChatKit UI. Streaming calls use execute_spec() which handles display
        through stream_agent_response().
        """
        from chatkit.types import (
            AssistantMessageContent,
            AssistantMessageItem,
            ThreadItemAddedEvent,
            ThreadItemDoneEvent,
        )

        from .utils import serialize_output

        output_str = serialize_output(output)

        item_id = self.store.generate_item_id("message", self.thread, {})
        item = AssistantMessageItem(
            id=item_id,
            thread_id=self.thread.id,
            created_at=datetime.now(),
            content=[AssistantMessageContent(type="output_text", text=output_str, annotations=[])],
        )
        await self.store.add_thread_item(self.thread.id, item, self.agent_context.request_context)
        await self.push_event(ThreadItemAddedEvent(type="thread.item.added", item=item))
        await self.push_event(ThreadItemDoneEvent(type="thread.item.done", item=item))

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
        """Execute ExecutionSpec with stream_agent_response.

        Streams events to the queue and returns final output.
        Returns T (str or Pydantic model based on Agent's output_type).

        Note: Uses Runner.run_streamed with context=agent_context to enable
        proper workflow/reasoning display in ChatKit.

        Session handling follows docs/design/execution-model.md:
        - phase 外: SDK handles Session read/write (str input)
        - phase 内: PhaseSession only, no Session (list input)
        - phase(persist=True): last pair written to Session at phase end

        SDK constraint: list input + session is not allowed.
        resolve_input() returns (str, session) or (list, None) appropriately.

        When is_silent=True, events are not pushed to the queue (no UI display).
        """
        from agents import Runner
        from chatkit.agents import stream_agent_response

        input_data, session = spec.resolve_input()

        # Build run_kwargs: session + spec modifiers (.run_config, .run_kwarg, .max_turns)
        run_kwargs: dict = {"session": session, **spec.run_kwargs}
        if spec.max_turns_sdk is not None:
            run_kwargs["max_turns"] = spec.max_turns_sdk

        # ChatKit context overwrites .context() modifier (required for workflow display)
        # Limitation: .context() is not supported in ChatKit mode
        run_kwargs["context"] = self.agent_context

        result = Runner.run_streamed(spec.sdk_agent, input_data, **run_kwargs)

        async for event in stream_agent_response(self.agent_context, result):
            if not spec.is_silent:
                await self.push_event(event)

        # Close workflow after each agent execution to ensure next agent gets its own workflow
        await self.close_workflow()

        return result.final_output

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
