"""Display rendering with Rich.

Intent: Rich Live display for real-time CLI updates.
Layout: Multi-panel (Tools + Reasoning + Output).

Features:
- Dual stream rendering (reasoning + output)
- Content-type aware rendering (text, markdown, json)
- JSON incremental parsing with fallback
"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING, Any

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

if TYPE_CHECKING:
    from ..types import ContentType, RunResult

SPINNER_FRAMES = ["◐", "◑", "◒", "◓"]

PANEL_WIDTH = 100
MAX_TOOL_ITEMS = 12
MAX_STREAM_LINES = 30


def sanitize_text(text: str) -> str:
    """Remove control characters and unicode escapes from text.

    Handles:
    - Unicode escape sequences like \\u007f
    - Control characters like \\x7f (DEL) and \\x08 (backspace)
    - Non-printable characters
    """
    clean = re.sub(r"\\u[0-9a-fA-F]{4}", "", text)
    clean = "".join(c for c in clean if (c.isprintable() or c in "\n\t") and c not in "\x7f\x08")
    return clean


class StreamRenderer:
    """Content-type aware stream renderer.

    Intent:
    - text: plain text with line limiting
    - markdown: Rich Markdown rendering
    - json: JSONDecoder.raw_decode for incremental parsing
    """

    def __init__(self, content_type: ContentType = "text") -> None:
        self.buffer = ""
        self.content_type: ContentType = content_type
        self.json_decoder = json.JSONDecoder()
        self.last_valid_json: Any = None

    def clear(self) -> None:
        """Clear buffer and reset state."""
        self.buffer = ""
        self.last_valid_json = None

    def set_content_type(self, content_type: ContentType) -> None:
        """Set content type and reset buffer."""
        self.content_type = content_type
        self.clear()

    def append(self, delta: str) -> None:
        """Append delta to buffer."""
        self.buffer += sanitize_text(delta)

        if self.content_type == "json":
            self.try_parse_json()

    def has_content(self) -> bool:
        """Check if buffer has content."""
        return bool(self.buffer.strip())

    def try_parse_json(self) -> None:
        """Try to parse JSON from buffer.

        Uses raw_decode to handle:
        - Complete JSON objects
        - NDJSON (multiple objects)
        - Incomplete JSON (wait for more)
        """
        buf = self.buffer.strip()
        if not buf:
            return

        try:
            obj, _ = self.json_decoder.raw_decode(buf)
            self.last_valid_json = obj
        except json.JSONDecodeError:
            pass

    def render(self, max_lines: int = MAX_STREAM_LINES) -> RenderableType:
        """Render buffer based on content type."""
        if not self.has_content():
            return Text.from_markup("[dim]...[/dim]")

        if self.content_type == "text":
            return self.render_text(max_lines)
        elif self.content_type == "markdown":
            return self.render_markdown()
        elif self.content_type == "json":
            return self.render_json()
        return Text(self.buffer)

    def render_text(self, max_lines: int) -> Text:
        """Plain text with line limiting."""
        preview = self.buffer[-800:]
        if len(self.buffer) > 800:
            preview = "..." + preview
        lines = preview.split("\n")
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return Text("\n".join(lines))

    def render_markdown(self, max_lines: int = MAX_STREAM_LINES) -> Markdown:
        """Markdown rendering with size limiting.

        Note: Incomplete code blocks may render oddly.
        Acceptable during streaming.
        """
        preview = self.buffer[-2000:]
        if len(self.buffer) > 2000:
            preview = "...\n" + preview
        lines = preview.split("\n")
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return Markdown("\n".join(lines))

    def render_json(self, max_lines: int = MAX_STREAM_LINES) -> RenderableType:
        """JSON rendering with size limiting.

        - If parseable: RichJSON with colors (truncated if large)
        - If incomplete: Syntax highlighting on raw text
        """
        preview = self.buffer[-3000:]
        if len(self.buffer) > 3000:
            preview = "...\n" + preview
        lines = preview.split("\n")
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        truncated = "\n".join(lines)

        if self.last_valid_json is not None:
            # For parsed JSON, show truncated raw text instead of full object
            return Syntax(truncated, "json", word_wrap=True, theme="monokai")
        return Syntax(truncated, "json", word_wrap=True, theme="monokai")


class TranscoderDisplay:
    """Rich-based CLI display with multi-panel layout.

    Supports dynamic phase count for State Machine flow.
    Phase names include emojis.

    Layout:
    - Top panel: Tools (load_skill, write_file, etc.)
    - Middle panel: Todo status (shown after first Reflect)
    - Reasoning panel: LLM reasoning process (when available)
    - Bottom panel: Streaming LLM output
    """

    PHASE_LABELS = {
        "🚀 Generate": "Generating",
        "💫 Improve": "Improving",
        "🔧 Fix": "Fixing",
        "🧪 Test": "Testing",
        "💎 Reflect": "Reflecting",
    }

    def __init__(self, console: Console) -> None:
        self.console = console
        self.start_time = time.time()
        self.current_phase = ""
        self.phase_label = ""
        self.phase_start_time = 0.0
        self.tool_items: list[str] = []
        self.files_created = 0
        self.tests_passed = 0
        self.tests_total = 0
        self.live: Live | None = None
        self.completed_phases: list[tuple[str, str, int]] = []
        self.todos: list[dict[str, str]] = []
        self.show_todos = False

        self.reasoning_renderer = StreamRenderer(content_type="markdown")
        self.output_renderer = StreamRenderer(content_type="text")

    def get_spinner_frame(self) -> str:
        """Get current spinner frame based on time."""
        idx = int(time.time() * 4) % len(SPINNER_FRAMES)
        return SPINNER_FRAMES[idx]

    def build_todo_panel(self) -> Panel | None:
        """Build Todo status panel."""
        if not self.show_todos or not self.todos:
            return None

        lines = []
        for todo in self.todos:
            status = todo.get("status", "pending")
            content = todo.get("content", "")
            if status == "pending":
                lines.append(f"  [bold yellow][ ][/bold yellow] {content}")
            elif status == "done":
                lines.append(f"  [bold blue][~][/bold blue] {content}")
            elif status == "verified":
                lines.append(f"  [bold green][v][/bold green] {content}")

        if not lines:
            return None

        return Panel(
            "\n".join(lines),
            title="[bold]📋 Todos[/bold]",
            title_align="left",
            width=PANEL_WIDTH,
            border_style="yellow",
        )

    def build_display(self) -> Group:
        """Build multi-panel display."""
        elements = []

        for phase_name, phase_label, elapsed in self.completed_phases:
            elements.append(Text.from_markup(f"  {phase_name} ✅ [dim]({elapsed}s)[/dim]"))

        if self.current_phase:
            elapsed = int(time.time() - self.phase_start_time)
            spinner = self.get_spinner_frame()

            if self.tool_items:
                tool_lines = []
                recent_tools = self.tool_items[-MAX_TOOL_ITEMS:]
                for item in recent_tools:
                    tool_lines.append(f"  [cyan]├─[/cyan] {item}")
                if len(self.tool_items) > MAX_TOOL_ITEMS:
                    hidden = len(self.tool_items) - MAX_TOOL_ITEMS
                    tool_lines.append(f"  [dim]({hidden} more)[/dim]")

                tool_panel = Panel(
                    "\n".join(tool_lines),
                    title="[bold]🔧 Tools[/bold]",
                    title_align="left",
                    width=PANEL_WIDTH,
                    border_style="dim",
                )
                elements.append(tool_panel)

            todo_panel = self.build_todo_panel()
            if todo_panel:
                elements.append(todo_panel)

            if self.reasoning_renderer.has_content():
                reasoning_panel = Panel(
                    self.reasoning_renderer.render(),
                    title="[bold]💡 Reasoning[/bold]",
                    title_align="left",
                    width=PANEL_WIDTH,
                    border_style="dim",
                )
                elements.append(reasoning_panel)

            stream_title = Text()
            stream_title.append(f"{self.current_phase} ", style="bold")
            stream_title.append(spinner, style="cyan")
            stream_title.append(f" ({elapsed}s)", style="dim")

            stream_panel = Panel(
                self.output_renderer.render(),
                title=stream_title,
                title_align="left",
                width=PANEL_WIDTH,
                border_style="cyan",
            )
            elements.append(stream_panel)

        return Group(*elements)

    def start_live(self) -> None:
        """Start Live display if not already started."""
        if self.live is None:
            self.live = Live(
                self.build_display(),
                console=self.console,
                refresh_per_second=4,
            )
            self.live.start()

    def stop_live(self) -> None:
        """Stop Live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def update(self) -> None:
        """Update Live display."""
        if self.live:
            self.live.update(self.build_display())

    def start_phase(self, phase_name: str, output_type: ContentType = "text") -> None:
        """Start a new phase.

        Args:
            phase_name: Phase label (e.g., "💎 Reflect")
            output_type: Content type for OUTPUT stream (reasoning is always text)
        """
        self.start_live()

        if phase_name == "💎 Reflect":
            self.show_todos = True

        self.current_phase = phase_name
        self.phase_label = self.PHASE_LABELS.get(phase_name, phase_name)
        self.phase_start_time = time.time()
        self.tool_items = []

        self.reasoning_renderer.clear()
        self.output_renderer.clear()
        self.output_renderer.set_content_type(output_type)

        self.update()

    def end_phase(self) -> None:
        """Complete current phase."""
        elapsed = int(time.time() - self.phase_start_time)
        self.completed_phases.append((self.current_phase, self.phase_label, elapsed))
        if self.current_phase == "💎 Reflect":
            self.show_todos = True
        self.current_phase = ""
        self.update()

    def update_todos(self, todos: list[dict[str, str]]) -> None:
        """Update todo list for display."""
        self.todos = todos
        self.update()

    def stream_reasoning_delta(self, delta: str) -> None:
        """Add reasoning summary delta."""
        self.reasoning_renderer.append(delta)
        self.update()

    def stream_output_delta(self, delta: str) -> None:
        """Add output delta."""
        self.output_renderer.append(delta)
        self.update()

    def stream_delta(self, delta: str) -> None:
        """Add streaming text delta (legacy compatibility)."""
        self.stream_output_delta(delta)

    def start_tool_stream(self, tool_name: str) -> None:
        """Clear output buffer and set JSON mode for tool args streaming."""
        self.output_renderer.clear()
        self.output_renderer.set_content_type("json")
        self.update()

    def tool_call(self, tool_name: str, summary: str) -> None:
        """Add tool call to Tools panel."""
        if tool_name == "write":
            self.files_created += 1
        self.tool_items.append(f"{tool_name} → {sanitize_text(summary).replace(chr(10), ', ')}")
        self.update()

    def header(self, input_file: str, output_dir: str) -> None:
        """Show header."""
        content = f"  {input_file} → {output_dir}"
        self.console.print(
            Panel(
                content,
                title="[bold]🧩 Transcoder[/bold]",
                title_align="left",
                width=PANEL_WIDTH,
                border_style="blue",
            )
        )
        self.console.print()

    def footer(self, output_dir: str, result: RunResult) -> None:
        """Show footer with result box."""
        self.stop_live()

        total = int(time.time() - self.start_time)

        if result.passed:
            status_line = "  ✨ [green]Complete[/green]"
        else:
            status_line = "  ❌ [red]Incomplete[/red]"

        lines = [status_line, ""]

        if self.files_created > 0:
            lines.append(f"  [bold]Files:[/bold] {self.files_created} created")

        if result.total > 0:
            passed = result.total - result.failed_count
            lines.append(f"  [bold]Tests:[/bold] {passed}/{result.total} passed")

        lines.extend(["", f"  [bold]Output:[/bold] {output_dir}"])

        if result.errors:
            lines.append("")
            lines.append("  [yellow]Errors:[/yellow]")
            for error in result.errors[:3]:
                lines.append(f"    [dim]•[/dim] {error.message}")

        content = "\n".join(lines)
        self.console.print()
        result_icon = "🎉" if result.passed else "⚠️"
        self.console.print(
            Panel(
                content,
                title=f"[bold]{result_icon} Result[/bold]",
                title_align="left",
                width=PANEL_WIDTH,
                border_style="green" if result.passed else "red",
            )
        )
        self.console.print()
        self.console.print(f"[dim]Total time: {total}s[/dim]")
