"""Persistence layer.

V1 ships SQLite at ``~/.local/share/swarmlord/runs.db`` (POSIX) or
``%APPDATA%\\swarmlord\\runs.db`` (Windows). V2 will swap the backend for
Postgres via SQLAlchemy 2.x async; the API surface here is kept narrow on
purpose so that swap is straightforward.
"""

from __future__ import annotations

from swarmlord.storage.run_history import (
    RunHistory,
    default_db_path,
)

__all__ = ["RunHistory", "default_db_path"]
