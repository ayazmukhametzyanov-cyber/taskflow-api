import pytest
from pydantic import ValidationError

from app.config import Settings, settings


def test_database_url_comes_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/other")
    assert Settings(_env_file=None).database_url == "postgresql+psycopg2://u:p@db:5432/other"


def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    assert error.value.errors()[0]["loc"] == ("database_url",)


def test_env_file_is_read_and_extra_keys_are_ignored(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_USER=taskflow\nDATABASE_URL=postgresql+psycopg2://a:b@db/c\n",
        encoding="utf-8",
    )
    assert Settings(_env_file=env_file).database_url == "postgresql+psycopg2://a:b@db/c"


def test_module_settings_use_test_database():
    assert settings.database_url.endswith("/taskflow_test")
