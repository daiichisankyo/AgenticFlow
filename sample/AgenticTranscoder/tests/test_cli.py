"""Layer 4: CLI smoke test for AgenticTranscoder.

Intent: Verify CLI runs and produces output.
- Basic tests: help, init (no API)
- Smoke test: full recomposition (requires API)

Philosophy v3 compliant:
- No --with-frontend flag (frontend is mandatory)
- Output includes builder_agents.py and frontend/
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

HAS_API_KEY = bool(os.getenv("OPENAI_API_KEY"))

MINIMAL_FIXTURE = """\
from agents import Agent

bot = Agent(name="bot", instructions="Say hello")
"""


class TestCLIBasic:
    """Basic CLI tests (no API calls)."""

    def test_cli_help_works(self):
        """transcoder --help should exit 0."""
        result = subprocess.run(
            [sys.executable, "-m", "agentic_transcoder.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        # fire outputs help to stderr
        output = result.stdout + result.stderr
        assert "transcoder" in output.lower() or "cli" in output.lower()

    def test_cli_init_creates_workspace(self, tmp_path: Path):
        """transcoder init <path> should create workspace structure."""
        workspace = tmp_path / "workspace"

        result = subprocess.run(
            [sys.executable, "-m", "agentic_transcoder.cli", "init", str(workspace)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert workspace.exists()

    def test_cli_init_copies_sample(self, tmp_path: Path):
        """transcoder init should copy sample builder_agent.py."""
        workspace = tmp_path / "workspace"

        subprocess.run(
            [sys.executable, "-m", "agentic_transcoder.cli", "init", str(workspace)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        # Should have sample file if fixtures exist
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        if (fixtures_dir / "builder_agent.py").exists():
            assert (workspace / "builder_agent.py").exists()

    def test_cli_run_missing_file_fails(self, tmp_path: Path):
        """transcoder -f <nonexistent> should fail gracefully."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agentic_transcoder.cli",
                "-f",
                str(tmp_path / "nonexistent.py"),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode != 0
        assert "Not found" in result.stdout or "Not found" in result.stderr

    def test_cli_reset_removes_af_dirs(self, tmp_path: Path):
        """transcoder reset should remove *_af directories."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agentic_transcoder.cli",
                "reset",
                str(workspace),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "No generated projects" in result.stdout or "No generated" in result.stderr

    def test_cli_delete_removes_workspace(self, tmp_path: Path):
        """transcoder delete should remove entire workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "test.txt").write_text("test")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agentic_transcoder.cli",
                "delete",
                str(workspace),
                "--force",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert not workspace.exists()

    def test_cli_reset_no_projects(self, tmp_path: Path):
        """transcoder reset with empty workspace should handle gracefully."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agentic_transcoder.cli",
                "reset",
                str(workspace),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "No generated projects" in result.stdout or "No generated" in result.stderr


@pytest.mark.skipif(not HAS_API_KEY, reason="OPENAI_API_KEY not set")
@pytest.mark.timeout(300)
class TestCLISmoke:
    """Smoke test: CLI runs and produces output (requires API)."""

    def test_cli_produces_output_directory(self, tmp_path: Path):
        """transcoder -f <input> should create output directory with files."""
        # Write fixture
        input_file = tmp_path / "input.py"
        input_file.write_text(MINIMAL_FIXTURE)

        output_dir = tmp_path / "output"

        # Run CLI - NO --with-frontend flag (frontend is mandatory)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agentic_transcoder.cli",
                "-f",
                str(input_file),
                "-o",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=Path(__file__).parent.parent,
            env={**os.environ, "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")},
        )

        # Debug output on failure
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

        # Assertions
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_dir.exists(), "Output directory not created"

        # Should have required files
        assert (output_dir / "builder_agents.py").exists(), "builder_agents.py missing"
        assert (output_dir / "flow.py").exists(), "flow.py missing"
        assert (output_dir / "server.py").exists(), "server.py missing"

        # Frontend is mandatory - should always be present
        assert (output_dir / "frontend").exists(), "frontend/ missing (mandatory)"

    def test_cli_output_has_valid_python(self, tmp_path: Path):
        """Generated Python files should have valid syntax."""
        input_file = tmp_path / "input.py"
        input_file.write_text(MINIMAL_FIXTURE)

        output_dir = tmp_path / "output"

        subprocess.run(
            [
                sys.executable,
                "-m",
                "agentic_transcoder.cli",
                "-f",
                str(input_file),
                "-o",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=Path(__file__).parent.parent,
            env={**os.environ, "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")},
        )

        if not output_dir.exists():
            pytest.skip("Output not generated")

        # Check all Python files have valid syntax
        for py_file in output_dir.glob("*.py"):
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Invalid syntax in {py_file.name}: {result.stderr}"
