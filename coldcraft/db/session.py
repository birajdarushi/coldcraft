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


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)