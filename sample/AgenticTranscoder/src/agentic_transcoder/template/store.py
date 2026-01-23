"""SQLite-based store for ChatKit threads and items."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from chatkit.store import NotFoundError, Store
from chatkit.types import Attachment, Page, ThreadItem, ThreadMetadata
from pydantic import TypeAdapter

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "threads.db"


class SQLiteStore(Store[dict]):
    """SQLite-based store for ChatKit with persistence."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.setup_tables()

    def setup_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT
            );
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            );
            CREATE INDEX IF NOT EXISTS idx_items_thread ON items(thread_id);
        """
        )
        self.conn.commit()

    def serialize_item(self, item: ThreadItem) -> str:
        return item.model_dump_json()

    def deserialize_item(self, data: str) -> ThreadItem:
        return TypeAdapter(ThreadItem).validate_json(data)

    async def load_thread(self, thread_id: str, context: dict) -> ThreadMetadata:
        row = self.conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
        if not row:
            thread = ThreadMetadata(
                id=thread_id,
                created_at=datetime.now(UTC),
            )
            await self.save_thread(thread, context)
            return thread
        return ThreadMetadata(
            id=row["id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def save_thread(self, thread: ThreadMetadata, context: dict) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO threads (id, title, created_at, metadata)
               VALUES (?, ?, ?, ?)""",
            (
                thread.id,
                thread.title,
                thread.created_at.isoformat(),
                json.dumps({}),
            ),
        )
        self.conn.commit()

    async def load_threads(
        self, limit: int, after: str | None, order: str, context: dict
    ) -> Page[ThreadMetadata]:
        order_dir = "DESC" if order == "desc" else "ASC"
        rows = self.conn.execute(
            f"SELECT * FROM threads ORDER BY created_at {order_dir} LIMIT ?",
            (limit + 1,),
        ).fetchall()

        threads = [
            ThreadMetadata(
                id=row["id"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows[:limit]
        ]
        return Page(data=threads, has_more=len(rows) > limit, after=None)

    async def load_thread_items(
        self, thread_id: str, after: str | None, limit: int, order: str, context: dict
    ) -> Page[ThreadItem]:
        order_dir = "DESC" if order == "desc" else "ASC"
        rows = self.conn.execute(
            f"""SELECT data FROM items
                WHERE thread_id = ?
                ORDER BY created_at {order_dir}
                LIMIT ?""",
            (thread_id, limit + 1),
        ).fetchall()

        items = [self.deserialize_item(row["data"]) for row in rows[:limit]]
        return Page(data=items, has_more=len(rows) > limit, after=None)

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: dict) -> None:
        created_at = getattr(item, "created_at", datetime.now(UTC))
        self.conn.execute(
            """INSERT OR REPLACE INTO items (id, thread_id, type, data, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                item.id,
                thread_id,
                type(item).__name__,
                self.serialize_item(item),
                created_at.isoformat(),
            ),
        )
        self.conn.commit()

    async def save_item(self, thread_id: str, item: ThreadItem, context: dict) -> None:
        await self.add_thread_item(thread_id, item, context)

    async def load_item(self, thread_id: str, item_id: str, context: dict) -> ThreadItem:
        row = self.conn.execute(
            "SELECT data FROM items WHERE id = ? AND thread_id = ?",
            (item_id, thread_id),
        ).fetchone()
        if not row:
            raise NotFoundError(f"Item {item_id} not found")
        return self.deserialize_item(row["data"])

    async def delete_thread(self, thread_id: str, context: dict) -> None:
        self.conn.execute("DELETE FROM items WHERE thread_id = ?", (thread_id,))
        self.conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
        self.conn.commit()

    async def delete_thread_item(self, thread_id: str, item_id: str, context: dict) -> None:
        self.conn.execute("DELETE FROM items WHERE id = ? AND thread_id = ?", (item_id, thread_id))
        self.conn.commit()

    async def save_attachment(self, attachment: Attachment, context: dict) -> None:
        raise NotImplementedError("Attachments not supported")

    async def load_attachment(self, attachment_id: str, context: dict) -> Attachment:
        raise NotImplementedError("Attachments not supported")

    async def delete_attachment(self, attachment_id: str, context: dict) -> None:
        raise NotImplementedError("Attachments not supported")
