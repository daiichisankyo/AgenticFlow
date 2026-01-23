"""Section 7: SDK Pass-through Tests - tools and handoffs.

Tests for:
- 7.1 tools / function calling / handoff are SDK domain
- Agent accepts tools parameter
- Agent accepts handoffs parameter
- Both are passed through to SDK

All tests use real GPT API calls. No mocks.
"""

from __future__ import annotations

import pytest
from agents import function_tool

from agentic_flow import Agent, Runner, phase


@function_tool
def get_current_weather(location: str) -> str:
    """Get weather for a location."""
    return f"Weather in {location}: Sunny, 22C"


@function_tool
def search_database(query: str) -> str:
    """Search the database."""
    return f"Results for '{query}': [item1, item2, item3]"


class TestToolsParameter:
    """7.1 tools - SDK pass-through."""

    def test_agent_with_tools_creation(self):
        """Agent with tools parameter creates correctly."""
        agent = Agent(
            name="tool_agent",
            instructions="Use tools when needed.",
            model="gpt-5.2",
            tools=[get_current_weather],
        )

        assert agent.sdk_kwargs.get("tools") == [get_current_weather]
        assert agent.sdk_kwargs.get("name") == "tool_agent"

    def test_agent_tools_passed_to_sdk(self):
        """tools are passed to SDK Agent."""
        agent = Agent(
            name="tool_agent",
            instructions="Use tools.",
            model="gpt-5.2",
            tools=[get_current_weather, search_database],
        )

        assert agent.sdk_agent.tools is not None
        assert len(agent.sdk_agent.tools) == 2

    def test_agent_without_tools(self):
        """Agent without tools has None."""
        agent = Agent(
            name="no_tools",
            instructions="No tools.",
            model="gpt-5.2",
        )

        assert agent.sdk_kwargs.get("tools") is None

    @pytest.mark.asyncio
    async def test_agent_tools_execution(self):
        """Agent with tools executes tool calls."""
        agent = Agent(
            name="weather_agent",
            instructions="Use get_current_weather tool for weather questions.",
            model="gpt-5.2",
            tools=[get_current_weather],
        )

        result = await agent("What's the weather in Tokyo?")

        assert "Tokyo" in result or "22" in result or "Sunny" in result
        print(f"Tool execution result: {result}")

    @pytest.mark.asyncio
    async def test_agent_tools_with_streaming(self, handler_log):
        """Agent with tools works with streaming."""
        agent = Agent(
            name="weather_agent",
            instructions="Use get_current_weather tool. Be concise.",
            model="gpt-5.2",
            tools=[get_current_weather],
        )

        async def flow(msg: str) -> str:
            async with phase("Weather"):
                return await agent(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("Weather in Paris?")

        assert len(result) > 0
        assert len(handler_log.events) > 0
        print(f"Streaming tool result: {result}")


class TestHandoffsParameter:
    """7.1 handoffs - SDK pass-through."""

    def test_agent_with_handoffs_creation(self):
        """Agent with handoffs parameter creates correctly."""
        specialist = Agent(
            name="specialist",
            instructions="I am a specialist.",
            model="gpt-5.2",
        )

        triage = Agent(
            name="triage",
            instructions="Route to specialist.",
            model="gpt-5.2",
            handoffs=[specialist],
        )

        assert triage.sdk_kwargs.get("handoffs") == [specialist]
        assert triage.sdk_kwargs.get("name") == "triage"

    def test_agent_handoffs_passed_to_sdk(self):
        """handoffs are passed to SDK Agent."""
        specialist = Agent(
            name="specialist",
            instructions="Specialist.",
            model="gpt-5.2",
        )

        triage = Agent(
            name="triage",
            instructions="Route.",
            model="gpt-5.2",
            handoffs=[specialist],
        )

        assert triage.sdk_agent.handoffs is not None
        assert len(triage.sdk_agent.handoffs) == 1

    def test_agent_without_handoffs(self):
        """Agent without handoffs has None."""
        agent = Agent(
            name="no_handoffs",
            instructions="No handoffs.",
            model="gpt-5.2",
        )

        assert agent.sdk_kwargs.get("handoffs") is None

    @pytest.mark.asyncio
    async def test_agent_handoffs_execution(self, handler_log):
        """Agent with handoffs can delegate."""
        billing_agent = Agent(
            name="billing",
            instructions="You handle billing questions. Say 'BILLING HANDLED'.",
            model="gpt-5.2",
        )

        triage_agent = Agent(
            name="triage",
            instructions="Triage agent. For billing, hand off to billing agent.",
            model="gpt-5.2",
            handoffs=[billing_agent],
        )

        async def flow(msg: str) -> str:
            async with phase("Triage"):
                return await triage_agent(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("I have a billing question")

        print(f"Handoff result: {result}")
        assert len(result) > 0


class TestToolsAndHandoffsCombined:
    """7.1 Combined tools and handoffs."""

    def test_agent_with_both(self):
        """Agent can have both tools and handoffs."""
        specialist = Agent(
            name="specialist",
            instructions="Specialist.",
            model="gpt-5.2",
        )

        coordinator = Agent(
            name="coordinator",
            instructions="Coordinate using tools and handoffs.",
            model="gpt-5.2",
            tools=[get_current_weather, search_database],
            handoffs=[specialist],
        )

        tools = [get_current_weather, search_database]
        assert coordinator.sdk_kwargs.get("tools") == tools
        assert coordinator.sdk_kwargs.get("handoffs") == [specialist]
        assert len(coordinator.sdk_agent.tools) == 2
        assert len(coordinator.sdk_agent.handoffs) == 1

    @pytest.mark.asyncio
    async def test_coordinator_flow(self, handler_log):
        """Coordinator with tools and handoffs works in flow."""
        specialist = Agent(
            name="weather_specialist",
            instructions="You are a weather specialist. Provide detailed forecasts.",
            model="gpt-5.2",
            tools=[get_current_weather],
        )

        coordinator = Agent(
            name="coordinator",
            instructions=(
                "You coordinate requests. For weather, use tool or hand off to specialist."
            ),
            model="gpt-5.2",
            tools=[get_current_weather],
            handoffs=[specialist],
        )

        async def flow(msg: str) -> str:
            async with phase("Coordinate"):
                return await coordinator(msg).stream()

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("What's the weather like in London?")

        print(f"Coordinator result: {result}")
        assert len(result) > 0
