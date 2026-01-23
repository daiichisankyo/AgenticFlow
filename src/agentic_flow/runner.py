"""Runner - Flow execution container.

Design:
    Runner holds Session, injects it into Flow execution via contextvars.
    Flow never references Session directly.

    Session read/write is handled by SDK at ExecutionSpec level.
    Runner does NOT write to Session.

Sync Execution:
    Runner provides synchronous (blocking) execution for Jupyter/REPL:
    - runner.run(msg).sync() - Deferred execution with RunHandle
    - runner.run_sync(msg) - Direct synchronous execution

    sync() is NOT a third execution trigger for ExecutionSpec.
    It's a Runner adapter that internally awaits the execution.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

from .agent import current_handler, current_session
from .types import Handler

if TYPE_CHECKING:
    from agents import Session

T = TypeVar("T")
Flow = Callable[[str], Awaitable[T]]


class RunHandle:
    """Deferred execution handle for Runner.

    Created by runner.run(user_message). Not executed until .sync() or awaited.
    This is a Runner adapter, NOT a third execution trigger for ExecutionSpec.

    Example:
        runner = Runner(flow=my_flow, session=session)

        # Synchronous (blocking) - for Jupyter/REPL
        result = runner.run("hello").sync()

        # Async - same as await runner("hello")
        result = await runner.run("hello")
    """

    def __init__(self, runner: Runner, user_message: str):
        self.runner = runner
        self.user_message = user_message

    def sync(self) -> Any:
        """Execute synchronously (blocking).

        Handles both cases:
        - No running event loop: uses asyncio.run()
        - Running event loop (Jupyter): uses ThreadPoolExecutor

        Warning:
            In Jupyter/running loop environments, execution occurs in a
            separate thread. This may cause issues with libraries that
            are not thread-safe or expect single-threaded event loops.
            For production use, prefer async execution directly.
        """
        try:
            asyncio.get_running_loop()
            has_running_loop = True
        except RuntimeError:
            has_running_loop = False

        if not has_running_loop:
            return asyncio.run(self.runner(self.user_message))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, self.runner(self.user_message))
            return future.result()

    def __await__(self):
        """Allow await on RunHandle for async contexts."""
        return self.runner(self.user_message).__await__()


class Runner:
    """Flow execution container with Session and Handler injection.

    Session is injected via contextvars. SDK handles Session read/write
    at ExecutionSpec level. Runner does NOT write to Session.

    Use phase(persist=True) to write to Session at phase end.

    Handler is injected by Runner (not by phase) to keep UI dependency
    out of Flow code.

    Example:
        def my_handler(event):
            if hasattr(event, "data") and hasattr(event.data, "delta"):
                print(event.data.delta, end="", flush=True)

        async def flow(user_message: str) -> str:
            async with phase("Research", persist=True):
                r1 = await researcher(user_message).stream()  # PhaseSession
                return await responder(f"Result: {r1}").stream()  # Session at phase end

        chat = Runner(flow=flow, session=SQLiteSession("conv_123"), handler=my_handler)
        result = await chat("hello")
    """

    def __init__(
        self,
        flow: Flow[Any],
        session: Session | None = None,
        handler: Handler | None = None,
    ):
        self.flow = flow
        self.session = session
        self.handler = handler

    async def __call__(self, user_message: str) -> Any:
        """Execute flow with user message."""
        session_token = None
        if self.session is not None:
            session_token = current_session.set(self.session)

        handler_token = None
        if self.handler is not None:
            handler_token = current_handler.set(self.handler)

        try:
            return await self.flow(user_message)
        finally:
            if handler_token is not None:
                current_handler.reset(handler_token)
            if session_token is not None:
                current_session.reset(session_token)

    def run(self, user_message: str) -> RunHandle:
        """Create deferred execution handle.

        Returns RunHandle that can be:
        - Awaited: await runner.run(msg)
        - Synced: runner.run(msg).sync()

        Example:
            runner = Runner(flow=my_flow)

            # Jupyter/REPL (synchronous)
            result = runner.run("hello").sync()

            # Async context
            result = await runner.run("hello")
        """
        return RunHandle(self, user_message)

    def run_sync(self, user_message: str) -> Any:
        """Execute synchronously (blocking).

        Convenience method equivalent to runner.run(msg).sync().
        For Jupyter/REPL environments.

        Example:
            runner = Runner(flow=my_flow)
            result = runner.run_sync("hello")
        """
        return self.run(user_message).sync()
