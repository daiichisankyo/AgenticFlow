"""Layer 1: Structure tests for AgenticTranscoder.

Intent: Verify module structure without API calls.
- Module imports work
- Agent definitions valid (1 coder agent)
- Pydantic types parse (RunResult, TestError only)
- Function signatures correct

Philosophy v3 compliant - no legacy agents or types.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path


class TestAgents:
    """Test agents.py module - single coder agent."""

    def test_coder_agent_exists(self):
        from agentic_transcoder.agents import coder

        assert coder.sdk_kwargs.get("name") == "coder"

    def test_coder_has_correct_model(self):
        from agentic_transcoder.agents import coder

        assert coder.sdk_kwargs.get("model") == "gpt-5.2"

    def test_coder_has_reasoning_high(self):
        from agentic_transcoder.agents import coder

        model_settings = coder.sdk_kwargs.get("model_settings")
        assert model_settings is not None
        assert model_settings.reasoning is not None
        assert model_settings.reasoning.effort == "high"

    def test_coder_has_file_tools(self):
        from agentic_transcoder.agents import coder

        tools = coder.sdk_kwargs.get("tools", [])
        tool_names = [t.name for t in tools]
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "list_files" in tool_names
        assert "exec_command" in tool_names

    def test_deploy_template_function_exists(self):
        from agentic_transcoder.agents import deploy_template

        assert callable(deploy_template)

    def test_deploy_template_signature(self):
        from agentic_transcoder.agents import deploy_template

        sig = inspect.signature(deploy_template)
        params = list(sig.parameters.keys())
        assert "output_dir" in params


class TestTypes:
    """Test types.py - RunResult and TestError only."""

    def test_run_result_model(self):
        from agentic_transcoder.types import RunResult

        result = RunResult(passed=True, total=5, failed_count=0)
        assert result.passed is True
        assert result.failed is False
        assert result.errors == []

    def test_run_result_failed_property(self):
        from agentic_transcoder.types import RunResult

        result = RunResult(passed=False, total=3, failed_count=2)
        assert result.failed is True
        assert result.passed is False

    def test_test_error_model(self):
        from agentic_transcoder.types import TestError

        error = TestError(file="test.py", line=10, message="Failed")
        assert error.file == "test.py"
        assert error.line == 10
        assert error.message == "Failed"

    def test_test_error_optional_fields(self):
        from agentic_transcoder.types import TestError

        error = TestError(file="test.py", message="Failed")
        assert error.line is None
        assert error.traceback is None

    def test_run_result_with_errors(self):
        from agentic_transcoder.types import RunResult, TestError

        result = RunResult(
            passed=False,
            total=3,
            failed_count=2,
            errors=[
                TestError(file="test_flow.py", message="AssertionError"),
                TestError(file="test_server.py", line=42, message="ConnectionError"),
            ],
        )
        assert len(result.errors) == 2


class TestFlow:
    """Test flow.py - Transcoder class and 2 phases."""

    def test_transcoder_class_exists(self):
        from agentic_transcoder.flow import Transcoder

        assert Transcoder is not None

    def test_transcoder_init_params(self):
        from agentic_transcoder.flow import Transcoder

        sig = inspect.signature(Transcoder.__init__)
        params = list(sig.parameters.keys())
        assert "source_code" in params
        assert "output_dir" in params
        # with_frontend is REMOVED (frontend mandatory)
        assert "with_frontend" not in params

    def test_transcoder_flow_method(self):
        from agentic_transcoder.flow import Transcoder

        r = Transcoder("source", "/tmp/out")
        assert hasattr(r, "flow")
        assert asyncio.iscoroutinefunction(r.flow)

    def test_transcoder_runner_method(self):
        from agentic_flow import Runner

        from agentic_transcoder.flow import Transcoder

        r = Transcoder("source", "/tmp/out")
        assert hasattr(r, "runner")
        runner = r.runner()
        assert isinstance(runner, Runner)

    def test_transcoder_returns_run_result(self):
        from agentic_transcoder.flow import Transcoder
        from agentic_transcoder.types import RunResult

        hints = inspect.get_annotations(Transcoder.flow)
        assert hints.get("return") in ("RunResult", RunResult)

    def test_transcode_function_exists(self):
        from agentic_transcoder.flow import transcode

        assert callable(transcode)

    def test_transcode_is_async(self):
        from agentic_transcoder.flow import transcode

        assert asyncio.iscoroutinefunction(transcode)

    def test_transcode_signature(self):
        from agentic_transcoder.flow import transcode

        sig = inspect.signature(transcode)
        params = list(sig.parameters.keys())
        assert "source_code" in params
        assert "output_dir" in params
        # with_frontend is REMOVED (frontend mandatory)
        assert "with_frontend" not in params

    def test_runner_exists(self):
        from agentic_transcoder.flow import runner

        assert runner is not None


class TestPrompts:
    """Test prompt templates in agents/coder/instructions.py."""

    def test_generate_prompt_exists(self):
        from agentic_transcoder.agents.coder import GENERATE_PROMPT

        assert GENERATE_PROMPT is not None
        assert len(GENERATE_PROMPT) > 0

    def test_generate_prompt_has_placeholders(self):
        from agentic_transcoder.agents.coder import GENERATE_PROMPT

        assert "{output_dir}" in GENERATE_PROMPT
        assert "{source_code}" in GENERATE_PROMPT

    def test_generate_prompt_is_formattable(self):
        from agentic_transcoder.agents.coder import GENERATE_PROMPT

        result = GENERATE_PROMPT.format(
            output_dir="/tmp/test",
            source_code="from agents import Agent",
        )
        assert "/tmp/test" in result
        assert "from agents import Agent" in result


class TestTools:
    """Test tools.py module - Pure functions."""

    def test_run_tests_exists(self):
        from agentic_transcoder.tools import run_tests

        assert callable(run_tests)
        assert asyncio.iscoroutinefunction(run_tests)

    def test_format_errors_function(self):
        from agentic_transcoder.tools import format_errors
        from agentic_transcoder.types import TestError

        errors = [
            TestError(file="test.py", line=10, message="Failed"),
            TestError(file="server.py", message="Timeout"),
        ]
        result = format_errors(errors)
        assert "test.py:10" in result
        assert "server.py:" in result

    def test_format_errors_empty(self):
        from agentic_transcoder.tools import format_errors

        result = format_errors([])
        assert result == "(none)"


class TestPublicAPI:
    """Test __init__.py public API - v3 exports."""

    def test_coder_exported(self):
        from agentic_transcoder import coder

        assert coder is not None

    def test_deploy_template_exported(self):
        from agentic_transcoder import deploy_template

        assert deploy_template is not None
        assert callable(deploy_template)

    def test_flow_exported(self):
        from agentic_transcoder import Transcoder, runner, transcode

        assert Transcoder is not None
        assert callable(transcode)
        assert runner is not None

    def test_types_exported(self):
        from agentic_transcoder import RunResult, TestError

        assert RunResult is not None
        assert TestError is not None

    def test_legacy_agents_not_exported(self):
        import agentic_transcoder

        # analyzer, planner, critic are REMOVED
        assert not hasattr(agentic_transcoder, "analyzer")
        assert not hasattr(agentic_transcoder, "planner")
        assert not hasattr(agentic_transcoder, "critic")

    def test_legacy_types_not_exported(self):
        import agentic_transcoder

        # Verdict, Diagnosis, TestPlan are REMOVED
        assert not hasattr(agentic_transcoder, "Verdict")
        assert not hasattr(agentic_transcoder, "Diagnosis")
        assert not hasattr(agentic_transcoder, "TestPlan")


class TestDirectories:
    """Test required directories exist."""

    def test_knowledge_directory_exists(self):
        knowledge_dir = Path(__file__).parent.parent / "src" / "agentic_transcoder" / "knowledge"
        assert knowledge_dir.exists()

    def test_template_directory_exists(self):
        template_dir = Path(__file__).parent.parent / "src" / "agentic_transcoder" / "template"
        assert template_dir.exists()

    def test_template_has_required_files(self):
        template_dir = Path(__file__).parent.parent / "src" / "agentic_transcoder" / "template"
        assert (template_dir / "agent_specs.py").exists()
        assert (template_dir / "flow.py").exists()
        assert (template_dir / "server.py").exists()
        assert (template_dir / "frontend").exists()

    def test_fixtures_directory_exists(self):
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        assert fixtures_dir.exists()


class TestConsole:
    """Test console module for CLI output."""

    def test_console_module_exists(self):
        from agentic_transcoder.console import display, handler

        assert hasattr(display, "TranscoderDisplay")
        assert hasattr(handler, "create_handler")

    def test_create_handler_returns_tuple(self):
        from rich.console import Console

        from agentic_transcoder.console import create_handler

        console = Console()
        disp, hdlr = create_handler(console)

        assert disp is not None
        assert callable(hdlr)

    def test_phase_labels_for_five_phases(self):
        from agentic_transcoder.console.display import TranscoderDisplay

        assert "🚀 Generate" in TranscoderDisplay.PHASE_LABELS
        assert "💫 Improve" in TranscoderDisplay.PHASE_LABELS
        assert "🔧 Fix" in TranscoderDisplay.PHASE_LABELS
        assert "🧪 Test" in TranscoderDisplay.PHASE_LABELS
        assert "💎 Reflect" in TranscoderDisplay.PHASE_LABELS
