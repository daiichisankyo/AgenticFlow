# CLI Display Patterns

Advanced patterns for building rich command-line interfaces with AF.

## Intent

CLI applications need more than simple text output. This guide covers:

- Phase-aware display with Rich panels
- Content-type aware rendering (text, markdown, JSON)
- Multi-phase formatting
- Live updating displays

## ContentRenderer Pattern

Render agent output with content-type awareness:

```python
import json
from typing import Literal

ContentType = Literal["text", "markdown", "json"]

class ContentRenderer:
    """Content-type aware renderer for agent output."""

    def __init__(self, content_type: ContentType = "text"):
        self.buffer = ""
        self.content_type = content_type

    def clear(self):
        """Reset buffer state."""
        self.buffer = ""

    def set_content(self, content: str):
        """Set full content from AgentResult."""
        self.buffer = content

    def render(self) -> str:
        """Render based on content type."""
        if self.content_type == "json":
            try:
                parsed = json.loads(self.buffer)
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                return self.buffer
        return self.buffer
```

## Multi-Phase Handler

Route events to display with phase context:

```python
import agentic_flow as af


class MultiPhaseHandler:
    """Handler that formats output per phase."""

    def __init__(self):
        self.current_phase: str | None = None
        self.phase_results: dict[str, str] = {}

    def __call__(self, event):
        # Phase boundaries
        if isinstance(event, af.PhaseStarted):
            self.current_phase = event.label
            print(f"\n[{event.label}]")
            return

        if isinstance(event, af.PhaseEnded):
            print(f"[/{event.label}] ({event.elapsed_ms}ms)")
            self.current_phase = None
            return

        # Agent result — full text delivered once
        if isinstance(event, af.AgentResult):
            content = str(event.content)
            if self.current_phase:
                self.phase_results[self.current_phase] = content
            print(content)
            return
```

## Rich Library Integration

Using Rich for beautiful terminal output:

```python
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

import agentic_flow as af


class RichPhaseDisplay:
    """Rich display with per-phase panels."""

    def __init__(self, console: Console):
        self.console = console
        self.current_phase: str | None = None
        self.phase_outputs: list[tuple[str, str]] = []
        self.pending_output: str = ""

    def handler(self, event):
        """Event handler for Rich display."""
        if isinstance(event, af.PhaseStarted):
            self.current_phase = event.label
            self.pending_output = ""
            return

        if isinstance(event, af.PhaseEnded):
            if self.pending_output:
                self.phase_outputs.append((event.label, self.pending_output))
                self.console.print(Panel(
                    Markdown(self.pending_output)
                    if self.looks_like_markdown(self.pending_output)
                    else Text(self.pending_output),
                    title=f"[bold]{event.label}[/bold] ({event.elapsed_ms}ms)",
                    border_style="cyan",
                ))
            self.current_phase = None
            return

        if isinstance(event, af.AgentResult):
            self.pending_output = str(event.content)
            return

    @staticmethod
    def looks_like_markdown(text: str) -> bool:
        """Simple heuristic for markdown detection."""
        markers = ["# ", "## ", "- ", "* ", "```", "**", "["]
        return any(marker in text for marker in markers)
```

## Complete Example

```python
import agentic_flow as af
from rich.console import Console

# Agents
researcher = af.Agent(
    name="researcher",
    instructions="Research thoroughly.",
    model="gpt-5.5",
    model_settings=af.reasoning("medium"),
)

# Rich display
console = Console()
display = RichPhaseDisplay(console)


async def research_flow(message: str) -> str:
    async with af.phase("Research", persist=True):
        return await researcher(message).stream()


runner = af.Runner(flow=research_flow, handler=display.handler)

if __name__ == "__main__":
    result = runner.run_sync("Explain quantum computing")
    console.print(f"\n[green]Done![/green] {len(result)} chars")
```

---

Next: [Testing](testing.md) :material-arrow-right:
