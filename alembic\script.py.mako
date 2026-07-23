"""${message}"""
from alembic import context
from alembic import context
config = context.config
target_metadata = config.attributes.get('target_metadata', None)

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = config.attributes.get('connection', None)
    if connectable is None:
        connectable = config.attributes.get('engine', None)
    if connectable is not None:
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    else:
        raise RuntimeError("No connection or engine available")

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
