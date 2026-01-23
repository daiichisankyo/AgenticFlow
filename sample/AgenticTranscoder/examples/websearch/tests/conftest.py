"""Pytest configuration for websearch agent tests.

Intent: Load .env.local for API keys before tests run.
"""

from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).parent.parent / ".env.local"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)
