"""Coder agent definition.

Intent: Code transformation agent (read/write) with reasoning("high").

Configuration:
    - model: gpt-5.2
    - model_settings: reasoning("high")
    - tools: load_skill, read_file, write_file, edit_file, list_files,
             exec_command, get_todos, mark_done

Prompts (selected by flow based on context):
    - GENERATE_PROMPT: First run transformation
    - FIX_PROMPT: Fix test failures
    - IMPROVE_PROMPT: Complete Reflector todos
"""

from agentic_flow import Agent, reasoning

from ..tools import (
    edit_file,
    exec_command,
    get_todos,
    list_files,
    load_skill,
    mark_done,
    read_file,
    write_file,
)
from .instructions import CODER_INSTRUCTIONS

coder = Agent(
    name="coder",
    instructions=CODER_INSTRUCTIONS,
    model="gpt-5.2",
    model_settings=reasoning("high", truncation="auto"),
    tools=[
        load_skill,
        read_file,
        write_file,
        edit_file,
        list_files,
        exec_command,
        get_todos,
        mark_done,
    ],
)
