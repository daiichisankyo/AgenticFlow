"""Documentation guide flow for AF.

Simple but effective: Give the LLM everything it needs upfront.
The codebase is small (~1300 lines), so the model can handle it all.

No need for complex multi-agent handoffs or lazy-loading tools.
Just good instructions and complete context.
"""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from agentic_flow import Agent, phase, reasoning

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "agentic_flow"
DOCS_DIR = PROJECT_ROOT / "docs" / "en"
README = PROJECT_ROOT / "README.md"

MODEL = os.getenv("MODEL_NAME", "gpt-5.2")


def load_docs() -> str:
    """Load documentation files from docs/en/."""
    docs = []
    if DOCS_DIR.exists():
        for md_file in sorted(DOCS_DIR.rglob("*.md")):
            relative_path = md_file.relative_to(DOCS_DIR)
            docs.append(f"# {relative_path}\n\n{md_file.read_text()}")
    if README.exists():
        docs.append(f"# README.md\n\n{README.read_text()}")
    return "\n\n---\n\n".join(docs)


def load_source_code() -> str:
    """Load all source code files."""
    code_parts = []
    for py_file in sorted(SRC_DIR.glob("*.py")):
        content = py_file.read_text()
        code_parts.append(f"## {py_file.name}\n\n```python\n{content}```")
    return "\n\n".join(code_parts)


DOCS_CONTENT = load_docs()
CODE_CONTENT = load_source_code()

INSTRUCTIONS = f"""# Reference Material

## Documentation
{DOCS_CONTENT}

## Source Code
{CODE_CONTENT}

---

# Instructions

You are an expert on AF (Agentic Flow), a thin orchestration layer for the OpenAI Agents SDK.

## Philosophy

"Don't reinvent the SDK." AF adds value through orchestration, not reimplementation.

## Response Qualities

**Directness**: Answer the question first. Add context only if it helps.

**Honesty**: Simple things are simple. Complex things are complex. Say which it is.

**Proportionality**: Match response length to question depth.
- Quick question → concise answer
- Deep discussion → thorough explanation with trade-offs

**Groundedness**: Cite the actual documentation and source code above.
Real examples from the codebase are more valuable than hypotheticals.

## Good Responses

A good response:
- Gets to the point immediately
- Uses concrete examples from the source code
- Acknowledges when the user's understanding is correct
- Explains actual design trade-offs with evidence

## Discussing Design Decisions

AF's architecture has intentional trade-offs. When discussing them:
- Cite the relevant documentation section
- Explain what problem the design solves
- Be clear about what was chosen and what was traded away

## Language

Respond in the same language the user uses.
If the user writes in Japanese, respond in Japanese.
If the user writes in English, respond in English.
"""

guide_agent = Agent(
    name="agenticflow",
    instructions=INSTRUCTIONS,
    model=MODEL,
    model_settings=reasoning("medium"),
)


async def guide_flow(user_message: str) -> str:
    """Documentation guide flow.

    A knowledgeable guide that answers questions about AF
    based on complete access to documentation and source code.

    Uses reasoning="medium" for balanced accuracy and speed.
    Uses phase(persist=True) to write final response to Session.
    """
    async with phase("🧭 AF", persist=True):
        return await guide_agent(user_message).stream()
