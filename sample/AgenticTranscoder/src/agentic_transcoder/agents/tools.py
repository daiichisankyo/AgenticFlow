"""Tools for coder agent.

Intent: File operations, template deployment, and Todo management.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from agents import function_tool

current_todos: ContextVar[list[dict[str, Any]]] = ContextVar("todos", default=[])

MODULE_ROOT = Path(__file__).parent.parent
KNOWLEDGE_ROOT = MODULE_ROOT / "knowledge"
TEMPLATE_ROOT = MODULE_ROOT / "template"
EXAMPLES_ROOT = MODULE_ROOT.parent.parent / "examples"
LIBRARY_ROOT = MODULE_ROOT.parent.parent.parent.parent
DOCS_DIR = LIBRARY_ROOT / "docs" / "en"
SRC_DIR = LIBRARY_ROOT / "src" / "agentic_flow"


def load_knowledge() -> str:
    """Load essential knowledge files only.

    Only loads agentic-flow-guidelines.md.
    transformation-rules.md is redundant with Skills (BEFORE/AFTER patterns).
    chatkit-integration.md is covered by Template files.
    """
    guidelines = KNOWLEDGE_ROOT / "agentic-flow-guidelines.md"
    if guidelines.exists():
        return f"# Agentic Flow Guidelines\n\n{guidelines.read_text()}"
    return ""


def load_docs() -> str:
    """Load core design philosophy from concepts/index.md.

    This contains the essential mental model:
    - Call-Spec Discipline (declaration != execution)
    - 5-Axis Model (WHAT/WHERE/HOW/LIMITS/WHEN)
    - Design principles

    Detailed docs (phase.md, modifiers.md) are learned via Skills.
    """
    concepts_index = DOCS_DIR / "concepts" / "index.md"
    if concepts_index.exists():
        return f"## Agentic Flow Design Philosophy\n\n{concepts_index.read_text()}"
    return ""


def load_source() -> str:
    """Load public API exports only.

    Full source code is too large for context window.
    Skills (BEFORE/AFTER) provide sufficient examples.
    """
    init_file = SRC_DIR / "__init__.py"
    if init_file.exists():
        return f"## Public API (__init__.py)\n\n```python\n{init_file.read_text()}```"
    return ""


def load_skills_catalog() -> str:
    """Load SKILLS.md catalog only (not skill content).

    Intent: Provide coder with skill catalog for pattern selection.
    Actual skill content is loaded on demand via load_skill() tool.
    """
    skills_md = EXAMPLES_ROOT / "SKILLS.md"
    return skills_md.read_text() if skills_md.exists() else ""


def load_single_skill(skill_dir: Path) -> str:
    """Load a single skill's BEFORE/AFTER files and tests.

    Each skill contains:
    - source.py: BEFORE (AgentBuilder format)
    - flow.py: AFTER (Agentic Flow flow)
    - agent_specs.py: AFTER (Agentic Flow agents)
    - tests/: Test patterns for this skill
    """
    parts = [f"\n### Skill: {skill_dir.name}\n"]

    source_file = skill_dir / "source.py"
    if source_file.exists():
        parts.append(f"""
#### BEFORE (AgentBuilder) - {skill_dir.name}/source.py
```python
{source_file.read_text()}
```
""")

    flow_file = skill_dir / "flow.py"
    if flow_file.exists():
        parts.append(f"""
#### AFTER (flow.py) - {skill_dir.name}/flow.py
```python
{flow_file.read_text()}
```
""")

    agents_file = skill_dir / "agent_specs.py"
    if agents_file.exists():
        parts.append(f"""
#### AFTER (agent_specs.py) - {skill_dir.name}/agent_specs.py
```python
{agents_file.read_text()}
```
""")

    tests_dir = skill_dir / "tests"
    if tests_dir.exists():
        for test_file in sorted(tests_dir.glob("test_*.py")):
            parts.append(f"""
#### TESTS - {skill_dir.name}/tests/{test_file.name}
```python
{test_file.read_text()}
```
""")

    return "\n".join(parts) if len(parts) > 1 else ""


@function_tool
async def load_skill(skill_name: str) -> str:
    """Load skill BEFORE/AFTER pair and tests by directory name.

    Intent: Provide complete transformation pattern including test examples.

    Args:
        skill_name: Directory name from examples/ (basic, websearch, guardrail, router)

    Returns:
        BEFORE (source.py) + AFTER (flow.py, agent_specs.py) + tests/ patterns
    """
    skill_dir = EXAMPLES_ROOT / skill_name
    if not skill_dir.exists():
        available = [
            d.name for d in EXAMPLES_ROOT.iterdir() if d.is_dir() and (d / "source.py").exists()
        ]
        return f"Error: Skill '{skill_name}' not found. Available: {', '.join(available)}"
    return load_single_skill(skill_dir)


KNOWLEDGE_CONTENT = load_knowledge()
DOCS_CONTENT = load_docs()
SOURCE_CONTENT = load_source()
SKILLS_CATALOG = load_skills_catalog()


@function_tool
async def read_file(path: str, cwd: str) -> str:
    """Read a file's contents. Path must be within cwd.

    Intent: Returns raw content for string-match editing.
    No line numbers needed since edit_file uses string matching.
    """
    if not cwd:
        return "Error: cwd is required. You can only read files in the project directory."

    cwd_path = Path(cwd).resolve()
    if os.path.isabs(path):
        full_path = Path(path).resolve()
    else:
        full_path = (cwd_path / path).resolve()

    try:
        full_path.relative_to(cwd_path)
    except ValueError:
        return f"Error: Cannot read files outside project directory. Path must be within {cwd}"

    try:
        if not full_path.exists():
            return f"Error: File not found: {full_path}"

        return full_path.read_text()
    except Exception as e:
        return f"Error reading file: {e}"


@function_tool
async def write_file(path: str, content: str, cwd: str = "") -> str:
    """Write content to a file."""
    try:
        if cwd and not os.path.isabs(path):
            full_path = Path(cwd) / path
        else:
            full_path = Path(path)

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

        return f"Written: {full_path} ({len(content)} bytes)"
    except Exception as e:
        return f"Error writing file: {e}"


@function_tool
async def edit_file(path: str, old_string: str, new_string: str, cwd: str = "") -> str:
    """Replace a unique string in a file.

    Intent: String-match editing is safer than line-number editing.
    - Line numbers shift after edits; strings don't
    - LLMs are better at pattern matching than counting
    - Unique match requirement prevents accidental edits

    Args:
        path: File path (relative to cwd)
        old_string: Exact string to find and replace (must be unique)
        new_string: Replacement string
        cwd: Working directory

    Returns:
        Success message or error if old_string not found/not unique
    """
    try:
        if cwd and not os.path.isabs(path):
            full_path = Path(cwd) / path
        else:
            full_path = Path(path)

        if not full_path.exists():
            return f"Error: File not found: {full_path}"

        content = full_path.read_text()

        count = content.count(old_string)
        if count == 0:
            preview = old_string[:100] + "..." if len(old_string) > 100 else old_string
            return f"Error: String not found in {path}:\n{preview}"
        if count > 1:
            return f"Error: String appears {count} times. Must be unique. Add more context."

        new_content = content.replace(old_string, new_string, 1)
        full_path.write_text(new_content)

        old_lines = old_string.count("\n") + 1
        new_lines = new_string.count("\n") + 1
        delta = new_lines - old_lines
        delta_str = f"+{delta}" if delta > 0 else str(delta) if delta < 0 else "±0"

        return f"Edited {path}: {old_lines} → {new_lines} lines ({delta_str})"
    except Exception as e:
        return f"Error editing file: {e}"


@function_tool
async def list_files(path: str = ".", cwd: str = "", pattern: str = "*") -> str:
    """List files in a directory. Path must be within cwd."""
    if not cwd:
        return "Error: cwd is required. You can only list files in the project directory."

    cwd_path = Path(cwd).resolve()
    if os.path.isabs(path):
        full_path = Path(path).resolve()
    else:
        full_path = (cwd_path / path).resolve()

    try:
        full_path.relative_to(cwd_path)
    except ValueError:
        return f"Error: Cannot list files outside project directory. Path must be within {cwd}"

    try:
        if not full_path.exists():
            return f"Error: Directory not found: {full_path}"

        files = []
        for item in full_path.glob(pattern):
            if item.is_file():
                files.append(str(item.relative_to(full_path)))
            elif item.is_dir():
                files.append(f"{item.relative_to(full_path)}/")

        return "\n".join(sorted(files)) if files else "(empty)"
    except Exception as e:
        return f"Error listing files: {e}"


@function_tool
async def exec_command(command: str, cwd: str = "") -> str:
    """Execute a shell command.

    Allowed commands:
    - python -m py_compile <file>: Syntax verification
    - pytest: Test execution
    - uv add <package>: Add dependency to pyproject.toml
    """
    is_py_compile = "py_compile" in command and command.strip().startswith("python")
    is_pytest = command.strip().startswith("pytest")
    is_uv_add = command.strip().startswith("uv add")

    if not (is_py_compile or is_pytest or is_uv_add):
        return "Error: Only 'python -m py_compile', 'pytest', and 'uv add' are allowed."

    try:
        cwd_path = Path(cwd) if cwd else None

        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd_path) if cwd_path else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()
        output = stdout.decode() + stderr.decode()

        if proc.returncode == 0:
            return f"Success (exit 0):\n{output[:2000]}"
        else:
            return f"Failed (exit {proc.returncode}):\n{output[:2000]}"
    except Exception as e:
        return f"Error executing command: {e}"


@function_tool
async def get_todos() -> str:
    """Get current todo list with status.

    Returns:
        Formatted list with status markers:
        - [ ] pending: Not started
        - [~] done: Marked done by Coder (awaiting Reflector verification)
        - [v] verified: Verified complete by Reflector
    """
    todos = current_todos.get()
    if not todos:
        return "No todos."

    lines = []
    for i, todo in enumerate(todos, 1):
        status = todo.get("status", "pending")
        content = todo.get("content", "")
        mark = {"pending": "[ ]", "done": "[~]", "verified": "[v]"}.get(status, "[ ]")
        lines.append(f"{i}. {mark} {content}")

    return "\n".join(lines)


@function_tool
async def mark_done(content: str) -> str:
    """Mark a todo item as done (Coder reports completion).

    Intent: Coder calls this AFTER completing the work.
    Reflector will verify the work in the next Reflect phase.

    Args:
        content: Partial content to match (case-insensitive substring match)

    Returns:
        Success message or error if not found
    """
    todos = current_todos.get()
    content_lower = content.lower()

    for todo in todos:
        if content_lower in todo.get("content", "").lower():
            if todo.get("status") == "verified":
                return f"Already verified: {todo['content']}"
            todo["status"] = "done"
            return f"Marked done: {todo['content']}"

    return f"Error: No todo matching '{content}'"


@function_tool
async def add_todo(content: str) -> str:
    """Add a new todo item (Reflector creates improvement tasks).

    Intent: Reflector identifies issues and creates todos for Coder to fix.

    Args:
        content: Clear, actionable description of what to fix

    Returns:
        Confirmation message
    """
    todos = current_todos.get()
    todos.append({"content": content, "status": "pending"})
    return f"Added todo: {content}"


@function_tool
async def verify_todo(content: str, verified: bool = True) -> str:
    """Verify a todo item (Reflector confirms completion).

    Intent: Reflector checks if Coder's work actually resolves the issue.

    Args:
        content: Partial content to match
        verified: True if work is complete, False to reset to pending

    Returns:
        Status message
    """
    todos = current_todos.get()
    content_lower = content.lower()

    for todo in todos:
        if content_lower in todo.get("content", "").lower():
            if verified:
                todo["status"] = "verified"
                return f"Verified: {todo['content']}"
            else:
                todo["status"] = "pending"
                return f"Reset to pending: {todo['content']}"

    return f"Error: No todo matching '{content}'"


def deploy_template(output_dir: str) -> str:
    """Deploy template to output directory.

    Copies template files (excluding frontend/node_modules) to output_dir.
    Renames .tmpl files by removing the .tmpl suffix.
    Runs uv sync to create .venv for coder's exec_command.
    Frontend requires clean npm install after deployment.

    Args:
        output_dir: Target directory for deployment

    Returns:
        Status message
    """
    import subprocess

    output_path = Path(output_dir)

    if output_path.exists():
        return f"Error: Output directory already exists: {output_dir}"

    output_path.mkdir(parents=True)

    for item in TEMPLATE_ROOT.iterdir():
        if item.name == "__pycache__":
            continue

        dst = output_path / item.name

        if item.is_dir():
            if item.name == "frontend":
                shutil.copytree(
                    item,
                    dst,
                    ignore=shutil.ignore_patterns("node_modules", ".next", "dist"),
                )
            else:
                shutil.copytree(item, dst)
        else:
            shutil.copy2(item, dst)

    for tmpl_file in output_path.rglob("*.tmpl"):
        target = tmpl_file.with_suffix("")
        tmpl_file.rename(target)

    subprocess.run(
        ["uv", "sync", "--all-extras"],
        cwd=str(output_path),
        capture_output=True,
    )

    return f"Deployed template to {output_dir}"
