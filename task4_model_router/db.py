import asyncio
import time
from pathlib import Path

import aiosqlite


DB_PATH = Path(__file__).with_name("gateway.db")

TOKEN_LIMIT = 50_000
WINDOW_SECONDS = 60

_lock = asyncio.Lock()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_key TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        await db.commit()


async def get_recent_usage(
    tenant_key: str,
    now: float | None = None,
) -> int:
    now = now or time.time()
    cutoff = now - WINDOW_SECONDS

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT COALESCE(SUM(tokens), 0)
            FROM token_usage
            WHERE tenant_key = ?
              AND created_at >= ?
            """,
            (tenant_key, cutoff),
        )

        row = await cursor.fetchone()

    return int(row[0] or 0)


async def check_and_record_usage(
    tenant_key: str,
    tokens: int,
) -> tuple[bool, int]:
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    async with _lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                DELETE FROM token_usage
                WHERE created_at < ?
                """,
                (cutoff,),
            )

            cursor = await db.execute(
                """
                SELECT COALESCE(SUM(tokens), 0)
                FROM token_usage
                WHERE tenant_key = ?
                  AND created_at >= ?
                """,
                (tenant_key, cutoff),
            )

            row = await cursor.fetchone()
            current_usage = int(row[0] or 0)

            projected_usage = current_usage + tokens

            if projected_usage > TOKEN_LIMIT:
                await db.commit()
                return False, current_usage

            await db.execute(
                """
                INSERT INTO token_usage (
                    tenant_key,
                    tokens,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    tenant_key,
                    tokens,
                    now,
                ),
            )

            await db.commit()

    return True, projected_usage