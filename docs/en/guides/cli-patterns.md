# CLI Display Patterns

Advanced patterns for building rich command-line interfaces with AF.

## Intent

CLI applications need more than simple text output. This guide covers:

- Multi-panel layouts (reasoning, output, tools)
- Content-type aware rendering (text, markdown, JSON)
- Incremental JSON parsing for tool arguments
- Live updating displays

## StreamRenderer Pattern

Buffer streaming content with content-type awareness:

```python
import json
from typing import Literal

ContentType = Literal["text", "markdown", "json"]

class StreamRenderer:
    """Content-type aware stream renderer."""

    def __init__(self, content_type: ContentType = "text"):
        self.buffer = ""
        self.content_type = content_type
        self.json_decoder = json.JSONDecoder()
        self.last_valid_json = None

    def clear(self):
        """Reset buffer state."""
        self.buffer = ""
        self.last_valid_json = None

    def append(self, delta: str):
        """Append delta and parse if JSON."""
        self.buffer += delta
        if self.content_type == "json":
            self.try_parse_json()

    def try_parse_json(self):
        """Incremental JSON parsing with raw_decode.

        Handles:
        - Complete JSON objects
        - Incomplete JSON (waits for more data)
        - NDJSON (multiple objects)
        """
        buf = self.buffer.strip()
        if not buf:
            return

        try:
            obj, _ = self.json_decoder.raw_decode(buf)
            self.last_valid_json = obj
        except json.JSONDecodeError:
            pass  # Wait for more data

    def render(self) -> str:
        """Render based on content type."""
        if self.content_type == "json" and self.last_valid_json:
            return json.dumps(self.last_valid_json, indent=2)
        return self.buffer
```

## Multi-Panel Handler

Route events to separate display areas:

```python
class MultiPanelHandler:
    """Handler with separate reasoning, output, and tool panels."""

    def __init__(self):
        self.reasoning = StreamRenderer("text")
        self.output = StreamRenderer("text")
        self.tools: list[str] = []

    def __call__(self, event):
        import agentic_flow as af

        # Phase boundaries
        if isinstance(event, af.PhaseStarted):
            self.on_phase_start(event.label)
            return
        if isinstance(event, af.PhaseEnded):
            self.on_phase_end(event.label, event.elapsed_ms)
            return

        # SDK streaming events
        if getattr(event, "type", None) != "raw_response_event":
            return

        data = getattr(event, "data", None)
        if not data:
            return

        data_type = getattr(data, "type", "")
        delta = getattr(data, "delta", "")

        if data_type == "response.reasoning_summary_text.delta":
            self.reasoning.append(delta)
            self.refresh()
        elif data_type == "response.output_text.delta":
            self.output.append(delta)
            self.refresh()
        elif data_type == "response.function_call_arguments.delta":
            self.output.append(delta)
            self.refresh()
        elif data_type == "response.output_item.added":
            item = getattr(data, "item", None)
            if item and getattr(item, "type", "") == "function_call":
                tool_name = getattr(item, "name", "tool")
                self.on_tool_start(tool_name)

    def on_phase_start(self, label: str):
        """Clear buffers for new phase."""
        self.reasoning.clear()
        self.output.clear()

    def on_phase_end(self, label: str, elapsed_ms: int):
        """Phase completed."""
        pass

    def on_tool_start(self, tool_name: str):
        """New tool call - switch output to JSON mode."""
        self.output.clear()
        self.output.content_type = "json"
        self.tools.append(tool_name)

    def refresh(self):
        """Update display - implement with your UI library."""
        pass
```

## Rich Library Integration

Using Rich for beautiful terminal output:

```python
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.json import JSON as RichJSON
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text

class RichStreamRenderer:
    """Rich-aware stream renderer."""

    def __init__(self, content_type: ContentType = "text"):
        self.buffer = ""
        self.content_type = content_type
        self.json_decoder = json.JSONDecoder()
        self.last_valid_json = None

    def render(self):
        """Render to Rich renderable."""
        if not self.buffer.strip():
            return Text.from_markup("[dim]...[/dim]")

        if self.content_type == "text":
            return Text(self.buffer)
        elif self.content_type == "markdown":
            return Markdown(self.buffer)
        elif self.content_type == "json":
            if self.last_valid_json is not None:
                return RichJSON.from_data(self.last_valid_json)
            return Syntax(self.buffer, "json", word_wrap=True)

        return Text(self.buffer)


class RichDisplay:
    """Multi-panel Rich display."""

    def __init__(self, console: Console):
        self.console = console
        self.reasoning = RichStreamRenderer("text")
        self.output = RichStreamRenderer("text")
        self.live: Live | None = None

    def start(self):
        """Start live display."""
        self.live = Live(self.build(), console=self.console, refresh_per_second=4)
        self.live.start()

    def stop(self):
        """Stop live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def update(self):
        """Refresh display."""
        if self.live:
            self.live.update(self.build())

    def build(self) -> Group:
        """Build multi-panel layout."""
        panels = []

        if self.reasoning.buffer.strip():
            panels.append(Panel(
                self.reasoning.render(),
                title="[bold]Reasoning[/bold]",
                border_style="dim",
            ))

        panels.append(Panel(
            self.output.render(),
            title="[bold]Output[/bold]",
            border_style="cyan",
        ))

        return Group(*panels)
```

## Complete Example

```python
import agentic_flow as af

# Agents
researcher = af.Agent(
    name="researcher",
    instructions="Research thoroughly.",
    model="gpt-5.2",
    model_settings=af.reasoning("medium"),
)

# Rich display
from rich.console import Console

console = Console()
display = RichDisplay(console)

def rich_handler(event):
    import agentic_flow as af

    if isinstance(event, af.PhaseStarted):
        display.reasoning.buffer = ""
        display.output.buffer = ""
        display.start()
        return

    if isinstance(event, af.PhaseEnded):
        display.stop()
        return

    if getattr(event, "type", None) != "raw_response_event":
        return

    data = getattr(event, "data", None)
    if not data:
        return

    data_type = getattr(data, "type", "")
    delta = getattr(data, "delta", "")

    if data_type == "response.reasoning_summary_text.delta":
        display.reasoning.buffer += delta
        display.update()
    elif data_type == "response.output_text.delta":
        display.output.buffer += delta
        display.update()


async def research_flow(message: str) -> str:
    async with af.phase("Research", persist=True):
        return await researcher(message).stream()


runner = af.Runner(flow=research_flow, handler=rich_handler)

if __name__ == "__main__":
    result = runner.run_sync("Explain quantum computing")
    console.print(f"\n[green]Done![/green] {len(result)} chars")
```

---

Next: [Testing](testing.md) :material-arrow-right:
