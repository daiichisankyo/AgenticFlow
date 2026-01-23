"""Reflector agent module.

Intent: Quality review agent with same knowledge as Coder.
Reviews for intent preservation, not arbitrary checklists.
"""

from .agent import reflector
from .instructions import REFLECT_PROMPT

__all__ = ["reflector", "REFLECT_PROMPT"]
