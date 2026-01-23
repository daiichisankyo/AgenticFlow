"""Event handler for Agentic Flow.

Intent: Stateful event handler that bridges Agentic Flow events to Display.

Streaming events:
- response.reasoning_summary_text.delta → Reasoning panel
- response.output_text.delta → Output panel
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from ..agents.tools import current_todos
from .display import TranscoderDisplay
from .parsers import parse_tool_output

if TYPE_CHECKING:
    from rich.console import Console

    from ..types import ContentType


class EventHandler:
    """Stateful event handler for Agentic Flow events."""

    def __init__(self, display: TranscoderDisplay) -> None:
        self.display = display
        self.pending_exec_cmd: str = ""

    def __call__(self, event: Any) -> None:
        """Handle Agentic Flow event."""
        event_type = getattr(event, "type", None)
        if event_type is None:
            return

        if event_type == "phase.started":
            self.handle_phase_started(event)
        elif event_type == "phase.ended":
            self.handle_phase_ended(event)
        elif event_type == "raw_response_event":
            self.handle_raw_response(event)
        elif event_type == "run_item_stream_event":
            self.handle_run_item_stream(event)
        elif event_type.startswith("test."):
            self.handle_test_event(event)

    def handle_phase_started(self, event: Any) -> None:
        """Handle phase.started event with optional output_type."""
        if hasattr(event, "label"):
            output_type: ContentType = getattr(event, "output_type", "text")
            self.display.start_phase(event.label, output_type)
            if self.display.show_todos:
                self.sync_todos()

    def handle_phase_ended(self, event: Any) -> None:
        """Handle phase.ended event."""
        self.display.end_phase()
        if self.display.show_todos:
            self.sync_todos()

    def handle_raw_response(self, event: Any) -> None:
        """Handle raw_response_event for streaming.

        Routes to appropriate renderer based on event type:
        - response.reasoning_summary_text.delta → Reasoning panel
        - response.output_text.delta → Output panel
        - response.function_call_arguments.delta → Output panel (tool args)
        """
        data = getattr(event, "data", None)
        if not data:
            return

        data_type = getattr(data, "type", "")

        if data_type == "response.reasoning_summary_text.delta":
            delta = getattr(data, "delta", "")
            if delta and isinstance(delta, str):
                self.display.stream_reasoning_delta(delta)
        elif data_type == "response.output_text.delta":
            delta = getattr(data, "delta", "")
            if delta and isinstance(delta, str):
                self.display.stream_output_delta(delta)
        elif data_type == "response.function_call_arguments.delta":
            delta = getattr(data, "delta", "")
            if delta and isinstance(delta, str):
                self.display.stream_output_delta(delta)
        elif data_type == "response.output_item.added":
            item = getattr(data, "item", None)
            if item and getattr(item, "type", "") == "function_call":
                tool_name = getattr(item, "name", "tool")
                self.display.start_tool_stream(tool_name)

    def handle_run_item_stream(self, event: Any) -> None:
        """Handle run_item_stream_event for tool calls."""
        name = getattr(event, "name", None)

        if name == "tool_called":
            self.handle_tool_called(event)
        elif name == "tool_output":
            self.handle_tool_output(event)

    def handle_tool_called(self, event: Any) -> None:
        """Handle tool_called event to capture pending command."""
        item = getattr(event, "item", None)
        if item is None:
            return

        raw_item = getattr(item, "raw_item", None)
        if raw_item is None:
            return

        tool_name = getattr(raw_item, "name", None) or "tool"
        if tool_name == "exec_command":
            args_str = getattr(raw_item, "arguments", None)
            if args_str:
                try:
                    args = json.loads(args_str)
                    cmd = args.get("command", "")
                    if cmd:
                        self.pending_exec_cmd = cmd[:50] + "..." if len(cmd) > 50 else cmd
                except json.JSONDecodeError:
                    pass

    def handle_tool_output(self, event: Any) -> None:
        """Handle tool_output event."""
        item = getattr(event, "item", None)
        if item is None:
            return

        raw_item = getattr(item, "raw_item", None)
        tool_name = getattr(raw_item, "name", None) if raw_item else None
        if not tool_name:
            tool_name = "tool"
        output = getattr(item, "output", None)

        if not isinstance(output, str):
            return

        if tool_name in ("get_todos", "add_todo", "mark_done", "verify_todo"):
            self.sync_todos()

        result = parse_tool_output(tool_name, output, self.pending_exec_cmd)
        if result:
            self.display.tool_call(result.tool_name, result.summary)

    def handle_test_event(self, event: Any) -> None:
        """Handle TestEvent for test streaming."""
        event_type = getattr(event, "type", "")

        if event_type == "test.started":
            content = getattr(event, "content", "")
            self.display.stream_delta(content + "\n")
        elif event_type == "test.output":
            content = getattr(event, "content", "")
            self.display.stream_delta(content + "\n")
        elif event_type == "test.completed":
            result = getattr(event, "result", None)
            if result:
                status = "✅ PASSED" if result.passed else "❌ FAILED"
                summary = f"\n{status} ({result.total} tests, {result.failed_count} failed)\n"
                self.display.stream_delta(summary)

    def sync_todos(self) -> None:
        """Sync todo state from ContextVar to display."""
        try:
            todos = current_todos.get()
            self.display.update_todos(list(todos))
        except LookupError:
            pass


def create_handler(console: Console) -> tuple[TranscoderDisplay, EventHandler]:
    """Create display and handler for Runner.

    Args:
        console: Rich Console instance

    Returns:
        Tuple of (display, handler) for CLI and Runner
    """
    display = TranscoderDisplay(console)
    handler = EventHandler(display)
    return display, handler
