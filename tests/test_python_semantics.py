"""Section 10: Python Semantics Tests - Real API calls.

Tests for:
- 10.1 Typed data transformation (Pure Python control flow)
- 10.2 Control structures (for, if/else, while, asyncio.gather)

This is THE CORE VALUE of AgenticFlow:
Pure Python control over Agent data flow.

All tests use real GPT API calls. No mocks.
"""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from agentic_flow import Agent, Runner, phase, reasoning


class Analysis(BaseModel):
    """Analysis result."""

    category: str
    confidence: float
    keywords: list[str]


class Decision(BaseModel):
    """Decision result."""

    action: str
    reason: str


class Review(BaseModel):
    """Review result."""

    approved: bool
    feedback: str


class TestTypedDataTransformation:
    """10.1 Typed data transformation - Pure Python control flow."""

    @pytest.mark.asyncio
    async def test_pydantic_to_prompt_transformation(self, handler_log):
        """Pydantic output can be used to construct next prompt."""
        analyzer = Agent(
            name="analyzer",
            instructions="Analyze input. Return category, confidence, keywords.",
            model="gpt-5.2",
            output_type=Analysis,
        )

        decider = Agent(
            name="decider",
            instructions="Based on analysis, decide action (approve/reject).",
            model="gpt-5.2",
            output_type=Decision,
        )

        async def flow(user_input: str) -> str:
            async with phase("Analysis"):
                analysis: Analysis = await analyzer(user_input).stream()

            prompt = f"""
            Category: {analysis.category}
            Confidence: {analysis.confidence}
            Keywords: {", ".join(analysis.keywords)}

            Should we approve this?
            """

            async with phase("Decision"):
                decision: Decision = await decider(prompt).stream()

            return f"Action: {decision.action}, Reason: {decision.reason}"

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("This is a positive customer review about fast delivery")

        assert "Action:" in result
        assert "Reason:" in result
        print(f"Typed flow result: {result}")

    @pytest.mark.asyncio
    async def test_conditional_flow_based_on_type(self, handler_log):
        """Python if/else based on Pydantic field values."""
        analyzer = Agent(
            name="classifier",
            instructions="Return category as 'urgent' or 'normal' with confidence 0-1.",
            model="gpt-5.2",
            output_type=Analysis,
        )

        urgent_handler = Agent(
            name="urgent",
            instructions="Handle urgent case. Reply with URGENT HANDLED.",
            model="gpt-5.2",
        )

        normal_handler = Agent(
            name="normal",
            instructions="Handle normal case. Reply with NORMAL HANDLED.",
            model="gpt-5.2",
        )

        async def flow(user_input: str) -> str:
            async with phase("Classify"):
                analysis: Analysis = await analyzer(user_input).stream()

            if analysis.category.lower() == "urgent" or analysis.confidence > 0.8:
                async with phase("Urgent"):
                    return await urgent_handler(user_input).stream()
            else:
                async with phase("Normal"):
                    return await normal_handler(user_input).stream()

        chat = Runner(flow=flow, handler=handler_log)

        result = await chat("EMERGENCY: Server is down!")
        print(f"Urgent case: {result}")

    @pytest.mark.asyncio
    async def test_ide_completion_works(self):
        """Verify that IDE completion works (type safety)."""
        analyzer = Agent(
            name="typed",
            instructions="Return category, confidence, keywords.",
            model="gpt-5.2",
            output_type=Analysis,
        )

        result: Analysis = await analyzer("Test input")

        category: str = result.category
        confidence: float = result.confidence
        keywords: list[str] = result.keywords

        assert isinstance(category, str)
        assert isinstance(confidence, float)
        assert isinstance(keywords, list)


class TestControlStructures:
    """10.2 Control structures - for, if/else, while, asyncio.gather."""

    @pytest.mark.asyncio
    async def test_for_loop(self, handler_log):
        """for loop with multiple agent calls."""
        processor = Agent(
            name="processor",
            instructions="Process item and return brief result.",
            model="gpt-5.2",
        )

        async def flow(user_input: str) -> str:
            items = ["apple", "banana", "cherry"]
            results = []

            for item in items:
                async with phase(f"Process {item}"):
                    result = await processor(f"Process: {item}").stream()
                    results.append(result)

            return f"Processed {len(results)} items"

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("test")

        assert "3" in result
        print(f"For loop: {result}")

    @pytest.mark.asyncio
    async def test_if_else(self, handler_log):
        """if/else branching based on condition."""
        classifier = Agent(
            name="classifier",
            instructions="Reply COMPLEX if question needs deep analysis, else SIMPLE.",
            model="gpt-5.2",
        )

        simple_handler = Agent(
            name="simple",
            instructions="Give a brief answer.",
            model="gpt-5.2",
        )

        complex_handler = Agent(
            name="complex",
            instructions="Give a detailed analysis.",
            model="gpt-5.2",
            model_settings=reasoning("low"),
        )

        async def flow(user_input: str) -> str:
            async with phase("Classify"):
                classification = await classifier(user_input).stream()

            if "COMPLEX" in classification.upper():
                async with phase("Complex Analysis"):
                    return await complex_handler(user_input).stream()
            else:
                async with phase("Simple Answer"):
                    return await simple_handler(user_input).stream()

        chat = Runner(flow=flow, handler=handler_log)

        result = await chat("What is the meaning of life and consciousness?")
        assert len(result) > 0
        print(f"If/else result: {result[:100]}")

    @pytest.mark.asyncio
    async def test_while_loop_with_typed_condition(self, handler_log):
        """while loop with Pydantic-based exit condition."""
        reviewer = Agent(
            name="reviewer",
            instructions=("Review text. Set approved=true if good, false if needs work."),
            model="gpt-5.2",
            output_type=Review,
        )

        refiner = Agent(
            name="refiner",
            instructions="Improve text based on feedback.",
            model="gpt-5.2",
        )

        async def flow(user_input: str) -> str:
            draft = user_input
            iteration = 0
            max_iterations = 3

            while iteration < max_iterations:
                async with phase(f"Review {iteration + 1}"):
                    review: Review = await reviewer(f"Review: {draft}").stream()

                if review.approved:
                    return f"Approved after {iteration + 1} iterations: {draft}"

                async with phase(f"Refine {iteration + 1}"):
                    prompt = f"Text: {draft}\nFeedback: {review.feedback}"
                    draft = await refiner(prompt).stream()

                iteration += 1

            return f"Max iterations reached: {draft}"

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("hello world this is a test")

        assert len(result) > 0
        print(f"While loop: {result[:100]}")

    @pytest.mark.asyncio
    async def test_asyncio_gather_with_isolated(self, handler_log):
        """asyncio.gather with isolated() for parallel execution."""
        searcher = Agent(
            name="searcher",
            instructions="Search for information about the topic. Reply briefly.",
            model="gpt-5.2",
        )

        async def flow(user_input: str) -> str:
            topics = ["Python", "JavaScript", "Rust"]

            results = await asyncio.gather(
                searcher(f"Tell me about {topics[0]}").isolated(),
                searcher(f"Tell me about {topics[1]}").isolated(),
                searcher(f"Tell me about {topics[2]}").isolated(),
            )

            return f"Found info on {len(results)} topics"

        chat = Runner(flow=flow)
        result = await chat("test")

        assert "3" in result
        print(f"Gather result: {result}")

    @pytest.mark.asyncio
    async def test_nested_loops(self, handler_log):
        """Nested loops demonstrating Python semantics."""
        await asyncio.sleep(0.1)

        processor = Agent(
            name="processor",
            instructions="Process item briefly. Reply with one word.",
            model="gpt-5.2",
        )

        async def flow(user_input: str) -> str:
            categories = ["X", "Y"]
            count = 0

            for cat in categories:
                async with phase(f"Process-{cat}"):
                    await processor(f"Process {cat}").stream()
                    count += 1

            return f"Processed {count} items"

        chat = Runner(flow=flow, handler=handler_log)
        result = await chat("test")

        assert "2" in result
        print(f"Nested loops: {result}")
