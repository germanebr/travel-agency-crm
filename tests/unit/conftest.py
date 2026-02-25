from __future__ import annotations

import os
from importlib import import_module

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def import_first(module_path: str, candidates: list[str]):
    mod = import_module(module_path)
    for name in candidates:
        if hasattr(mod, name):
            return getattr(mod, name)
    raise ImportError(f"None of {candidates} found in {module_path}")


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def engine():
    # IMPORTANT: your models use Postgres schema "epic_trips_crm".
    # SQLite has no schemas, so we translate that schema to None.
    schema_map = {"epic_trips_crm": None}

    eng = create_engine("sqlite+pysqlite:///:memory:", future=True)

    # Apply schema translation for all operations using this engine
    eng = eng.execution_options(schema_translate_map=schema_map)

    return eng


@pytest.fixture()
def session(engine):
    Base = import_first("epic_trips_crm.db.models", ["Base"])

    # Create all tables in SQLite, with schema translated away
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
        expire_on_commit=False,
    )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
