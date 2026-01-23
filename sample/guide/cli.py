"""AF Guide - Textual TUI.

Run:
    cd sample
    uv run python -m guide.cli

Classic Macintosh style with modern Textual widgets.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sqlite3
import sys
import uuid

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent.parent / ".env.local")

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from agentic_flow import Runner
from agents import SQLiteSession
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Input,
    ProgressBar,
    RichLog,
    Rule,
    Static,
    TabbedContent,
    TabPane,
)

from .flow import guide_flow

DATA_DIR = pathlib.Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "cli_session.db"
LAST_SESSION_FILE = DATA_DIR / "last_session_id.txt"


def get_last_session_id() -> str:
    """Get the last session ID or create a new one."""
    if LAST_SESSION_FILE.exists():
        return LAST_SESSION_FILE.read_text().strip()
    return create_new_session_id()


def create_new_session_id() -> str:
    """Create a new session ID and save it."""
    session_id = f"guide_{uuid.uuid4().hex[:8]}"
    LAST_SESSION_FILE.write_text(session_id)
    return session_id


def load_chat_history(session_id: str, db_path: pathlib.Path) -> list[dict]:
    """Load chat history from SQLiteSession database.

    Returns list of {"role": "user"|"assistant", "content": str}.
    """
    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT message_data FROM agent_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        conn.close()

        messages = []
        for row in rows:
            data = json.loads(row["message_data"])
            role = data.get("role", "")
            content_parts = data.get("content", [])
            text = ""
            for part in content_parts:
                if part.get("type") in ("input_text", "output_text"):
                    text += part.get("text", "")
            if text:
                messages.append({"role": role, "content": text})
        return messages
    except Exception:
        return []


HAPPY_MAC = """
     ┌─────────┐
     │  ┌───┐  │
     │  │◉ ◉│  │
     │  └───┘  │
     │    ▽    │
     │  ╲___╱  │
     │         │
     └─────────┘
"""


class GuideApp(App):
    """AF Guide - Classic Macintosh Style with Modern Widgets."""

    CSS_PATH = "cli.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+k", "clear", "Clear"),
        Binding("ctrl+n", "new_chat", "New"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.reasoning_text = ""
        self.streaming_text = ""
        self.is_streaming = False
        self.current_user_input = ""
        self.current_phase_label = ""
        self.session_id = get_last_session_id()
        self.session = SQLiteSession(
            session_id=self.session_id,
            db_path=str(DB_PATH),
        )
        self.runner = Runner(flow=guide_flow, session=self.session)

    def create_new_session(self) -> None:
        """Create a new chat session."""
        self.session_id = create_new_session_id()
        self.session = SQLiteSession(
            session_id=self.session_id,
            db_path=str(DB_PATH),
        )
        self.runner = Runner(flow=guide_flow, session=self.session)

    def compose(self) -> ComposeResult:
        with Horizontal(id="menu-bar"):
            yield Static("", id="apple-menu")
            yield Static("File  Edit  View  Help", id="menu-items")

        with Vertical(id="main-window"):
            with Horizontal(id="title-bar"):
                yield Button("◻", id="close-button", variant="default")
                yield Static("AF Guide", id="title-text")

            with TabbedContent(initial="tab-chat"):
                with TabPane("Welcome", id="tab-welcome"):
                    with Vertical(id="welcome-panel"):
                        yield Static(HAPPY_MAC, id="mac-icon")
                        yield Static(
                            "Welcome to AF.\n\n"
                            "I am your Guide.\n"
                            "Ask me about design, implementation, or usage.",
                            id="welcome-text",
                        )
                        yield Button("New Chat", id="new-chat-button", variant="primary")

                with TabPane("Chat", id="tab-chat"):
                    with Vertical(id="chat-area"):
                        yield RichLog(id="chat-log", highlight=True, markup=True)
                        yield Rule()
                        with Horizontal(id="input-area"):
                            yield Input(
                                placeholder="Type your question here...",
                                id="user-input",
                            )

            with Horizontal(id="status-bar"):
                yield Static("Ready", id="status-text")
                yield ProgressBar(id="progress", show_eta=False, show_percentage=True)

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#progress", ProgressBar).update(total=100, progress=0)
        self.load_history()
        self.set_timer(0.1, self.focus_input)

    def load_history(self) -> None:
        """Load and display chat history from previous sessions."""
        history = load_chat_history(self.session_id, DB_PATH)
        if not history:
            return

        chat_log = self.query_one("#chat-log", RichLog)
        for msg in history:
            if msg["role"] == "user":
                chat_log.write(
                    Panel(
                        Text(msg["content"]),
                        title="You",
                        title_align="left",
                        border_style="bright_black",
                    )
                )
            elif msg["role"] == "assistant":
                chat_log.write(
                    Panel(
                        Markdown(msg["content"]),
                        title="Guide",
                        title_align="left",
                        border_style="bright_black",
                    )
                )

        if history:
            self.query_one(TabbedContent).active = "tab-chat"

    def focus_input(self) -> None:
        self.query_one("#user-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-chat-button":
            self.create_new_session()
            self.query_one("#chat-log", RichLog).clear()
            self.query_one(TabbedContent).active = "tab-chat"
            self.call_later(self.focus_input)
        elif event.button.id == "close-button":
            self.exit()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value.strip() or self.is_streaming:
            return

        user_input = event.value.strip()
        event.input.value = ""

        self.query_one(TabbedContent).active = "tab-chat"
        chat_log = self.query_one("#chat-log", RichLog)

        chat_log.write(
            Panel(
                Text(user_input),
                title="You",
                title_align="left",
                border_style="bright_black",
            )
        )

        self.reasoning_text = ""
        self.streaming_text = ""
        self.run_guide(user_input)

    @work(exclusive=True)
    async def run_guide(self, user_input: str) -> None:
        self.is_streaming = True
        self.current_user_input = user_input
        status = self.query_one("#status-text", Static)
        progress = self.query_one("#progress", ProgressBar)
        chat_log = self.query_one("#chat-log", RichLog)

        status.update("Processing...")
        progress.update(total=100, progress=0)

        try:
            result = await self.execute_guide(user_input)

            chat_log.clear()
            self.write_user_panel(chat_log, user_input)

            label = self.current_phase_label or "Guide"
            if self.reasoning_text:
                chat_log.write(
                    Panel(
                        Markdown(self.reasoning_text),
                        title=f"{label} (reasoning)",
                        title_align="left",
                        border_style="yellow",
                    )
                )

            response_text = str(result) if result else "(No response)"
            chat_log.write(
                Panel(
                    Markdown(response_text),
                    title=label,
                    title_align="left",
                    border_style="bright_black",
                )
            )

            progress.update(progress=100)

        except asyncio.CancelledError:
            chat_log.write(Text("[Cancelled]", style="italic"))
        except Exception as e:
            chat_log.write(Text(f"Error: {e!r}", style="bold"))
        finally:
            self.is_streaming = False
            status.update("Ready")
            progress.update(progress=0)

    def write_user_panel(self, chat_log: RichLog, user_input: str) -> None:
        chat_log.write(
            Panel(
                Text(user_input),
                title="You",
                title_align="left",
                border_style="bright_black",
            )
        )

    async def execute_guide(self, user_input: str) -> str:
        progress = self.query_one("#progress", ProgressBar)
        chat_log = self.query_one("#chat-log", RichLog)

        def handle_event(event) -> None:
            if hasattr(event, "label") and not hasattr(event, "elapsed_ms"):
                self.current_phase_label = event.label

            label = self.current_phase_label or "Guide"
            event_type = getattr(event, "type", None)

            if hasattr(event, "data") and hasattr(event.data, "delta"):
                delta = event.data.delta

                if event_type and "reasoning" in event_type:
                    self.reasoning_text += delta
                    chat_log.clear()
                    self.write_user_panel(chat_log, self.current_user_input)
                    chat_log.write(
                        Panel(
                            Markdown(self.reasoning_text),
                            title=f"{label} (reasoning...)",
                            title_align="left",
                            border_style="yellow",
                        )
                    )
                else:
                    self.streaming_text += delta
                    total = len(self.reasoning_text) + len(self.streaming_text)
                    current = min(20 + total // 10, 95)
                    progress.update(progress=current)

                    chat_log.clear()
                    self.write_user_panel(chat_log, self.current_user_input)
                    if self.reasoning_text:
                        chat_log.write(
                            Panel(
                                Markdown(self.reasoning_text),
                                title=f"{label} (reasoning)",
                                title_align="left",
                                border_style="yellow",
                            )
                        )
                    chat_log.write(
                        Panel(
                            Markdown(self.streaming_text),
                            title=f"{label} (streaming...)",
                            title_align="left",
                            border_style="dim",
                        )
                    )

        runner = Runner(flow=guide_flow, session=self.session, handler=handle_event)
        return await runner(user_input)

    def action_clear(self) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()

    def action_new_chat(self) -> None:
        self.create_new_session()
        self.action_clear()
        self.query_one(TabbedContent).active = "tab-welcome"

    def action_cancel(self) -> None:
        if self.is_streaming:
            for worker in self.workers:
                worker.cancel()


def main() -> None:
    app = GuideApp()
    app.run()


if __name__ == "__main__":
    main()
