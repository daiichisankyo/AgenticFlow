"""User memory - Long-term fact storage.

Extracts and stores personal facts (max 33) like ChatGPT:
- Name, profession, location
- Goals, preferences, routines
- Projects, learning topics
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from agentic_flow import Agent

from .types import MemoryDecision

MODEL = os.getenv("MODEL_NAME", "gpt-5.5")

memory_agent = Agent(
    name="memory_extractor",
    instructions="""Decide if user's message contains a fact worth remembering long-term.

SAVE these types of facts:
- Name, age, location
- Profession, job title, company
- Goals, aspirations
- Preferences (language, style, tools)
- Routines (fitness, work habits)
- Ongoing projects
- Learning topics, skills

DO NOT SAVE:
- Temporary states ("I'm tired today")
- Opinions about external content
- Questions
- Task requests
- Greetings

If should_save=true, extract a concise fact (e.g., "Python developer in Tokyo").
If should_save=false, set fact=null.""",
    model=MODEL,
    output_type=MemoryDecision,
)


class UserMemory:
    """Manages user facts (max 33, like ChatGPT)."""

    def __init__(self, max_facts: int = 33, storage_path: str | None = None):
        self.facts: list[str] = []
        self.max_facts = max_facts
        self.storage_path = storage_path
        if storage_path:
            self.load()

    async def process(self, message: str) -> MemoryDecision | None:
        """Extract fact from message if worth saving.

        Uses isolated() + silent() to avoid polluting conversation context.
        """
        existing = self.to_prompt() if self.facts else "None"
        decision: MemoryDecision = (
            await memory_agent(f"Existing facts:\n{existing}\n\nUser said: {message}")
            .isolated()
            .silent()
        )

        if decision.should_save and decision.fact:
            self.add_fact(decision.fact)

        return decision

    def add_fact(self, fact: str) -> None:
        """Add fact, respecting max limit (FIFO)."""
        if fact in self.facts:
            return
        self.facts.append(fact)
        if len(self.facts) > self.max_facts:
            self.facts.pop(0)
        if self.storage_path:
            self.save()

    def remove_fact(self, keyword: str) -> bool:
        """Remove fact containing keyword. Returns True if removed."""
        for i, fact in enumerate(self.facts):
            if keyword.lower() in fact.lower():
                self.facts.pop(i)
                if self.storage_path:
                    self.save()
                return True
        return False

    def clear(self) -> None:
        """Clear all facts."""
        self.facts = []
        if self.storage_path:
            self.save()

    def to_prompt(self) -> str:
        """Format facts for prompt injection."""
        if not self.facts:
            return ""
        return "\n".join(f"- {f}" for f in self.facts)

    def load(self) -> None:
        """Load facts from JSON file."""
        if not self.storage_path:
            return
        path = pathlib.Path(self.storage_path)
        if path.exists():
            data = json.loads(path.read_text())
            self.facts = data.get("facts", [])

    def save(self) -> None:
        """Save facts to JSON file."""
        if not self.storage_path:
            return
        path = pathlib.Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"facts": self.facts}, indent=2))
