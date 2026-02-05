from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from epic_trips_crm.config.settings import require_database_url

_ENGINE: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _ENGINE, SessionLocal
    if _ENGINE is None:
        _ENGINE = create_engine(
            require_database_url(),
            pool_pre_ping=True,
        )
        SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False)
    return _ENGINE


@contextmanager
def get_session() -> Iterator[Session]:
    if SessionLocal is None:
        get_engine()

    assert SessionLocal is not None  # for type checkers
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
