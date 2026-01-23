# ChatKit Integration Guide

When `frontend=True`, generate a full-stack application with ChatKit.

---

## Intent

ChatKit provides a standardized protocol for chat UIs.
Generate applications that match `sample/guide` quality:
- Backend: FastAPI + ChatKitServer
- Frontend: React + ChatKit (copied from template)
- Storage: SQLiteStore for thread persistence

---

## Architecture

```
Frontend (React) ───POST /chatkit──→ Backend (FastAPI)
                                          │
                                          ▼
                                    ChatKitServer.respond()
                                          │
                                          ▼
                                    Runner(flow, session)
                                          │
                                          ▼
                                    run_with_chatkit_context()
```

---

## Required Files (frontend=True)

| File | Source | Description |
|------|--------|-------------|
| `store.py` | `copy_store(cwd)` | SQLiteStore for threads |
| `frontend/` | `copy_frontend(cwd)` | React + ChatKit UI |
| `server.py` | **Generate** | ChatKitServer implementation |
| `agent_specs.py` | **Generate** | Agent definitions |
| `flow.py` | **Generate** | Flow with phases |

---

## server.py Pattern (MUST follow)

```python
"""FastAPI server with ChatKit integration."""
from __future__ import annotations

import pathlib
from collections.abc import AsyncIterator
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from starlette.responses import JSONResponse

load_dotenv(pathlib.Path(__file__).parent / ".env.local")

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
from openai.types.responses import ResponseInputContentParam

from flow import main_flow  # Your flow function
from store import DATA_DIR, SQLiteStore

app = FastAPI(title="Project Title")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AppServer(ChatKitServer[dict[str, Any]]):
    """ChatKit server bridging frontend to Agentic Flow."""

    def __init__(self) -> None:
        self.sqlite_store = SQLiteStore()
        super().__init__(self.sqlite_store)

    async def respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        # Extract user message text
        user_message = ""
        if item and item.content:
            for part in item.content:
                if hasattr(part, "text"):
                    user_message += part.text

        # Create session per thread (conversation history)
        session = SQLiteSession(
            session_id=thread.id,
            db_path=str(DATA_DIR / "sessions.db"),
        )

        # Runner is mandatory - never call flow directly
        runner = Runner(flow=main_flow, session=session)

        # Stream events to ChatKit
        async for event in run_with_chatkit_context(
            runner, thread, self.sqlite_store, context, user_message
        ):
            yield event

    def get_stream_options(
        self, thread: ThreadMetadata, context: dict[str, Any]
    ) -> StreamOptions:
        return StreamOptions(allow_cancel=True)

    async def to_message_content(
        self, attachment: Attachment
    ) -> ResponseInputContentParam:
        raise RuntimeError("Attachments not supported")


server = AppServer()


@app.post("/chatkit")
async def chatkit_endpoint(request: Request) -> Response:
    """ChatKit protocol endpoint."""
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
```

---

## Key Integration Points

### 1. ChatKitServer Inheritance

```python
class AppServer(ChatKitServer[dict[str, Any]]):
    def __init__(self) -> None:
        self.sqlite_store = SQLiteStore()
        super().__init__(self.sqlite_store)
```

### 2. respond() Method

```python
async def respond(self, thread, item, context) -> AsyncIterator[ThreadStreamEvent]:
    # Extract text from user message
    user_message = extract_text_from_item(item)

    # Session per thread
    session = SQLiteSession(session_id=thread.id, ...)

    # Runner is mandatory
    runner = Runner(flow=main_flow, session=session)

    # Stream via run_with_chatkit_context
    async for event in run_with_chatkit_context(runner, thread, store, context, user_message):
        yield event
```

### 3. /chatkit Endpoint

```python
@app.post("/chatkit")
async def chatkit_endpoint(request: Request) -> Response:
    payload = await request.body()
    result = await server.process(payload, {"request": request})

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    # ... handle other response types
```

---

## Forbidden Patterns

```python
# WRONG: Direct flow call in respond()
async def respond(self, thread, item, context):
    result = await my_flow(user_message)  # NO!
    yield some_event

# WRONG: No session
async def respond(self, thread, item, context):
    runner = Runner(flow=my_flow)  # Missing session!

# WRONG: Simple /chat endpoint (use /chatkit)
@app.post("/chat")  # Wrong endpoint for ChatKit
async def chat(request):
    ...
```

---

## Running the Application

```bash
# Backend (Terminal 1)
cd output_dir
uv run uvicorn server:app --port 8000

# Frontend (Terminal 2)
cd output_dir/frontend
npm install
npm run dev
```

Frontend: http://localhost:5173
Backend: http://localhost:8000
