"""Tools for AgenticTranscoder.

Intent: Pure functions for test execution and error formatting.
These are called from the flow to run tests and format results.

Design: Use Pydantic RunResult from types.py for structured output.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from .types import RunResult, TestError, TestEvent

if TYPE_CHECKING:
    Handler = Callable[[Any], Any]


def parse_pytest_output(output: str) -> list[TestError]:
    """Parse pytest output to extract structured errors."""
    errors = []

    failure_pattern = re.compile(r"FAILED\s+(\S+)::(\S+)")
    error_pattern = re.compile(r"(\S+\.py):(\d+):\s*(.+)")

    for match in failure_pattern.finditer(output):
        file_path = match.group(1)
        test_name = match.group(2)
        errors.append(
            TestError(
                file=file_path,
                message=f"Test {test_name} failed",
                traceback=None,
            )
        )

    for match in error_pattern.finditer(output):
        file_path = match.group(1)
        line_num = int(match.group(2))
        message = match.group(3)

        if not any(e.file == file_path and e.line == line_num for e in errors):
            errors.append(
                TestError(
                    file=file_path,
                    line=line_num,
                    message=message,
                )
            )

    return errors


def count_tests(output: str) -> tuple[int, int]:
    """Count total and failed tests from pytest output."""
    passed_match = re.search(r"(\d+)\s+passed", output)
    failed_match = re.search(r"(\d+)\s+failed", output)

    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0

    return passed + failed, failed


class TestRunner:
    """Test runner with handler injection for streaming.

    Design: Handler is injected at construction time.
    This makes the dependency explicit and testable.

    Usage:
        runner = TestRunner(output_dir, handler=my_handler)
        result = await runner.run()
        # Events are emitted to handler during execution

    Without handler (silent mode):
        runner = TestRunner(output_dir)
        result = await runner.run()
        # No events emitted, just returns result
    """

    def __init__(self, output_dir: str, handler: Handler | None = None):
        self.output_dir = output_dir
        self.handler = handler

    def emit(self, event: TestEvent) -> None:
        """Emit event to handler if available."""
        if self.handler:
            self.handler(event)

    async def run(self) -> RunResult:
        """Run tests with event emission.

        Returns:
            RunResult with structured errors
        """
        cwd_path = Path(self.output_dir)
        cmd = ["uv", "run", "pytest", "tests/", "-v", "--tb=short"]

        self.emit(TestEvent(type="test.started", content="Running pytest..."))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_lines: list[str] = []

        async for line in proc.stdout:
            text = line.decode().rstrip()
            output_lines.append(text)
            self.emit(TestEvent(type="test.output", content=text))

        await proc.wait()

        output = "\n".join(output_lines)
        total, failed_count = count_tests(output)
        errors = parse_pytest_output(output) if proc.returncode != 0 else []

        result = RunResult(
            passed=(proc.returncode == 0),
            total=total,
            failed_count=failed_count,
            errors=errors,
        )

        self.emit(TestEvent(type="test.completed", result=result))

        return result


async def run_tests(output_dir: str, handler: Handler | None = None) -> RunResult:
    """Run pytest and return structured results.

    Convenience wrapper for TestRunner.

    Args:
        output_dir: Project directory
        handler: Optional event handler for streaming

    Returns:
        RunResult with structured errors
    """
    runner = TestRunner(output_dir, handler=handler)
    return await runner.run()


def format_errors(errors: list[TestError]) -> str:
    """Format errors for prompt injection.

    Args:
        errors: List of TestError objects

    Returns:
        Formatted string for LLM prompts
    """
    if not errors:
        return "(none)"

    lines = []
    for e in errors:
        if e.line:
            lines.append(f"- {e.file}:{e.line}: {e.message}")
        else:
            lines.append(f"- {e.file}: {e.message}")

    return "\n".join(lines)
