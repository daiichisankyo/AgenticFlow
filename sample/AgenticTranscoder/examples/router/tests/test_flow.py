"""Flow integration tests.

Uses real API - requires OPENAI_API_KEY.
"""

import json

import pytest

from flow import router_flow


@pytest.mark.asyncio
async def test_routes_to_cook():
    """Test that router_flow routes cooking questions to cook agent."""
    result = await router_flow("おすすめのパスタレシピを教えて")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_routes_to_meteorologist():
    """Test that router_flow routes weather questions to meteorologist agent."""
    result = await router_flow("明日の東京の天気は？")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_returns_classifier_json_for_others():
    """Test that router_flow returns classifier JSON for other queries."""
    result = await router_flow("Hello, how are you?")
    payload = json.loads(result)
    assert payload == {"category": "others"}
