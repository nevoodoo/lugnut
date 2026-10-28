from alembic import context
from sqlalchemy import create_engine

url = context.config.get_main_option("sqlalchemy.url")
assert url is not None
# Deliberately a plain engine: foreign_keys stays off during migrations. With it on, batch
# table rebuilds would cascade-delete child rows. Never switch this to get_engine.
engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
