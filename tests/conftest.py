"""pytest configuration for Agentic Flow tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)


@pytest.fixture(autouse=True)
def reset_openai_http_client():
    """Reset OpenAI SDK's shared HTTP client after each test.

    The SDK caches httpx.AsyncClient globally (agents/models/openai_provider.py),
    which causes issues when pytest-asyncio creates a new event loop for each test.
    The cached client is bound to the old event loop, causing "Event loop is closed"
    errors in subsequent tests.
    """
    yield
    try:
        from agents.models import openai_provider

        openai_provider._http_client = None
    except (ImportError, AttributeError):
        pass


@pytest.fixture
def handler_log():
    events = []

    def handler(event):
        events.append(event)

    handler.events = events
    return handler


def message_items(items):
    """Return only user/assistant message items, dropping reasoning items."""
    return [item for item in items if item.get("role") in ("user", "assistant")]


class Analysis(BaseModel):
    """Sentiment analysis result."""

    sentiment: str
    score: float


class Decision(BaseModel):
    """Decision result."""

    action: str
    reason: str
