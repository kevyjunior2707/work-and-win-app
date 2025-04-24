# migrations/env.py (Configuration Standard pour Application Factory)

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- Ajout pour Flask-Migrate avec Application Factory ---
import os
import sys
# Ajoute le répertoire racine du projet au PYTHONPATH
# Permet à Alembic de trouver le module 'app'
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# Importe create_app et db depuis votre application
from app import create_app, db
# Crée une instance de l'application Flask pour obtenir le contexte
# Utilise la configuration par défaut (qui devrait lire .env ou les variables d'env)
flask_app = create_app()
# --- Fin Ajout ---


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- Ajout pour Flask-Migrate ---
# Définit l'URL de la base de données à partir de la config Flask
# Cela assure qu'Alembic utilise la même BDD que l'application
# (Important pour lire DATABASE_URL depuis les variables d'environnement sur Render)
config.set_main_option('sqlalchemy.url', flask_app.config['SQLALCHEMY_DATABASE_URI'])
# --- Fin Ajout ---

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# --- Modifié pour Flask-Migrate ---
# Utilise les métadonnées de l'objet db de Flask-SQLAlchemy
target_metadata = db.metadata
# --- Fin Modification ---

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()