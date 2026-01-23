"""Coder agent module.

Intent: Code transformation agent (read/write).
"""

from .agent import coder
from .instructions import FIX_PROMPT, GENERATE_PROMPT, IMPROVE_PROMPT

__all__ = ["coder", "GENERATE_PROMPT", "FIX_PROMPT", "IMPROVE_PROMPT"]
