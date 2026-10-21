from alembic import context

from backend.config import Settings
from backend.database import Database
from backend.models import Base


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


supplied_connection = context.config.attributes.get("connection")
if supplied_connection is not None:
    run(supplied_connection)
else:
    settings = Settings()
    if settings.database_url is None:
        raise RuntimeError("Set RUNTU_DATABASE_URL before running migrations")
    url = settings.database_url.get_secret_value()
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        database = Database(url)
        try:
            with database.engine.connect() as connection:
                run(connection)
        finally:
            database.dispose()
