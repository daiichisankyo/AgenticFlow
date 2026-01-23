"""Pydantic types for AgenticTranscoder.

Intent: Provide structured output types for test results.

Design principle: Never parse LLM text manually.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ContentType = Literal["text", "markdown", "json"]


class TestError(BaseModel):
    """Individual test error."""

    file: str
    line: int | None = None
    message: str
    traceback: str | None = None


class RunResult(BaseModel):
    """Structured test execution result."""

    passed: bool = Field(description="All tests passed")
    total: int = Field(default=0, description="Total test count")
    failed_count: int = Field(default=0, description="Number of failed tests")
    errors: list[TestError] = Field(default_factory=list, description="Structured errors")

    @property
    def failed(self) -> bool:
        return not self.passed


class ReflectionResult(BaseModel):
    """Structured reflection output from reflector agent.

    Reflector uses tools to manage todos:
    - add_todo(): Create improvement tasks for Coder
    - verify_todo(): Confirm Coder's work is complete
    - patterns_ok: Set True when all patterns correct and all todos verified
    """

    patterns_ok: bool = Field(default=False, description="All Agentic Flow patterns correct")


class TestEvent(BaseModel):
    """Test execution event for streaming.

    Emitted by TestRunner during test execution.
    Handler receives these events to update display.
    """

    type: Literal["test.started", "test.output", "test.completed"] = "test.output"
    content: str = ""
    result: RunResult | None = None
