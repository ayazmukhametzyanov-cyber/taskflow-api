import io

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from helpers import (
    ROOT,
    TEST_DATABASE_URL,
    alembic_config,
    ensure_database,
    recreate_schema,
)
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from alembic import command
from app.config import settings

TABLES = {"users", "projects", "labels", "tasks", "comments"}


@pytest.fixture
def scratch_url(monkeypatch):
    """Отдельная база: миграции вверх-вниз не должны трогать общую тестовую."""
    url = make_url(TEST_DATABASE_URL).set(database="taskflow_migrations").render_as_string(
        hide_password=False
    )
    ensure_database(url)
    recreate_schema(url)
    monkeypatch.setattr(settings, "database_url", url)
    return url


def table_names(url):
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def current_revision(url):
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def test_single_head_revision():
    script = ScriptDirectory.from_config(alembic_config())
    assert script.get_heads() == ["0001"]


def test_upgrade_creates_all_tables(scratch_url):
    command.upgrade(alembic_config(), "head")

    assert table_names(scratch_url) == TABLES
    assert current_revision(scratch_url) == "0001"


def test_upgrade_creates_keys_and_defaults(scratch_url):
    command.upgrade(alembic_config(), "head")
    engine = create_engine(scratch_url)
    inspector = inspect(engine)

    ondelete = {
        fk["constrained_columns"][0]: fk["options"].get("ondelete")
        for fk in inspector.get_foreign_keys("tasks") + inspector.get_foreign_keys("comments")
    }
    assert ondelete == {
        "project_id": "CASCADE",
        "assignee_id": "SET NULL",
        "label_id": "SET NULL",
        "task_id": "CASCADE",
        "author_id": "RESTRICT",
    }
    assert [u["column_names"] for u in inspector.get_unique_constraints("users")] == [["email"]]
    assert [u["column_names"] for u in inspector.get_unique_constraints("labels")] == [["name"]]
    defaults = {c["name"]: c["default"] for c in inspector.get_columns("tasks")}
    assert defaults["status"] == "'open'::character varying"
    assert defaults["priority"] == "'medium'::character varying"
    engine.dispose()


def test_downgrade_removes_everything(scratch_url):
    config = alembic_config()
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    assert table_names(scratch_url) == set()
    assert current_revision(scratch_url) is None


def test_up_down_up_cycle_is_clean(scratch_url):
    config = alembic_config()
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert table_names(scratch_url) == TABLES


def test_models_match_migrations(scratch_url):
    config = alembic_config()
    command.upgrade(config, "head")
    command.check(config)


def test_offline_mode_renders_sql_without_connecting(monkeypatch):
    # адрес на несуществующий сервер: в автономном режиме подключения быть не должно
    monkeypatch.setattr(
        settings, "database_url", "postgresql+psycopg2://nobody@nowhere.invalid/none"
    )
    out = io.StringIO()
    config = alembic_config()
    config.output_buffer = out

    command.upgrade(config, "head", sql=True)

    sql = out.getvalue()
    assert "CREATE TABLE users" in sql
    assert "CREATE TABLE comments" in sql
    assert "INSERT INTO alembic_version" in sql


def test_env_without_ini_file_skips_logging_setup(scratch_url):
    config = Config()
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, "head")

    assert table_names(scratch_url) == TABLES
    with create_engine(scratch_url).connect() as conn:
        assert conn.execute(text("select count(*) from users")).scalar() == 0
