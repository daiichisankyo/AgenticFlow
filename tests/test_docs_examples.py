"""Test documentation code examples for syntax correctness.

This ensures all code examples in docs/examples/ are valid Python.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DOCS_EXAMPLES_DIR = Path(__file__).parent.parent / "docs" / "examples"


def get_example_files() -> list[Path]:
    """Get all Python files in docs/examples/."""
    if not DOCS_EXAMPLES_DIR.exists():
        return []
    return sorted(DOCS_EXAMPLES_DIR.glob("*.py"))


@pytest.mark.parametrize(
    "example_file",
    get_example_files(),
    ids=lambda p: p.name,
)
def test_example_syntax(example_file: Path) -> None:
    """Verify each example file has valid Python syntax."""
    source = example_file.read_text()
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"Syntax error in {example_file.name}: {e}")


@pytest.mark.parametrize(
    "example_file",
    get_example_files(),
    ids=lambda p: p.name,
)
def test_example_compiles(example_file: Path) -> None:
    """Verify each example file compiles without errors."""
    source = example_file.read_text()
    try:
        compile(source, example_file, "exec")
    except SyntaxError as e:
        pytest.fail(f"Compilation error in {example_file.name}: {e}")


def test_examples_exist() -> None:
    """Verify at least one example file exists."""
    files = get_example_files()
    assert len(files) > 0, "No example files found in docs/examples/"


def test_line_counts() -> None:
    """Verify line counts match documented values."""
    expected_counts = {
        "pure_sdk_chatkit.py": (110, 130),
        "agenticflow_flow.py": (35, 45),
        "agenticflow_chatkit.py": (15, 25),
        "agenticflow_cli.py": (10, 18),
    }

    for filename, (min_lines, max_lines) in expected_counts.items():
        filepath = DOCS_EXAMPLES_DIR / filename
        if not filepath.exists():
            pytest.skip(f"{filename} not found")

        lines = len(filepath.read_text().strip().splitlines())
        assert min_lines <= lines <= max_lines, (
            f"{filename}: expected {min_lines}-{max_lines} lines, got {lines}"
        )
