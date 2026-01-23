"""Reflector agent definition.

Intent: Quality review agent (read-only + todo management) with reasoning("high").

Configuration:
    - model: gpt-5.2
    - model_settings: reasoning("high")
    - tools: load_skill, read_file, list_files, get_todos, add_todo, verify_todo
    - output_type: ReflectionResult

Responsibility:
    - Review transformed code for SDK pattern compliance
    - Create todos for improvements (add_todo)
    - Verify Coder's work is complete (verify_todo)
    - Return patterns_ok=True when all patterns correct and todos verified
"""

from agentic_flow import Agent, reasoning

from ...types import ReflectionResult
from ..tools import add_todo, get_todos, list_files, load_skill, read_file, verify_todo
from .instructions import REFLECTOR_INSTRUCTIONS

reflector = Agent(
    name="reflector",
    instructions=REFLECTOR_INSTRUCTIONS,
    model="gpt-5.2",
    model_settings=reasoning("medium", truncation="auto"),
    tools=[load_skill, read_file, list_files, get_todos, add_todo, verify_todo],
    output_type=ReflectionResult,
)
