"""FastAPI server with ChatKit integration.

Run:
    cd examples/router
    uv run uvicorn server:app --reload --port 8000
"""

from __future__ import annotations

import pathlib
import sys
from collections.abc import AsyncIterator
from typing import Any

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env.local")

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "src"))

from agentic_flow import Runner
from agentic_flow.chatkit import run_with_chatkit_context
from agents import SQLiteSession
from chatkit.server import ChatKitServer, StreamingResult
from chatkit.types import (
    Attachment,
    StreamOptions,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from flow import router_flow
from openai.types.responses import ResponseInputContentParam
from starlette.responses import JSONResponse
from store import DATA_DIR, SQLiteStore

app = FastAPI(title="Router Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatServer(ChatKitServer[dict[str, Any]]):
    """ChatKit server for Router Agent."""

    def __init__(self) -> None:
        self.sqlite_store = SQLiteStore()
        super().__init__(self.sqlite_store)

    async def respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        user_message = ""
        if item and item.content:
            for part in item.content:
                if hasattr(part, "text"):
                    user_message += part.text

        session = SQLiteSession(
            session_id=thread.id,
            db_path=str(DATA_DIR / "sessions.db"),
        )
        runner = Runner(flow=router_flow, session=session)

        async for event in run_with_chatkit_context(
            runner, thread, self.sqlite_store, context, user_message
        ):
            yield event

    def get_stream_options(self, thread: ThreadMetadata, context: dict[str, Any]) -> StreamOptions:
        return StreamOptions(allow_cancel=True)

    async def to_message_content(self, attachment: Attachment) -> ResponseInputContentParam:
        raise RuntimeError("Attachments not supported")


server = ChatServer()


@app.post("/chatkit")
async def chatkit_endpoint(request: Request) -> Response:
    """ChatKit endpoint."""
    payload = await request.body()
    result = await server.process(payload, {"request": request})

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
