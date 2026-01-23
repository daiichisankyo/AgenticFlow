"""CLI for AgenticTranscoder.

Intent: Provide clean CLI interface per Part IV design.
Runner with handler injection pattern.

Usage:
    uv run transcoder init              # Initialize workspace
    uv run transcoder                   # Run with default input
    uv run transcoder -f ./my_agent.py  # Run with explicit file
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

import fire
from dotenv import load_dotenv
from rich.console import Console

from .console import create_handler
from .flow import Transcoder

PACKAGE_DIR = Path(__file__).parent.parent.parent
ENV_LOCAL = PACKAGE_DIR / ".env.local"
FIXTURES_DIR = PACKAGE_DIR / "fixtures"

DEFAULT_WORKSPACE = Path("./workspace")
DEFAULT_INPUT = "builder_agent.py"


class TranscoderCLI:
    """AgenticTranscoder CLI."""

    def __init__(self) -> None:
        self.console = Console()

    def init(self, workspace: str = "./workspace") -> None:
        """Initialize workspace with .env.local and sample files."""
        ws = Path(workspace).resolve()

        if ws.exists():
            self.console.print(f"[yellow]Already exists: {ws}[/yellow]")
            return

        ws.mkdir(parents=True)

        if ENV_LOCAL.exists():
            shutil.copy(ENV_LOCAL, ws / ".env.local")
            self.console.print("✅ Copied .env.local")

        sample = FIXTURES_DIR / "builder_agent.py"
        if sample.exists():
            shutil.copy(sample, ws / "builder_agent.py")
            self.console.print("✅ Copied builder_agent.py")

        self.console.print()
        self.console.print(f"✅ Initialized: {ws}")
        self.console.print("[dim]Next:[/dim] uv run transcoder")

    def reset(self, workspace: str = "./workspace", force: bool = False) -> None:
        """Remove generated *_af directories from workspace."""
        ws = Path(workspace).resolve()

        if not ws.exists():
            self.console.print(f"[red]Not found: {ws}[/red]")
            sys.exit(1)

        af_dirs = list(ws.glob("*_af"))
        if not af_dirs:
            self.console.print("[dim]No generated projects[/dim]")
            return

        for d in af_dirs:
            self.console.print(f"  {d.name}/")

        if not force:
            confirm = self.console.input("[yellow]Remove? [Y/n]:[/yellow] ")
            if confirm.lower() not in ("", "y", "yes"):
                return

        for d in af_dirs:
            shutil.rmtree(d)
            self.console.print(f"✅ Removed {d.name}/")

    def delete(self, workspace: str = "./workspace", force: bool = False) -> None:
        """Delete entire workspace directory. Alias: del"""
        ws = Path(workspace).resolve()

        if not ws.exists():
            self.console.print(f"[red]Not found: {ws}[/red]")
            sys.exit(1)

        self.console.print(f"  {ws}/")

        if not force:
            confirm = self.console.input("[yellow]Delete workspace? [Y/n]:[/yellow] ")
            if confirm.lower() not in ("", "y", "yes"):
                return

        shutil.rmtree(ws)
        self.console.print(f"✅ Deleted {ws.name}/")

    def run(
        self,
        f: str | None = None,
        o: str | None = None,
    ) -> None:
        """Run recomposition.

        Args:
            f: Input file (default: ./workspace/builder_agent.py)
            o: Output directory (default: <input>_af)
        """
        if f is None:
            input_path = (DEFAULT_WORKSPACE / DEFAULT_INPUT).resolve()
            workspace = DEFAULT_WORKSPACE.resolve()
        else:
            input_path = Path(f).resolve()
            workspace = input_path.parent

        if not input_path.exists():
            self.console.print(f"[red]Not found: {input_path}[/red]")
            if f is None:
                self.console.print("[dim]Run: uv run transcoder init[/dim]")
            sys.exit(1)

        env_file = workspace / ".env.local"
        if env_file.exists():
            load_dotenv(env_file)

        output_path = Path(o).resolve() if o else workspace / f"{input_path.stem}_af"

        display, handler = create_handler(self.console)

        display.header(input_path.name, output_path.name)

        source_code = input_path.read_text()

        transcoder = Transcoder(
            source_code=source_code,
            output_dir=str(output_path),
        )
        run = transcoder.runner(handler=handler)
        result = asyncio.run(run(""))

        display.footer(str(output_path), result)

    def __call__(
        self,
        f: str | None = None,
        o: str | None = None,
    ) -> None:
        """Default command - run recomposition."""
        self.run(f=f, o=o)


VALID_COMMANDS = {"init", "run", "reset", "delete", "del", "--help", "-h"}


def main() -> None:
    """Entry point."""
    cli = TranscoderCLI()

    # Handle 'del' alias before Fire (del is Python reserved word)
    if len(sys.argv) > 1 and sys.argv[1] == "del":
        sys.argv[1] = "delete"

    # Validate command to prevent Fire's prefix matching (e.g., "rest" → "reset")
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        cmd = sys.argv[1]
        if cmd not in VALID_COMMANDS:
            valid = sorted(VALID_COMMANDS - {"del", "--help", "-h"})
            Console().print(f"[red]Unknown command: {cmd}[/red]")
            Console().print(f"[dim]Valid commands: {', '.join(valid)}[/dim]")
            sys.exit(1)

    fire.Fire(cli)


if __name__ == "__main__":
    main()
