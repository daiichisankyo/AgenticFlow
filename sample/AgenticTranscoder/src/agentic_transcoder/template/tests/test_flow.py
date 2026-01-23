"""Flow structure tests.

Tests flow imports and structure without API calls.
API integration tests are skipped by default for speed.
"""


def test_chat_flow_exists():
    """Test that chat_flow can be imported."""
    from flow import chat_flow

    assert callable(chat_flow)


def test_agent_specs_exists():
    """Test that agent_specs can be imported."""
    from agent_specs import chat_agent

    assert chat_agent is not None
