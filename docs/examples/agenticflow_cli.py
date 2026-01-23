"""Agentic Flow CLI - Simple streaming handler."""

from agents import SQLiteSession

import agentic_flow as af

from .agenticflow_flow import my_flow


def cli_handler(event):
    if hasattr(event, "data") and hasattr(event.data, "delta"):
        print(event.data.delta, end="", flush=True)


runner = af.Runner(flow=my_flow, session=SQLiteSession("chat.db"), handler=cli_handler)
result = runner.run_sync("Explain quantum computing")
