"""AF: Custom ModelProvider skeleton.

This shows how to plug a custom model implementation into the SDK and
use it from AF. Replace the TODOs with your internal API logic.

Usage:
    python sample/multi_provider/custom_provider.py
"""

import asyncio
import uuid
from typing import Any

import agentic_flow as af
from agents import RunConfig
from agents.items import ModelResponse
from agents.models.interface import Model, ModelProvider
from agents.usage import Usage
from openai.types.responses import ResponseOutputMessage, ResponseOutputText


class MyCompanyModel(Model):
    """Connection to internal LLM API."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name

    @staticmethod
    def _extract_text(input_data: str | list[Any]) -> str:
        if isinstance(input_data, str):
            return input_data

        for item in reversed(input_data):
            if not isinstance(item, dict):
                continue
            if item.get("role") != "user":
                continue
            content = item.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") in {"input_text", "text"}:
                        text = part.get("text")
                        if isinstance(text, str):
                            return text
        return "(no user text)"

    async def get_response(
        self,
        system_instructions,
        input,
        model_settings,
        tools,
        output_schema,
        handoffs,
        tracing,
        **kwargs,
    ):
        user_text = self._extract_text(input)
        model_name = self.model_name or "my-company-default"
        text = f"[MyCompanyProvider mock]\nmodel={model_name}\necho={user_text}"
        message = ResponseOutputMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            role="assistant",
            status="completed",
            type="message",
            content=[
                ResponseOutputText(
                    type="output_text",
                    text=text,
                    annotations=[],
                )
            ],
        )
        return ModelResponse(
            output=[message],
            usage=Usage(requests=1),
            response_id=f"resp_{uuid.uuid4().hex[:8]}",
        )

    def stream_response(
        self,
        system_instructions,
        input,
        model_settings,
        tools,
        output_schema,
        handoffs,
        tracing,
        **kwargs,
    ):
        raise NotImplementedError(
            "This mock provider implements only non-streaming get_response()."
        )


class MyCompanyProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        return MyCompanyModel(model_name)


async def main() -> None:
    agent = af.Agent(
        name="internal",
        instructions="Use the internal model.",
        model="my-model-v3",
    )
    config = RunConfig(model_provider=MyCompanyProvider())

    async def flow(query: str) -> str:
        async with af.phase("Process", persist=True):
            return await agent(query).run_config(config)

    runner = af.Runner(flow=flow)
    result = await runner("Test request")
    print("==== result ====")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
