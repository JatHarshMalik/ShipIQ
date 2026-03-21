"""In-memory storage for cargo, tank, and result state.

A real production service would back this with a database such as
PostgreSQL or Redis.  The interface is intentionally kept generic so that
swapping the backend only requires replacing this module.
"""

from __future__ import annotations

from typing import Optional

from app.models import InputPayload, OptimizationResult


class SessionStore:
    """Holds the most-recently submitted input and computed result."""

    def __init__(self) -> None:
        self._input: Optional[InputPayload] = None
        self._result: Optional[OptimizationResult] = None

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def save_input(self, payload: InputPayload) -> None:
        self._input = payload
        self._result = None  # invalidate stale result

    def get_input(self) -> Optional[InputPayload]:
        return self._input

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def save_result(self, result: OptimizationResult) -> None:
        self._result = result

    def get_result(self) -> Optional[OptimizationResult]:
        return self._result

    def clear(self) -> None:
        """Reset state (useful for testing)."""
        self._input = None
        self._result = None


# Module-level singleton – imported by main.py and injected via FastAPI
# dependency injection where needed.
store = SessionStore()
