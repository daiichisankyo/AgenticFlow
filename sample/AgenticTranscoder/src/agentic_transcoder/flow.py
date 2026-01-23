"""AgenticTranscoder flow - State Machine transformation.

Intent: Transform AgentBuilder code into a working Agentic Flow project.

Architecture:
    Transcoder class holds configuration and provides a Runner-compatible
    1-argument flow method. This respects Agentic Flow's Runner API while
    enabling batch processing with multiple configuration parameters.

    Usage:
        transcoder = Transcoder(source_code, output_dir)
        runner = transcoder.runner(handler=my_handler)
        result = await runner("")

State Machine (3 states):
    [*] --> CODER
    CODER --> TEST
    TEST --> CODER: fail
    TEST --> REFLECTOR: pass
    REFLECTOR --> CODER: has_pending
    REFLECTOR --> [*]: all_verified

    CODER uses different prompts based on context:
    - Generate: First run (no todos)
    - Fix: After test failure
    - Improve: After Reflector creates todos

Agents:
    - coder: File editing agent with reasoning("high")
    - reflector: Quality review agent with reasoning("high")

Todo Responsibility:
    - Reflector: Creates todos (add_todo), verifies completion (verify_todo)
    - Coder: Executes todos, reports completion (mark_done)
    - Flow: State transitions only
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from agentic_flow import Runner, phase
from agentic_flow.agent import current_handler

from .agents import coder, deploy_template, reflector
from .agents.coder import FIX_PROMPT, GENERATE_PROMPT, IMPROVE_PROMPT
from .agents.reflector import REFLECT_PROMPT
from .agents.tools import current_todos
from .tools import format_errors, run_tests
from .types import RunResult

if TYPE_CHECKING:
    from agentic_flow.types import Handler


class State(Enum):
    """State machine states.

    Aligned with README specification:
    - CODER: Uses different prompts (Generate/Fix/Improve) based on context
    - TEST: Runs tests
    - REFLECTOR: Reviews patterns and manages todos
    """

    CODER = "CODER"
    TEST = "TEST"
    REFLECTOR = "REFLECTOR"


MAX_LOOP = 10


class Transcoder:
    """Transform AgentBuilder code to Agentic Flow project.

    Holds configuration and provides Runner-compatible flow method.
    Runner Is Mandatory - use runner() to get a configured Runner.

    Todo Management:
        self.todos is the shared state accessible via ContextVar.
        - Reflector creates todos (add_todo) and verifies them (verify_todo)
        - Coder executes and reports completion (mark_done)
        - Flow only manages state transitions

    Example:
        transcoder = Transcoder(
            source_code=code,
            output_dir="/tmp/project",
        )
        runner = transcoder.runner(handler=my_handler)
        result = await runner("")
    """

    def __init__(self, source_code: str, output_dir: str):
        self.source_code = source_code
        self.output_dir = output_dir
        self.todos: list[dict[str, Any]] = []

    def has_pending_todos(self) -> bool:
        """Check if there are pending todos to work on."""
        return any(t.get("status") == "pending" for t in self.todos)

    def all_verified(self) -> bool:
        """Check if all todos are verified by Reflector."""
        if not self.todos:
            return True
        return all(t.get("status") == "verified" for t in self.todos)

    async def flow(self, _: str = "") -> RunResult:
        """Runner-compatible flow method (1 argument).

        State machine (aligned with README):
            [*] --> CODER
            CODER --> TEST
            TEST --> CODER: fail
            TEST --> REFLECTOR: pass
            REFLECTOR --> CODER: has_pending
            REFLECTOR --> [*]: all_verified

        Returns:
            RunResult with test execution results
        """
        state = State.CODER
        test: RunResult | None = None
        last_test_failed = False

        deploy_template(self.output_dir)
        current_todos.set(self.todos)

        for _ in range(MAX_LOOP):
            match state:
                case State.CODER:
                    if last_test_failed:
                        async with phase("🔧 Fix"):
                            prompt = FIX_PROMPT.format(
                                output_dir=self.output_dir,
                                errors=format_errors(test.errors) if test else "",
                            )
                            await coder(prompt).max_turns(100).stream()
                    elif self.has_pending_todos():
                        async with phase("💫 Improve"):
                            prompt = IMPROVE_PROMPT.format(output_dir=self.output_dir)
                            await coder(prompt).max_turns(100).stream()
                    else:
                        async with phase("🚀 Generate"):
                            prompt = GENERATE_PROMPT.format(
                                output_dir=self.output_dir,
                                source_code=self.source_code,
                            )
                            await coder(prompt).max_turns(100).stream()
                    state = State.TEST

                case State.TEST:
                    async with phase("🧪 Test"):
                        handler = current_handler.get()
                        test = await run_tests(self.output_dir, handler=handler)

                    if test.failed:
                        last_test_failed = True
                        state = State.CODER
                    else:
                        last_test_failed = False
                        state = State.REFLECTOR

                case State.REFLECTOR:
                    async with phase("💎 Reflect"):
                        prompt = REFLECT_PROMPT.format(
                            output_dir=self.output_dir,
                            source_code=self.source_code,
                        )
                        reflection = await reflector(prompt).max_turns(100).stream()

                    if reflection.patterns_ok and self.all_verified():
                        break
                    if self.has_pending_todos():
                        state = State.CODER

        return test

    def runner(self, handler: Handler | None = None) -> Runner:
        """Create Runner with handler injection."""
        return Runner(flow=self.flow, handler=handler)


async def transcode(source_code: str, output_dir: str) -> RunResult:
    """Convenience function wrapping Transcoder.

    For simple usage without handler injection.
    For handler support, use Transcoder class directly.
    """
    return await Transcoder(source_code, output_dir).flow()


runner = Runner(flow=transcode)
