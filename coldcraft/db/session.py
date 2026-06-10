import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

_engine = None
_SessionLocal = None


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://gtm:gtm@localhost:5432/gtm",
    )


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = _database_url()
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


@contextmanager
def get_session():
    get_engine()
    session = _SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _migrate_jobs_table(engine) -> None:
    """Add normalized job columns when upgrading an existing jobs table."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("jobs")}
    additions = {
        "title": "VARCHAR(512) DEFAULT '' NOT NULL",
        "company": "VARCHAR(255)",
        "url": "VARCHAR(2048)",
        "location": "VARCHAR(255)",
        "description": "TEXT",
        "source": "VARCHAR(64) DEFAULT 'careers_page' NOT NULL",
        "scraped_at": "TIMESTAMP WITH TIME ZONE",
    }
    with engine.begin() as conn:
        for col, ddl in additions.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {col} {ddl}"))
        if "url" in additions and "url" not in existing:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_jobs_url ON jobs (url) "
                    "WHERE url IS NOT NULL"
                )
            )


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_jobs_table(engine)