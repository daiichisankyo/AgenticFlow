"""pytest configuration for Agentic Flow tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

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


@pytest.fixture
def text_collector():
    texts = []

    def handler(event):
        if hasattr(event, "data") and hasattr(event.data, "delta"):
            texts.append(event.data.delta)

    handler.texts = texts
    handler.get_text = lambda: "".join(texts)
    return handler
