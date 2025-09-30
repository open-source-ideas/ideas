from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable, Optional


class Database:
    """Lightweight SQLite wrapper for per-user categories and messages."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # enable foreign keys on every connection
        self._connect_args = {"detect_types": sqlite3.PARSE_DECLTYPES, "check_same_thread": False}

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, **self._connect_args)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialise(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    UNIQUE (user_id, name)
                );

                CREATE TABLE IF NOT EXISTS active_categories (
                    user_id INTEGER PRIMARY KEY,
                    category_id INTEGER NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS storage_channels (
                    user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    original_chat TEXT,
                    original_sender TEXT,
                    forward_date TEXT,
                    saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS message_links (
                    message_id INTEGER PRIMARY KEY,
                    forwarded_chat_id INTEGER NOT NULL,
                    forwarded_message_id INTEGER NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
                );
                """
            )

    def add_category(self, user_id: int, name: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT OR IGNORE INTO categories (user_id, name) VALUES (?, ?)",
                (user_id, name.strip()),
            )

    def list_categories(self, user_id: int) -> list[str]:
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "SELECT name FROM categories WHERE user_id = ? ORDER BY name COLLATE NOCASE",
                (user_id,),
            )
            return [row[0] for row in cur.fetchall()]

    def list_categories_full(self, user_id: int) -> list[tuple[int, str]]:
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name COLLATE NOCASE",
                (user_id,),
            )
            return cur.fetchall()

    def set_active_category(self, user_id: int, name: str) -> bool:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "SELECT id FROM categories WHERE user_id = ? AND name = ?",
                (user_id, name.strip()),
            )
            row = cur.fetchone()
            if not row:
                return False
            category_id = row[0]
            conn.execute(
                "INSERT INTO active_categories (user_id, category_id) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET category_id = excluded.category_id",
                (user_id, category_id),
            )
            return True

    def set_active_category_by_id(self, user_id: int, category_id: int) -> Optional[str]:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "SELECT name FROM categories WHERE user_id = ? AND id = ?",
                (user_id, category_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            name = row[0]
            conn.execute(
                "INSERT INTO active_categories (user_id, category_id) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET category_id = excluded.category_id",
                (user_id, category_id),
            )
            return name

    def get_active_category(self, user_id: int) -> Optional[str]:
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "SELECT c.name FROM active_categories ac "
                "JOIN categories c ON ac.category_id = c.id "
                "WHERE ac.user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def save_message(
        self,
        user_id: int,
        text: str,
        *,
        category_name: Optional[str] = None,
        category_id: Optional[int] = None,
        original_chat: Optional[str] = None,
        original_sender: Optional[str] = None,
        forward_date: Optional[str] = None,
    ) -> Optional[int]:
        text = (text or "").strip()
        if not text:
            return None

        with closing(self._connect()) as conn, conn:
            if category_id is not None:
                cur = conn.execute(
                    "SELECT id FROM categories WHERE user_id = ? AND id = ?",
                    (user_id, category_id),
                )
            elif category_name:
                cur = conn.execute(
                    "SELECT id FROM categories WHERE user_id = ? AND name = ?",
                    (user_id, category_name),
                )
            else:
                cur = conn.execute(
                    "SELECT category_id FROM active_categories WHERE user_id = ?",
                    (user_id,),
                )
            row = cur.fetchone()
            if not row:
                return None
            category_id = row[0]
            cur = conn.execute(
                "INSERT INTO messages (user_id, category_id, text, original_chat, original_sender, forward_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, category_id, text, original_chat, original_sender, forward_date),
            )
            return cur.lastrowid

    def attach_forward_copy(self, message_id: int, chat_id: int, forwarded_message_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO message_links (message_id, forwarded_chat_id, forwarded_message_id) "
                "VALUES (?, ?, ?)",
                (message_id, chat_id, forwarded_message_id),
            )

    def list_messages(self, user_id: int, category_name: str) -> Iterable[tuple[int, str, str, Optional[int], Optional[int]]]:
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "SELECT m.id, m.text, m.saved_at, ml.forwarded_chat_id, ml.forwarded_message_id "
                "FROM messages m "
                "JOIN categories c ON m.category_id = c.id "
                "LEFT JOIN message_links ml ON ml.message_id = m.id "
                "WHERE m.user_id = ? AND c.name = ? "
                "ORDER BY m.saved_at DESC",
                (user_id, category_name),
            )
            yield from cur.fetchall()

    def search_messages(self, user_id: int, term: str) -> Iterable[tuple[str, str, str, Optional[int], Optional[int]]]:
        pattern = f"%{term.lower()}%"
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "SELECT c.name, m.text, m.saved_at, ml.forwarded_chat_id, ml.forwarded_message_id "
                "FROM messages m "
                "JOIN categories c ON m.category_id = c.id "
                "LEFT JOIN message_links ml ON ml.message_id = m.id "
                "WHERE m.user_id = ? AND LOWER(m.text) LIKE ? "
                "ORDER BY m.saved_at DESC LIMIT 25",
                (user_id, pattern),
            )
            yield from cur.fetchall()

    def set_storage_channel(self, user_id: int, chat_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO storage_channels (user_id, chat_id) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET chat_id = excluded.chat_id",
                (user_id, chat_id),
            )

    def clear_storage_channel(self, user_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM storage_channels WHERE user_id = ?", (user_id,))

    def get_storage_channel(self, user_id: int) -> Optional[int]:
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "SELECT chat_id FROM storage_channels WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
