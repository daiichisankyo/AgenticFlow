"""Layer 3: Integration tests for AgenticTranscoder.

Intent: Test deploy_template and coder agent with real operations.
deploy_template tests run without API (fast).
coder agent tests require OPENAI_API_KEY (slow, 60-120s).

Philosophy v3 compliant - 1 agent (coder), no legacy agents.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

HAS_API_KEY = bool(os.getenv("OPENAI_API_KEY"))


class TestDeployTemplate:
    """Test deploy_template function (no API required)."""

    def test_deploy_creates_directory(self, tmp_path: Path):
        from agentic_transcoder.agents import deploy_template

        output_dir = tmp_path / "project"
        result = deploy_template(str(output_dir))

        assert output_dir.exists()
        assert "Deployed" in result

    def test_deploy_copies_required_files(self, tmp_path: Path):
        from agentic_transcoder.agents import deploy_template

        output_dir = tmp_path / "project"
        deploy_template(str(output_dir))

        assert (output_dir / "agent_specs.py").exists()
        assert (output_dir / "flow.py").exists()
        assert (output_dir / "server.py").exists()
        assert (output_dir / "store.py").exists()
        assert (output_dir / "pyproject.toml").exists()

    def test_deploy_copies_frontend(self, tmp_path: Path):
        from agentic_transcoder.agents import deploy_template

        output_dir = tmp_path / "project"
        deploy_template(str(output_dir))

        assert (output_dir / "frontend").exists()
        assert (output_dir / "frontend" / "package.json").exists()

    def test_deploy_excludes_node_modules(self, tmp_path: Path):
        from agentic_transcoder.agents import deploy_template

        output_dir = tmp_path / "project"
        deploy_template(str(output_dir))

        # node_modules should never be copied
        assert not (output_dir / "frontend" / "node_modules").exists()

    def test_deploy_copies_tests(self, tmp_path: Path):
        from agentic_transcoder.agents import deploy_template

        output_dir = tmp_path / "project"
        deploy_template(str(output_dir))

        assert (output_dir / "tests").exists()
        assert (output_dir / "tests" / "test_flow.py").exists()
        assert (output_dir / "tests" / "test_server.py").exists()

    def test_deploy_fails_if_exists(self, tmp_path: Path):
        from agentic_transcoder.agents import deploy_template

        output_dir = tmp_path / "project"
        output_dir.mkdir()

        result = deploy_template(str(output_dir))

        assert "Error" in result
        assert "already exists" in result

    def test_deploy_excludes_pycache(self, tmp_path: Path):
        from agentic_transcoder.agents import deploy_template

        output_dir = tmp_path / "project"
        deploy_template(str(output_dir))

        # __pycache__ should never be copied
        pycache_dirs = list(output_dir.rglob("__pycache__"))
        assert len(pycache_dirs) == 0

    def test_deploy_renames_tmpl_files(self, tmp_path: Path):
        from agentic_transcoder.agents import deploy_template

        output_dir = tmp_path / "project"
        deploy_template(str(output_dir))

        # .tmpl files should be renamed (suffix removed)
        tmpl_files = list(output_dir.rglob("*.tmpl"))
        assert len(tmpl_files) == 0

        # App.tsx should exist (renamed from App.tsx.tmpl)
        assert (output_dir / "frontend" / "src" / "App.tsx").exists()


class TestKnowledgeLoading:
    """Test dynamic knowledge loading (no API required)."""

    def test_load_knowledge_returns_string(self):
        from agentic_transcoder.agents import load_knowledge

        content = load_knowledge()

        assert isinstance(content, str)
        assert len(content) > 0

    def test_load_knowledge_contains_guidelines(self):
        from agentic_transcoder.agents import load_knowledge

        content = load_knowledge()

        # Should contain agentic-flow-guidelines content
        assert "agentic-flow-guidelines" in content or "Agentic Flow" in content

    def test_load_docs_returns_string(self):
        from agentic_transcoder.agents import load_docs

        content = load_docs()

        assert isinstance(content, str)

    def test_load_source_returns_string(self):
        from agentic_transcoder.agents import load_source

        content = load_source()

        assert isinstance(content, str)


class TestCoderAgentStructure:
    """Test coder agent structure (no API required)."""

    def test_coder_has_file_tools(self):
        from agentic_transcoder.agents import coder

        tools = coder.sdk_kwargs.get("tools", [])
        tool_names = [t.name for t in tools]

        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "list_files" in tool_names
        assert "exec_command" in tool_names

    def test_coder_instructions_contain_knowledge(self):
        from agentic_transcoder.agents import CODER_INSTRUCTIONS

        assert "Agentic Flow" in CODER_INSTRUCTIONS
        assert "agent_specs.py" in CODER_INSTRUCTIONS
        assert "gpt-5.2" in CODER_INSTRUCTIONS


@pytest.mark.skipif(not HAS_API_KEY, reason="OPENAI_API_KEY not set")
@pytest.mark.timeout(120)
class TestCoderAgentAPI:
    """Test coder agent with real API (60-120s per test)."""

    @pytest.mark.asyncio
    async def test_coder_returns_string(self):
        from agentic_transcoder.agents import coder

        result = await coder("Say hello").max_turns(3).stream()

        assert isinstance(result, str)
        assert len(result) > 0
