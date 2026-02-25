from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from epic_trips_crm.db.engine import get_session


@dataclass(frozen=True)
class DBPingResult:
    ok: bool
    message: str


def ping_db() -> DBPingResult:
    """
    What it does:
    - Executes a lightweight SELECT 1 against Neon.

    Why it matters:
    - UI can quickly show connection status and provide actionable error info.

    Behavior:
    - Returns ok=True if query succeeds; otherwise ok=False with exception text.
    """
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return DBPingResult(ok=True, message="DB OK")
    except Exception as e:
        return DBPingResult(ok=False, message=f"DB error: {e}")
