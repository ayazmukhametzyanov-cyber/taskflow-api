import os
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://taskflow:taskflow@localhost:5433/taskflow_test",
)
# приложение и alembic читают адрес базы при импорте, поэтому подменяем его до импорта app
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

TABLES = "comments, tasks, labels, projects, users"


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return config


def ensure_database(url: str) -> None:
    """Создаёт базу, если её ещё нет; подключается к служебной базе postgres."""
    target = make_url(url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("select 1 from pg_database where datname = :name"),
            {"name": target.database},
        ).scalar()
        if not exists:
            conn.execute(text(f'create database "{target.database}"'))
    admin.dispose()


def recreate_schema(url: str) -> None:
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("drop schema public cascade"))
        conn.execute(text("create schema public"))
    engine.dispose()
