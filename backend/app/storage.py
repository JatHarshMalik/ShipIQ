"""Persistent SQLite storage for cargo, tank, and result state.

Each session is identified by a session_id string.  The default singleton
``store`` uses the session_id ``"default"`` so legacy single-user code works
unchanged, while multi-user callers can pass their own session_id.

Schema
------
One table:
  sessions(session_id TEXT PRIMARY KEY, input_json TEXT, result_json TEXT)

JSON columns hold Pydantic-serialised models so no migration is needed
when models gain new optional fields.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator, Optional

from app.models import InputPayload, OptimizationResult

DB_PATH = os.getenv("SHIPIQ_DB_PATH", "shipiq.db")

_lock = threading.Lock()


@contextmanager
def _get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Thread-safe SQLite connection context manager."""
    with _lock:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _init_db() -> None:
    """Create the sessions table if it does not already exist."""
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id  TEXT PRIMARY KEY,
                input_json  TEXT,
                result_json TEXT
            )
            """
        )


_init_db()


class SessionStore:
    """Persistent per-session store backed by SQLite."""

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def save_input(
        self, payload: InputPayload, session_id: str = "default"
    ) -> None:
        """Persist input and clear any stale result for this session."""
        data = payload.model_dump_json()
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, input_json, result_json)
                VALUES (?, ?, NULL)
                ON CONFLICT(session_id) DO UPDATE SET
                    input_json  = excluded.input_json,
                    result_json = NULL
                """,
                (session_id, data),
            )

    def get_input(self, session_id: str = "default") -> Optional[InputPayload]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT input_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None or row["input_json"] is None:
            return None
        return InputPayload.model_validate_json(row["input_json"])

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def save_result(
        self, result: OptimizationResult, session_id: str = "default"
    ) -> None:
        data = result.model_dump_json()
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, input_json, result_json)
                VALUES (?, NULL, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    result_json = excluded.result_json
                """,
                (session_id, data),
            )

    def get_result(
        self, session_id: str = "default"
    ) -> Optional[OptimizationResult]:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT result_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None or row["result_json"] is None:
            return None
        return OptimizationResult.model_validate_json(row["result_json"])

    def clear(self, session_id: str = "default") -> None:
        """Delete the session row (used in tests and by the clear endpoint)."""
        with _get_conn() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE session_id = ?", (session_id,)
            )


# Module-level singleton – "default" session_id for backward-compat.
store = SessionStore()
