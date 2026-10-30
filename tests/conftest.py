from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# helpers подменяет DATABASE_URL, поэтому импортируется раньше app
from helpers import (
    TABLES,
    TEST_DATABASE_URL,
    alembic_config,
    ensure_database,
    recreate_schema,
)
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.database import SessionLocal, get_db
from app.main import app


def pytest_collection_modifyitems(items):
    for item in items:
        folder = Path(item.fspath).parent.name
        if folder in {"unit", "db", "integration", "e2e"}:
            item.add_marker(getattr(pytest.mark, folder))


@pytest.fixture(scope="session")
def database():
    """Тестовая база с чистой схемой, накатанной миграциями."""
    ensure_database(TEST_DATABASE_URL)
    recreate_schema(TEST_DATABASE_URL)
    command.upgrade(alembic_config(), "head")
    return TEST_DATABASE_URL


@pytest.fixture
def clean_db(database):
    engine = create_engine(database)
    with engine.begin() as conn:
        conn.execute(text(f"truncate {TABLES} restart identity cascade"))
    engine.dispose()


@pytest.fixture
def session(clean_db):
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client(clean_db):
    return TestClient(app)


@pytest.fixture
def commit_fails():
    """Включает сессию, у которой commit() падает с IntegrityError.

    Возвращает список, в который попадает каждый вызов rollback().
    """

    def enable():
        rollbacks = []

        def override():
            with SessionLocal() as db:
                real_rollback = db.rollback

                def boom():
                    raise IntegrityError("commit", {}, Exception("boom"))

                def rollback():
                    rollbacks.append(1)
                    real_rollback()

                db.commit = boom
                db.rollback = rollback
                yield db

        app.dependency_overrides[get_db] = override
        return rollbacks

    yield enable
    app.dependency_overrides.clear()


@pytest.fixture
def api(client):
    """Короткие помощники, чтобы тесты не повторяли тела запросов."""

    class Api:
        def user(self, **fields):
            body = {"email": "ivan@example.com", "display_name": "Иван"} | fields
            response = client.post("/v1/users", json=body)
            assert response.status_code == 201, response.text
            return response.json()

        def project(self, **fields):
            body = {"name": "Онбординг"} | fields
            response = client.post("/v1/projects", json=body)
            assert response.status_code == 201, response.text
            return response.json()

        def label(self, **fields):
            body = {"name": "bug"} | fields
            response = client.post("/v1/labels", json=body)
            assert response.status_code == 201, response.text
            return response.json()

        def task(self, project_id=None, **fields):
            if project_id is None:
                project_id = self.project()["id"]
            body = {"project_id": project_id, "title": "Поднять окружение"} | fields
            response = client.post("/v1/tasks", json=body)
            assert response.status_code == 201, response.text
            return response.json()

        def comment(self, task_id=None, author_id=None, **fields):
            if task_id is None:
                task_id = self.task()["id"]
            if author_id is None:
                author_id = self.user()["id"]
            body = {"task_id": task_id, "author_id": author_id, "body": "готово"} | fields
            response = client.post("/v1/comments", json=body)
            assert response.status_code == 201, response.text
            return response.json()

    return Api()
