"""Tool output parsing.

Intent: Parse tool outputs into display-friendly format.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToolResult:
    """Parsed tool result for display."""

    tool_name: str
    summary: str


def shorten_path(full_path: str, keep_parts: int = 2) -> str:
    """Shorten path to last N parts."""
    path_parts = full_path.split("/")
    if len(path_parts) > keep_parts:
        return "/".join(path_parts[-keep_parts:])
    return full_path


def parse_tool_output(tool_name: str, output: str, pending_cmd: str = "") -> ToolResult | None:
    """Parse tool output into display-friendly format.

    Args:
        tool_name: Name of the tool that produced output
        output: Raw output string from tool
        pending_cmd: Pending exec command (for exec_command tool)

    Returns:
        ToolResult with display-friendly name and summary, or None if should skip
    """
    if output.startswith("Written:"):
        parts = output.split(" ", 1)
        if len(parts) > 1:
            full_path = parts[1].split(" ")[0]
            short_path = shorten_path(full_path)
            return ToolResult("write", short_path)

    if output.startswith("Edited"):
        file_part = output.split(":")[0].replace("Edited ", "")
        return ToolResult("edit", file_part)

    if output.startswith("Error:"):
        error_msg = output[6:].strip()[:40]
        return ToolResult(tool_name, f"[red]{error_msg}[/red]")

    if output.startswith("Success"):
        return ToolResult("exec", f"{pending_cmd} ✅")

    if output.startswith("Failed"):
        return ToolResult("exec", f"{pending_cmd} ❌")

    if "### Skill:" in output:
        skill_match = output.split("### Skill:")[1].split("\n")[0].strip()
        return ToolResult("skill", skill_match)

    if len(output) < 100:
        return ToolResult(tool_name, output[:50])

    return None
