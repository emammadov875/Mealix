import sqlite3
import json
import os
from typing import List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "fridge_bot.db")


class Database:
    def __init__(self):
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    name        TEXT,
                    dietary     TEXT DEFAULT 'none',
                    favourites  TEXT DEFAULT '[]',
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def upsert_user(self, user_id: int, name: str):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, name)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET name = excluded.name
                """,
                (user_id, name),
            )

    def get_dietary(self, user_id: int) -> str:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT dietary FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row["dietary"] if row else "none"

    def set_dietary(self, user_id: int, dietary: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET dietary = ? WHERE user_id = ?",
                (dietary, user_id),
            )

    def get_favourites(self, user_id: int) -> List[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT favourites FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if not row:
                return []
            try:
                return json.loads(row["favourites"])
            except Exception:
                return []

    def add_favourite(self, user_id: int, recipe_name: str):
        favs = self.get_favourites(user_id)
        if recipe_name not in favs:
            favs.insert(0, recipe_name)
            favs = favs[:20]  # Keep max 20
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET favourites = ? WHERE user_id = ?",
                (json.dumps(favs), user_id),
            )
