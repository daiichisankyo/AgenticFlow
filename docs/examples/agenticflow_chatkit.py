"""Agentic Flow ChatKit Server - Minimal boilerplate."""

from agents import SQLiteSession
from chatkit.server import ChatKitServer

import agentic_flow as af

from .agenticflow_flow import my_flow


class MyServer(ChatKitServer):
    async def respond(self, thread, item, context):
        user_message = item.content[0].text if item else ""
        session = SQLiteSession(session_id=thread.id, db_path="chat.db")
        runner = af.Runner(flow=my_flow, session=session)

        async for event in af.chatkit.run_with_chatkit_context(
            runner, thread, self.store, context, user_message
        ):
            yield event
