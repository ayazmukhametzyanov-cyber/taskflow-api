import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app import database, models
from app.routers._common import raise_conflict


def test_raise_conflict_is_409_with_original_error_attached():
    original = IntegrityError("insert", {}, Exception("duplicate"))
    with pytest.raises(HTTPException) as error:
        raise_conflict(original)
    assert error.value.status_code == 409
    assert error.value.detail == "Дубликат значения или неверная ссылка"
    assert error.value.__cause__ is original


def test_metadata_has_five_tables():
    assert set(database.Base.metadata.tables) == {
        "users",
        "projects",
        "labels",
        "tasks",
        "comments",
    }


def test_foreign_key_actions():
    def action(model, column):
        (fk,) = model.__table__.c[column].foreign_keys
        return fk.ondelete

    assert action(models.Task, "project_id") == "CASCADE"
    assert action(models.Task, "assignee_id") == "SET NULL"
    assert action(models.Task, "label_id") == "SET NULL"
    assert action(models.Comment, "task_id") == "CASCADE"
    assert action(models.Comment, "author_id") == "RESTRICT"


def test_unique_columns():
    assert models.User.__table__.c.email.unique
    assert models.Label.__table__.c.name.unique
    assert not models.Project.__table__.c.name.unique


class FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_get_db_yields_session_and_closes_it(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake)

    gen = database.get_db()
    assert next(gen) is fake
    assert not fake.closed

    gen.close()
    assert fake.closed


def test_get_db_closes_session_when_request_fails(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake)

    gen = database.get_db()
    next(gen)
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    assert fake.closed


def test_engine_checks_connections_before_use():
    assert database.engine.pool._pre_ping is True


def test_session_does_not_autoflush():
    assert database.SessionLocal.kw["autoflush"] is False
