"""Flow integration tests.

Intent: Verify basic chat flow returns a response.
Uses real API - requires OPENAI_API_KEY.
"""

import pytest

from flow import chat_flow


@pytest.mark.asyncio
async def test_chat_flow_responds():
    """Test that chat_flow returns a response."""
    result = await chat_flow("Hello, who are you?")
    assert isinstance(result, str)
    assert len(result) > 0
