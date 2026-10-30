import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app


def test_health_checks_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_health_fails_when_database_is_down():
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("select 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        broken = TestClient(app, raise_server_exceptions=False)
        assert broken.get("/health").status_code == 500
    finally:
        app.dependency_overrides.clear()


def test_openapi_lists_all_resources(client):
    paths = client.get("/openapi.json").json()["paths"]
    for resource in ("users", "projects", "labels", "tasks", "comments"):
        assert f"/v1/{resource}" in paths
        assert f"/v1/{resource}/{{{resource[:-1]}_id}}" in paths
    assert "/health" in paths


def test_api_title_and_version(client):
    info = client.get("/openapi.json").json()["info"]
    assert info["title"] == "TaskFlow API"
    assert info["version"] == "1.0.0"


def test_docs_page_is_served(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


@pytest.mark.parametrize("path", ["/users", "/v2/users", "/v1/unknown"])
def test_unknown_paths_are_404(client, path):
    assert client.get(path).status_code == 404


def test_wrong_method_is_405(client):
    assert client.put("/v1/users/1", json={}).status_code == 405
