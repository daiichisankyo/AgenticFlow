"""Layer 2: Mock tests for AgenticTranscoder.

Intent: Test flow logic WITHOUT real API calls.
These tests are FAST (<1s) and DETERMINISTIC.

What we test:
- Console display logic with 4 phases (Generate, Fix, Test, Reflect)
- Handler event processing
- Type validation at boundaries
- Tool helper functions

Philosophy v3 compliant - State Machine with coder + reflector.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from agentic_transcoder.types import RunResult


class TestConsoleLogic:
    """Test console display with 3 states."""

    def test_display_tracks_multiple_phases(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.end_phase()
        display.start_phase("🔧 Fix")
        display.end_phase()
        display.start_phase("💎 Reflect")
        display.end_phase()

        assert len(display.completed_phases) == 3
        assert display.completed_phases[0][0] == "🚀 Generate"
        assert display.completed_phases[1][0] == "🔧 Fix"
        assert display.completed_phases[2][0] == "💎 Reflect"

    def test_display_phase_labels(self):
        from agentic_transcoder.console.display import TranscoderDisplay

        assert TranscoderDisplay.PHASE_LABELS == {
            "🚀 Generate": "Generating",
            "💫 Improve": "Improving",
            "🔧 Fix": "Fixing",
            "🧪 Test": "Testing",
            "💎 Reflect": "Reflecting",
        }

    def test_display_counts_files(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.tool_call("write", "file1.py")
        display.tool_call("write", "file2.py")
        display.tool_call("read", "file3.py")

        assert display.files_created == 2

    def test_display_streams_delta(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.stream_delta("Hello ")
        display.stream_delta("World")

        assert display.output_renderer.buffer == "Hello World"

    def test_display_resets_on_new_phase(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.stream_delta("some text")
        display.tool_call("write", "file.py")
        display.end_phase()

        display.start_phase("🔧 Fix")
        assert display.output_renderer.buffer == ""
        assert display.tool_items == []

    def test_display_show_todos_after_reflect(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        assert display.show_todos is False

        display.start_phase("🚀 Generate")
        display.end_phase()
        assert display.show_todos is False

        display.start_phase("💎 Reflect")
        display.end_phase()
        assert display.show_todos is True

    def test_display_update_todos(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        todos = [
            {"content": "Add guardrail", "status": "pending"},
            {"content": "Fix import", "status": "done"},
            {"content": "Update test", "status": "verified"},
        ]
        display.update_todos(todos)

        assert len(display.todos) == 3
        assert display.todos[0]["status"] == "pending"
        assert display.todos[1]["status"] == "done"
        assert display.todos[2]["status"] == "verified"

    def test_display_todo_panel_hidden_before_reflect(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.update_todos([{"content": "Task", "status": "pending"}])
        panel = display.build_todo_panel()

        assert panel is None

    def test_display_todo_panel_shown_after_reflect(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()
        display.update_todos([{"content": "Task", "status": "pending"}])
        panel = display.build_todo_panel()

        assert panel is not None

    def test_display_todo_panel_empty_returns_none(self):
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()
        panel = display.build_todo_panel()

        assert panel is None


class TestHandlerEvents:
    """Test handler responds to state machine events."""

    def test_handler_tracks_generate_phase(self):
        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        event = MagicMock()
        event.type = "phase.started"
        event.label = "🚀 Generate"
        handler(event)

        assert display.current_phase == "🚀 Generate"

    def test_handler_tracks_fix_phase(self):
        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        event = MagicMock()
        event.type = "phase.started"
        event.label = "🔧 Fix"
        handler(event)

        assert display.current_phase == "🔧 Fix"

    def test_handler_tracks_reflect_phase(self):
        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        event = MagicMock()
        event.type = "phase.started"
        event.label = "💎 Reflect"
        handler(event)

        assert display.current_phase == "💎 Reflect"

    def test_handler_ends_phase(self):
        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "🚀 Generate"
        handler(start_event)

        end_event = MagicMock()
        end_event.type = "phase.ended"
        handler(end_event)

        assert display.current_phase == ""
        assert len(display.completed_phases) == 1

    def test_handler_ignores_unknown_events(self):
        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        unknown_event = MagicMock()
        unknown_event.type = "unknown.event"
        handler(unknown_event)

        assert display.current_phase == ""
        assert len(display.completed_phases) == 0

    def test_handler_processes_stream_delta(self):
        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        event = MagicMock()
        event.type = "raw_response_event"
        event.data = MagicMock()
        event.data.type = "response.output_text.delta"
        event.data.delta = "Hello"
        handler(event)

        assert display.output_renderer.buffer == "Hello"

    def test_handler_syncs_todos_after_reflect_end(self):
        from rich.console import Console

        from agentic_transcoder.agents.tools import current_todos
        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        todos = [{"content": "Test task", "status": "pending"}]
        current_todos.set(todos)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "💎 Reflect"
        handler(start_event)

        end_event = MagicMock()
        end_event.type = "phase.ended"
        handler(end_event)

        assert display.show_todos is True
        assert len(display.todos) == 1
        assert display.todos[0]["content"] == "Test task"

    def test_handler_syncs_todos_on_phase_start_after_reflect(self):
        from rich.console import Console

        from agentic_transcoder.agents.tools import current_todos
        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        todos = [{"content": "Improve task", "status": "pending"}]
        current_todos.set(todos)

        reflect_start = MagicMock()
        reflect_start.type = "phase.started"
        reflect_start.label = "💎 Reflect"
        handler(reflect_start)

        reflect_end = MagicMock()
        reflect_end.type = "phase.ended"
        handler(reflect_end)

        todos[0]["status"] = "done"

        improve_start = MagicMock()
        improve_start.type = "phase.started"
        improve_start.label = "💫 Improve"
        handler(improve_start)

        assert display.todos[0]["status"] == "done"


class TestTypeValidation:
    """Test Pydantic type validation at boundaries."""

    def test_run_result_properties(self):
        result = RunResult(passed=False, total=10, failed_count=3)

        assert result.failed is True
        assert result.passed is False

    def test_run_result_defaults(self):
        result = RunResult(passed=True)

        assert result.total == 0
        assert result.failed_count == 0
        assert result.errors == []


class TestToolFunctions:
    """Test tool helper functions (no API calls)."""

    def test_format_errors_with_line(self):
        from agentic_transcoder.tools import format_errors
        from agentic_transcoder.types import TestError

        errors = [TestError(file="test.py", line=42, message="Failed")]
        result = format_errors(errors)

        assert "test.py:42" in result
        assert "Failed" in result

    def test_format_errors_without_line(self):
        from agentic_transcoder.tools import format_errors
        from agentic_transcoder.types import TestError

        errors = [TestError(file="test.py", message="Failed")]
        result = format_errors(errors)

        assert "test.py:" in result

    def test_format_errors_empty(self):
        from agentic_transcoder.tools import format_errors

        result = format_errors([])
        assert result == "(none)"

    def test_format_errors_multiple(self):
        from agentic_transcoder.tools import format_errors
        from agentic_transcoder.types import TestError

        errors = [
            TestError(file="test_unit.py", message="Unit fail"),
            TestError(file="test_server.py", message="Server fail"),
        ]
        result = format_errors(errors)

        assert "test_unit.py" in result
        assert "test_server.py" in result

    def test_parse_pytest_output(self):
        from agentic_transcoder.tools import parse_pytest_output

        output = """
        FAILED tests/test_flow.py::test_example
        tests/test_flow.py:10: AssertionError
        """
        errors = parse_pytest_output(output)

        assert len(errors) >= 1

    def test_count_tests(self):
        from agentic_transcoder.tools import count_tests

        output = "5 passed, 2 failed in 1.5s"
        total, failed = count_tests(output)

        assert total == 7
        assert failed == 2

    def test_count_tests_only_passed(self):
        from agentic_transcoder.tools import count_tests

        output = "10 passed in 2.0s"
        total, failed = count_tests(output)

        assert total == 10
        assert failed == 0


class TestCLIDisplayPanels:
    """Test CLI display panels (Tools, Reasoning, Output) render correctly."""

    def test_tools_panel_displays_skill_loads(self):
        """Test Tools panel displays skill loads correctly."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.tool_call("skill", "guardrails")
        display.tool_call("skill", "router")
        display.tool_call("skill", "websearch")

        assert len(display.tool_items) == 3
        assert "skill → guardrails" in display.tool_items[0]
        assert "skill → router" in display.tool_items[1]
        assert "skill → websearch" in display.tool_items[2]

    def test_tools_panel_displays_file_operations(self):
        """Test Tools panel displays file operations correctly."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.tool_call("read", "agent_specs.py")
        display.tool_call("write", "flow.py")
        display.tool_call("edit", "tests/test_flow.py")

        assert len(display.tool_items) == 3
        assert "read → agent_specs.py" in display.tool_items[0]
        assert "write → flow.py" in display.tool_items[1]
        assert "edit → tests/test_flow.py" in display.tool_items[2]
        assert display.files_created == 1

    def test_reasoning_panel_displays_content(self):
        """Test Reasoning panel displays reasoning content."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.stream_reasoning_delta("**Considering file modifications**\n\n")
        display.stream_reasoning_delta("I might need to be cautious...")

        assert display.reasoning_renderer.has_content()
        assert "Considering file modifications" in display.reasoning_renderer.buffer
        assert "cautious" in display.reasoning_renderer.buffer

    def test_output_panel_displays_json_stream(self):
        """Test Output panel displays JSON streaming correctly."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.start_tool_stream("read_file")
        display.stream_output_delta('{"path": "agent_specs.py", ')
        display.stream_output_delta('"cwd": "/workspace/project"}')

        assert display.output_renderer.content_type == "json"
        assert "agent_specs.py" in display.output_renderer.buffer

    def test_full_generate_phase_display(self):
        """Test full Generate phase with Tools + Reasoning + Output."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")

        display.tool_call("skill", "guardrails")
        display.tool_call("skill", "router")

        display.stream_reasoning_delta("**Analysis**\n\nThe source code uses routing...")

        display.stream_output_delta("Transforming agent definitions...")

        assert display.current_phase == "🚀 Generate"
        assert len(display.tool_items) == 2
        assert display.reasoning_renderer.has_content()
        assert display.output_renderer.has_content()

        group = display.build_display()
        assert group is not None

    def test_handler_routes_reasoning_events(self):
        """Test handler routes reasoning events to Reasoning panel."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "🚀 Generate"
        handler(start_event)

        reasoning_event = MagicMock()
        reasoning_event.type = "raw_response_event"
        reasoning_event.data = MagicMock()
        reasoning_event.data.type = "response.reasoning_summary_text.delta"
        reasoning_event.data.delta = "**Thinking about the problem**"
        handler(reasoning_event)

        assert display.reasoning_renderer.has_content()
        assert "Thinking about the problem" in display.reasoning_renderer.buffer

    def test_handler_routes_output_events(self):
        """Test handler routes output events to Output panel."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "🚀 Generate"
        handler(start_event)

        output_event = MagicMock()
        output_event.type = "raw_response_event"
        output_event.data = MagicMock()
        output_event.data.type = "response.output_text.delta"
        output_event.data.delta = "Writing agent_specs.py..."
        handler(output_event)

        assert display.output_renderer.has_content()
        assert "agent_specs.py" in display.output_renderer.buffer

    def test_handler_routes_function_call_args(self):
        """Test handler routes function call arguments to Output panel."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "🚀 Generate"
        handler(start_event)

        func_args_event = MagicMock()
        func_args_event.type = "raw_response_event"
        func_args_event.data = MagicMock()
        func_args_event.data.type = "response.function_call_arguments.delta"
        func_args_event.data.delta = '{"path": "flow.py"}'
        handler(func_args_event)

        assert display.output_renderer.has_content()
        assert "flow.py" in display.output_renderer.buffer

    def test_completed_phases_display(self):
        """Test completed phases show checkmarks."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.end_phase()
        display.start_phase("🧪 Test")
        display.end_phase()
        display.start_phase("💎 Reflect")
        display.end_phase()

        assert len(display.completed_phases) == 3
        assert display.completed_phases[0][0] == "🚀 Generate"
        assert display.completed_phases[1][0] == "🧪 Test"
        assert display.completed_phases[2][0] == "💎 Reflect"


class TestReflectorDisplayPanels:
    """Test Reflector phase CLI display (Tools, Reasoning, Todos)."""

    def test_reflector_tools_panel_displays_skill_loads(self):
        """Test Reflector Tools panel displays skill loads."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.tool_call("skill", "guardrails")
        display.tool_call("read", "agent_specs.py")
        display.tool_call("read", "flow.py")

        assert len(display.tool_items) == 3
        assert "skill → guardrails" in display.tool_items[0]
        assert "read → agent_specs.py" in display.tool_items[1]
        assert "read → flow.py" in display.tool_items[2]

    def test_reflector_reasoning_panel_displays(self):
        """Test Reflector Reasoning panel displays review thoughts."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.stream_reasoning_delta("**Reviewing transformation quality**\n\n")
        display.stream_reasoning_delta("Checking for SDK pattern compliance...")

        assert display.reasoning_renderer.has_content()
        assert "Reviewing transformation quality" in display.reasoning_renderer.buffer
        assert "SDK pattern compliance" in display.reasoning_renderer.buffer

    def test_reflector_todo_tools_display(self):
        """Test Reflector todo tools (add_todo, verify_todo) display."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.tool_call("add_todo", "Use SDK guardrails decorator")
        display.tool_call("add_todo", "Remove manual history management")
        display.tool_call("get_todos", "2 items")

        assert len(display.tool_items) == 3
        assert "add_todo → Use SDK guardrails decorator" in display.tool_items[0]
        assert "add_todo → Remove manual history management" in display.tool_items[1]

    def test_reflector_todo_panel_shown_after_reflect(self):
        """Test Todo panel appears after first Reflect phase."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.end_phase()
        assert display.show_todos is False

        display.start_phase("🧪 Test")
        display.end_phase()
        assert display.show_todos is False

        display.start_phase("💎 Reflect")
        display.end_phase()
        assert display.show_todos is True

    def test_reflector_todo_panel_displays_status(self):
        """Test Todo panel displays pending/done/verified status."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()

        todos = [
            {"content": "Use SDK guardrails", "status": "pending"},
            {"content": "Remove manual history", "status": "done"},
            {"content": "Add phase labels", "status": "verified"},
        ]
        display.update_todos(todos)

        panel = display.build_todo_panel()
        assert panel is not None
        assert len(display.todos) == 3
        assert display.todos[0]["status"] == "pending"
        assert display.todos[1]["status"] == "done"
        assert display.todos[2]["status"] == "verified"

    def test_handler_routes_reflector_reasoning(self):
        """Test handler routes Reflector reasoning to Reasoning panel."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "💎 Reflect"
        handler(start_event)

        reasoning_event = MagicMock()
        reasoning_event.type = "raw_response_event"
        reasoning_event.data = MagicMock()
        reasoning_event.data.type = "response.reasoning_summary_text.delta"
        reasoning_event.data.delta = "**Checking intent preservation**"
        handler(reasoning_event)

        assert display.reasoning_renderer.has_content()
        assert "Checking intent preservation" in display.reasoning_renderer.buffer

    def test_handler_syncs_todos_on_reflect_end(self):
        """Test handler syncs todos when Reflect phase ends."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.agents.tools import current_todos
        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        todos = [
            {"content": "Add SDK guardrails", "status": "pending"},
            {"content": "Fix import order", "status": "pending"},
        ]
        current_todos.set(todos)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "💎 Reflect"
        handler(start_event)

        end_event = MagicMock()
        end_event.type = "phase.ended"
        handler(end_event)

        assert display.show_todos is True
        assert len(display.todos) == 2
        assert display.todos[0]["content"] == "Add SDK guardrails"

    def test_full_reflect_phase_display(self):
        """Test full Reflect phase with Tools + Reasoning + Todos."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.end_phase()
        display.start_phase("🧪 Test")
        display.end_phase()

        display.start_phase("💎 Reflect")

        display.tool_call("skill", "guardrails")
        display.tool_call("read", "agent_specs.py")
        display.tool_call("add_todo", "Use @input_guardrail decorator")

        display.stream_reasoning_delta("**Pattern Analysis**\n\n")
        display.stream_reasoning_delta("The code uses inline guardrails...")

        display.stream_output_delta('{"patterns_ok": false}')

        assert display.current_phase == "💎 Reflect"
        assert len(display.tool_items) == 3
        assert display.reasoning_renderer.has_content()
        assert display.output_renderer.has_content()

        group = display.build_display()
        assert group is not None

    def test_improve_phase_after_reflect(self):
        """Test Improve phase shows Todos panel from previous Reflect."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.agents.tools import current_todos
        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        todos = [{"content": "Improve task", "status": "pending"}]
        current_todos.set(todos)

        reflect_start = MagicMock()
        reflect_start.type = "phase.started"
        reflect_start.label = "💎 Reflect"
        handler(reflect_start)

        reflect_end = MagicMock()
        reflect_end.type = "phase.ended"
        handler(reflect_end)

        assert display.show_todos is True

        improve_start = MagicMock()
        improve_start.type = "phase.started"
        improve_start.label = "💫 Improve"
        handler(improve_start)

        assert display.show_todos is True
        assert display.current_phase == "💫 Improve"

        panel = display.build_todo_panel()
        assert panel is not None


class TestReflectorTodoPanel:
    """Test Reflector Todo panel CLI display like the real output.

    CLI Output Example:
    ╭─ 📋 Todos ──────────────────────────────────────────────────────────────╮
    │   [ ] Fix Q&A routes session persistence...                             │
    │   [ ] Ensure guardrails behavior is preserved...                        │
    │   [ ] Either use verification_router in the verify loop...              │
    ╰─────────────────────────────────────────────────────────────────────────╯
    """

    def test_todo_panel_checkbox_pending_status(self):
        """Test pending todos display as [ ]."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()

        todos = [
            {"content": "Fix Q&A routes session persistence", "status": "pending"},
        ]
        display.update_todos(todos)

        assert display.todos[0]["status"] == "pending"
        panel = display.build_todo_panel()
        assert panel is not None

    def test_todo_panel_checkbox_done_status(self):
        """Test done todos display as [x] or similar."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()

        todos = [
            {"content": "Use SDK guardrails decorator", "status": "done"},
        ]
        display.update_todos(todos)

        assert display.todos[0]["status"] == "done"

    def test_todo_panel_checkbox_verified_status(self):
        """Test verified todos display as [✓] or similar."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()

        todos = [
            {"content": "Add phase labels", "status": "verified"},
        ]
        display.update_todos(todos)

        assert display.todos[0]["status"] == "verified"

    def test_todo_panel_multiple_pending_items(self):
        """Test multiple pending todos like real CLI output."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()

        todos = [
            {"content": "Fix Q&A routes session persistence", "status": "pending"},
            {"content": "Ensure guardrails behavior is preserved", "status": "pending"},
            {"content": "Either use verification_router in verify loop", "status": "pending"},
        ]
        display.update_todos(todos)

        panel = display.build_todo_panel()
        assert panel is not None
        assert len(display.todos) == 3
        assert all(t["status"] == "pending" for t in display.todos)

    def test_todo_panel_mixed_status(self):
        """Test todos with mixed status (pending, done, verified)."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()

        todos = [
            {"content": "Add SDK guardrails", "status": "verified"},
            {"content": "Remove manual history", "status": "done"},
            {"content": "Fix session persistence", "status": "pending"},
        ]
        display.update_todos(todos)

        panel = display.build_todo_panel()
        assert panel is not None
        assert display.todos[0]["status"] == "verified"
        assert display.todos[1]["status"] == "done"
        assert display.todos[2]["status"] == "pending"

    def test_todo_panel_lifecycle_pending_to_done(self):
        """Test todo lifecycle: pending -> done (Coder marks done)."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()

        # Initial: pending
        todos = [{"content": "Use SDK guardrails", "status": "pending"}]
        display.update_todos(todos)
        assert display.todos[0]["status"] == "pending"

        # After Coder executes: done
        todos[0]["status"] = "done"
        display.update_todos(todos)
        assert display.todos[0]["status"] == "done"

    def test_todo_panel_lifecycle_done_to_verified(self):
        """Test todo lifecycle: done -> verified (Reflector verifies)."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()

        # Initial: done
        todos = [{"content": "Use SDK guardrails", "status": "done"}]
        display.update_todos(todos)
        assert display.todos[0]["status"] == "done"

        # After Reflector verifies: verified
        todos[0]["status"] = "verified"
        display.update_todos(todos)
        assert display.todos[0]["status"] == "verified"

    def test_todo_panel_with_add_todo_tool(self):
        """Test add_todo tool creates todos displayed in panel."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")

        # Reflector calls add_todo
        display.tool_call("add_todo", "Use SDK guardrails decorator")
        display.tool_call("add_todo", "Remove manual history management")

        display.end_phase()

        assert len(display.tool_items) == 2
        assert "add_todo → Use SDK guardrails decorator" in display.tool_items[0]
        assert "add_todo → Remove manual history management" in display.tool_items[1]

    def test_todo_panel_with_verify_todo_tool(self):
        """Test verify_todo tool marks todos as verified."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")

        # Reflector calls verify_todo
        display.tool_call("verify_todo", "Use SDK guardrails decorator")
        display.tool_call("get_todos", "1 verified")

        assert len(display.tool_items) == 2
        assert "verify_todo → Use SDK guardrails decorator" in display.tool_items[0]

    def test_handler_updates_todos_via_context_var(self):
        """Test handler syncs todos from ContextVar after Reflector actions."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.agents.tools import current_todos
        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        # Simulate Reflector adding todos via ContextVar
        todos = [
            {"content": "Fix Q&A routes session persistence", "status": "pending"},
            {"content": "Ensure guardrails behavior is preserved", "status": "pending"},
            {"content": "Either use verification_router", "status": "pending"},
        ]
        current_todos.set(todos)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "💎 Reflect"
        handler(start_event)

        end_event = MagicMock()
        end_event.type = "phase.ended"
        handler(end_event)

        assert display.show_todos is True
        assert len(display.todos) == 3
        assert display.todos[0]["content"] == "Fix Q&A routes session persistence"
        assert display.todos[1]["content"] == "Ensure guardrails behavior is preserved"
        assert display.todos[2]["content"] == "Either use verification_router"


class TestCoderTodoPanel:
    """Test Coder phase Todo panel CLI display.

    CLI Output Example (Improve phase):
    ╭─ 🔧 Tools ──────────────────────────────────────────────────────────────╮
    │   ├─ edit → flow.py                                                     │
    │   ├─ exec → python -m py_compile flow.py ✅                             │
    │   ├─ edit → agent_specs.py                                              │
    ╰─────────────────────────────────────────────────────────────────────────╯
    ╭─ 📋 Todos ──────────────────────────────────────────────────────────────╮
    │   [~] Fix Q&A routes session persistence...                             │
    │   [ ] Ensure guardrails behavior is preserved...                        │
    │   [ ] Either use verification_router...                                 │
    ╰─────────────────────────────────────────────────────────────────────────╯
    """

    def test_coder_tools_panel_displays_file_operations(self):
        """Test Coder Tools panel displays file operations."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💫 Improve")
        display.tool_call("edit", "flow.py")
        display.tool_call("exec", "python -m py_compile flow.py ✅")
        display.tool_call("edit", "agent_specs.py")

        assert len(display.tool_items) == 3
        assert "edit → flow.py" in display.tool_items[0]
        assert "exec → python -m py_compile flow.py" in display.tool_items[1]
        assert "edit → agent_specs.py" in display.tool_items[2]

    def test_coder_tools_panel_displays_skill_loads(self):
        """Test Coder Tools panel displays skill loads."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("🚀 Generate")
        display.tool_call("skill", "guardrails")
        display.tool_call("skill", "router")
        display.tool_call("read", "agent_specs.py")

        assert len(display.tool_items) == 3
        assert "skill → guardrails" in display.tool_items[0]
        assert "skill → router" in display.tool_items[1]
        assert "read → agent_specs.py" in display.tool_items[2]

    def test_coder_mark_done_tool_display(self):
        """Test Coder mark_done tool displays in Tools panel."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💫 Improve")
        display.tool_call("edit", "flow.py")
        display.tool_call("mark_done", "Fix Q&A routes session persistence")
        display.tool_call("get_todos", "1 done, 2 pending")

        assert len(display.tool_items) == 3
        assert "mark_done → Fix Q&A routes session persistence" in display.tool_items[1]

    def test_coder_todo_panel_shows_in_progress(self):
        """Test Coder todo panel shows [~] for in-progress items."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        # First, Reflect phase enables todo panel
        display.start_phase("💎 Reflect")
        display.end_phase()

        # Then Improve phase shows todos
        display.start_phase("💫 Improve")

        todos = [
            {"content": "Fix Q&A routes session persistence", "status": "in_progress"},
            {"content": "Ensure guardrails behavior", "status": "pending"},
        ]
        display.update_todos(todos)

        assert display.todos[0]["status"] == "in_progress"
        assert display.todos[1]["status"] == "pending"

    def test_coder_todo_lifecycle_pending_to_in_progress(self):
        """Test todo lifecycle: pending -> in_progress (Coder starts working)."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()
        display.start_phase("💫 Improve")

        # Initial: pending
        todos = [{"content": "Fix Q&A routes", "status": "pending"}]
        display.update_todos(todos)
        assert display.todos[0]["status"] == "pending"

        # Coder starts working: in_progress
        todos[0]["status"] = "in_progress"
        display.update_todos(todos)
        assert display.todos[0]["status"] == "in_progress"

    def test_coder_todo_lifecycle_in_progress_to_done(self):
        """Test todo lifecycle: in_progress -> done (Coder marks done)."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💎 Reflect")
        display.end_phase()
        display.start_phase("💫 Improve")

        # Initial: in_progress
        todos = [{"content": "Fix Q&A routes", "status": "in_progress"}]
        display.update_todos(todos)
        assert display.todos[0]["status"] == "in_progress"

        # Coder completes: done
        todos[0]["status"] = "done"
        display.update_todos(todos)
        assert display.todos[0]["status"] == "done"

    def test_coder_fix_phase_with_todos(self):
        """Test Fix phase displays todos from previous Reflect."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.agents.tools import current_todos
        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        todos = [{"content": "Fix import error", "status": "pending"}]
        current_todos.set(todos)

        # Reflect phase enables todo display
        reflect_start = MagicMock()
        reflect_start.type = "phase.started"
        reflect_start.label = "💎 Reflect"
        handler(reflect_start)

        reflect_end = MagicMock()
        reflect_end.type = "phase.ended"
        handler(reflect_end)

        # Fix phase shows todos
        fix_start = MagicMock()
        fix_start.type = "phase.started"
        fix_start.label = "🔧 Fix"
        handler(fix_start)

        assert display.show_todos is True
        assert display.current_phase == "🔧 Fix"
        panel = display.build_todo_panel()
        assert panel is not None

    def test_coder_reasoning_panel_displays(self):
        """Test Coder Reasoning panel displays thinking."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💫 Improve")
        display.stream_reasoning_delta("**Completing task marking**\n\n")
        display.stream_reasoning_delta("I've finished a task and need to mark it as done...")

        assert display.reasoning_renderer.has_content()
        assert "Completing task marking" in display.reasoning_renderer.buffer
        assert "mark it as done" in display.reasoning_renderer.buffer

    def test_coder_output_panel_displays_edit(self):
        """Test Coder Output panel displays edit arguments."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        display.start_phase("💫 Improve")
        display.start_tool_stream("edit_file")
        display.stream_output_delta('{"path": "agent_specs.py", ')
        display.stream_output_delta('"old_string": "try:\\n", ')
        display.stream_output_delta('"new_string": "try:\\n    from guardrails"}')

        assert display.output_renderer.has_content()
        assert "agent_specs.py" in display.output_renderer.buffer

    def test_full_improve_phase_display(self):
        """Test full Improve phase with Tools + Reasoning + Todos + Output."""
        from rich.console import Console

        from agentic_transcoder.console.display import TranscoderDisplay

        console = Console(force_terminal=True)
        display = TranscoderDisplay(console)

        # Enable todo panel
        display.start_phase("💎 Reflect")
        display.end_phase()

        # Improve phase
        display.start_phase("💫 Improve")

        # Tools
        display.tool_call("edit", "flow.py")
        display.tool_call("exec", "python -m py_compile flow.py ✅")
        display.tool_call("edit", "agent_specs.py")

        # Reasoning
        display.stream_reasoning_delta("**Updating imports and typing**\n\n")
        display.stream_reasoning_delta("I'm considering whether I need to update any imports...")

        # Output
        display.stream_output_delta('{"path": "agent_specs.py", "old_string": "..."}')

        # Update todos
        todos = [
            {"content": "Fix Q&A routes session persistence", "status": "in_progress"},
            {"content": "Ensure guardrails behavior", "status": "pending"},
        ]
        display.update_todos(todos)

        assert display.current_phase == "💫 Improve"
        assert len(display.tool_items) == 3
        assert display.reasoning_renderer.has_content()
        assert display.output_renderer.has_content()
        assert display.show_todos is True
        assert len(display.todos) == 2

        group = display.build_display()
        assert group is not None

    def test_handler_routes_coder_reasoning(self):
        """Test handler routes Coder reasoning to Reasoning panel."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        start_event = MagicMock()
        start_event.type = "phase.started"
        start_event.label = "💫 Improve"
        handler(start_event)

        reasoning_event = MagicMock()
        reasoning_event.type = "raw_response_event"
        reasoning_event.data = MagicMock()
        reasoning_event.data.type = "response.reasoning_summary_text.delta"
        reasoning_event.data.delta = "**Completing task marking**"
        handler(reasoning_event)

        assert display.reasoning_renderer.has_content()
        assert "Completing task marking" in display.reasoning_renderer.buffer

    def test_handler_syncs_todos_during_improve(self):
        """Test handler syncs todos when Improve phase starts."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from agentic_transcoder.agents.tools import current_todos
        from agentic_transcoder.console import create_handler

        console = Console(force_terminal=True)
        display, handler = create_handler(console)

        todos = [
            {"content": "Fix Q&A routes session persistence", "status": "pending"},
            {"content": "Ensure guardrails behavior", "status": "pending"},
        ]
        current_todos.set(todos)

        # Reflect phase enables todo display
        reflect_start = MagicMock()
        reflect_start.type = "phase.started"
        reflect_start.label = "💎 Reflect"
        handler(reflect_start)

        reflect_end = MagicMock()
        reflect_end.type = "phase.ended"
        handler(reflect_end)

        # Update todo status (Coder starts working)
        todos[0]["status"] = "in_progress"

        # Improve phase syncs updated todos
        improve_start = MagicMock()
        improve_start.type = "phase.started"
        improve_start.label = "💫 Improve"
        handler(improve_start)

        assert display.todos[0]["status"] == "in_progress"
        assert display.todos[1]["status"] == "pending"
