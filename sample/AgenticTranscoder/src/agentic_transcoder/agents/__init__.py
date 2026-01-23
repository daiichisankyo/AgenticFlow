"""Agents for AgenticTranscoder.

Intent: Two agents with same knowledge, different roles.

Architecture:
- coder: File editing agent (read/write) with reasoning("high")
- reflector: Quality review agent (read-only + todo management) with reasoning("high")

Both agents share the same knowledge base (skills, docs, transformation rules).
Coder writes code, Reflector reviews for intent preservation.

Tools:
- coder: load_skill, read/write/edit_file, list_files, exec_command, get_todos, mark_done
- reflector: load_skill, read_file, list_files, get_todos, add_todo, verify_todo
"""

from .coder import coder
from .coder.instructions import CODER_INSTRUCTIONS
from .reflector import reflector
from .tools import deploy_template, load_docs, load_knowledge, load_source

__all__ = [
    "coder",
    "reflector",
    "deploy_template",
    "load_knowledge",
    "load_docs",
    "load_source",
    "CODER_INSTRUCTIONS",
]
