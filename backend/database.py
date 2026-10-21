from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.models import ModuleConfigRecord


class Database:
    """Lazy connections; one transaction/session per service operation."""

    def __init__(self, url: str) -> None:
        parsed = make_url(url)
        if parsed.drivername not in ("sqlite", "sqlite+pysqlite", "postgresql+psycopg"):
            raise ValueError("Use sqlite or postgresql+psycopg for the database driver")
        connect_args = (
            {"check_same_thread": False} if parsed.get_backend_name() == "sqlite"
            else {"connect_timeout": 3}
        )
        self.engine = create_engine(parsed, pool_pre_ping=True, connect_args=connect_args)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self._sessions.begin() as session:
            yield session

    def is_ready(self) -> bool:
        try:
            with self.transaction() as session:
                # Check both connectivity and the required migrated table.
                session.execute(select(ModuleConfigRecord).limit(1))
            return True
        except SQLAlchemyError:
            return False

    def dispose(self) -> None:
        self.engine.dispose()
