"""Pytest configuration - load environment variables."""

import pathlib

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent.parent / ".env.local", override=True)
