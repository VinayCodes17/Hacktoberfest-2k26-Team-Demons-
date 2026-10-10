from alembic import context

from app.persistence.database import make_engine
from app.persistence.models import Base
from app.settings import Settings


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


supplied = context.config.attributes.get("connection")
if supplied is not None:
    run(supplied)
else:
    engine = make_engine(Settings().database_path)
    try:
        with engine.begin() as connection:
            run(connection)
    finally:
        engine.dispose()
