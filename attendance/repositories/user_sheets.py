from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass(slots=True, frozen=True)
class UserSheet:
    user_id: int
    sheet_id: str


class SQLiteUserSheetRepository:

    def __init__(self, db: aiosqlite.Connection):
        self._db = db
        self._lock = asyncio.Lock()

    @classmethod
    async def create(cls, path: Path) -> "SQLiteUserSheetRepository":
        path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(path)
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sheets (
                user_id INTEGER PRIMARY KEY,
                sheet_id TEXT NOT NULL,
                updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            );
            """
        )
        await db.commit()
        return cls(db)

    async def close(self) -> None:
        await self._db.close()

    async def get_sheet_id(self, user_id: int) -> str | None:
        async with self._lock:
            cur = await self._db.execute(
                "SELECT sheet_id FROM user_sheets WHERE user_id = ?",
                (user_id,),
            )
            row = await cur.fetchone()
            await cur.close()
        return row[0] if row else None

    async def set_sheet_id(self, user_id: int, sheet_id: str) -> None:
        async with self._lock:
            await self._db.execute(
                """
                INSERT INTO user_sheets(user_id, sheet_id, updated_at)
                VALUES(?, ?, strftime('%s','now'))
                ON CONFLICT(user_id) DO UPDATE SET
                    sheet_id=excluded.sheet_id,
                    updated_at=excluded.updated_at
                """,
                (user_id, sheet_id),
            )
            await self._db.commit()
