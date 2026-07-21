# mew/mew_db.py
"""
Separate SQLite database for the Meowie module.
Holds the list of added users and per-user game state.
"""
import aiosqlite
import datetime
from . import config


class MewDB:
    def __init__(self, path: str = config.DB_PATH):
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def init(self):
        self._conn = await aiosqlite.connect(self.path)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS added_users (
                account_id  TEXT PRIMARY KEY,
                session_name TEXT,
                added_at    TEXT NOT NULL
            )
        """)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS mew_state (
                account_id  TEXT PRIMARY KEY,
                points      INTEGER DEFAULT 0,
                extra       TEXT
            )
        """)
        # NEW TABLE: Tracks if a specific task is on/off per user
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS task_states (
                account_id  TEXT,
                task_name   TEXT,
                enabled     INTEGER DEFAULT 1,
                PRIMARY KEY (account_id, task_name)
            )
        """)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    # --- added users ---
    async def add_user(self, account_id: str, session_name: str):
        await self._conn.execute(
            "INSERT OR IGNORE INTO added_users(account_id, session_name, added_at) VALUES (?,?,?)",
            (account_id, session_name, datetime.datetime.utcnow().isoformat())
        )
        await self._conn.commit()

    async def remove_user(self, account_id: str):
        await self._conn.execute("DELETE FROM added_users WHERE account_id=?", (account_id,))
        await self._conn.execute("DELETE FROM task_states WHERE account_id=?", (account_id,))
        await self._conn.commit()

    async def is_added(self, account_id: str) -> bool:
        async with self._conn.execute(
            "SELECT 1 FROM added_users WHERE account_id=?", (account_id,)
        ) as cur:
            return await cur.fetchone() is not None

    async def list_added(self) -> list[tuple[str, str]]:
        async with self._conn.execute(
            "SELECT account_id, session_name FROM added_users ORDER BY added_at"
        ) as cur:
            return await cur.fetchall()

    # --- task states ---
    async def set_task_enabled(self, account_id: str, task_name: str, enabled: bool):
        await self._conn.execute(
            "INSERT INTO task_states(account_id, task_name, enabled) VALUES(?,?,?) "
            "ON CONFLICT(account_id, task_name) DO UPDATE SET enabled=?",
            (account_id, task_name, int(enabled), int(enabled))
        )
        await self._conn.commit()

    async def is_task_enabled(self, account_id: str, task_name: str, default: bool) -> bool:
        async with self._conn.execute(
            "SELECT enabled FROM task_states WHERE account_id=? AND task_name=?",
            (account_id, task_name)
        ) as cur:
            row = await cur.fetchone()
            if row is None:
                return default
            return bool(row[0])