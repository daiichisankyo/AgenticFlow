"""AgenticTranscoder - Template-based code transformation.

Transforms AgentBuilder code into Agentic Flow projects using
State Machine flow with pattern-based termination.

Architecture:
- 2 Agents: coder (edits), reflector (reviews)
- 5 Phases: Generate, Improve, Fix, Test, Reflect
- Pydantic types for structured output
- Termination: patterns_ok + all todos verified

Usage:
    transcoder init
    transcoder -f /path/to/input.py
"""

from .agents import coder, deploy_template, reflector
from .flow import Transcoder, runner, transcode
from .types import ReflectionResult, RunResult, TestError

__all__ = [
    "Transcoder",
    "transcode",
    "runner",
    "coder",
    "reflector",
    "deploy_template",
    "TestError",
    "RunResult",
    "ReflectionResult",
]
