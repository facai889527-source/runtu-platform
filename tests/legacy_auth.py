"""Disposable historical-schema fixture: never an application bootstrap path."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import MetaData, Table
from backend.auth.service import HASHER


def seed_legacy_owner(database, password):
    metadata = MetaData()
    users = Table('auth_users', metadata, autoload_with=database.engine)
    bootstrap = Table('auth_bootstrap', metadata, autoload_with=database.engine)
    identifier, now = str(uuid4()), datetime.now(timezone.utc)
    with database.engine.begin() as connection:
        connection.execute(users.insert().values(id=identifier, username='operator', password_hash=HASHER.hash(password),
            active=True, is_admin=True, role='owner', created_at=now))
        connection.execute(bootstrap.insert().values(id=1, created_at=now))
    return identifier
