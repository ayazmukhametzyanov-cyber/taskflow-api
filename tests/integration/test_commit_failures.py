"""Любой сбой commit() в изменяющих запросах превращается в 409, а не в 500."""
import pytest

CONFLICT = {"detail": "Дубликат значения или неверная ссылка"}

CREATE = {
    "users": {"email": "new@example.com", "display_name": "Новый"},
    "projects": {"name": "Новый"},
    "labels": {"name": "new"},
    "tasks": {"project_id": 1, "title": "Новая"},
    "comments": {"task_id": 1, "author_id": 1, "body": "текст"},
}
PATCH = {
    "users": {"display_name": "Другое"},
    "projects": {"name": "Другое"},
    "labels": {"name": "other"},
    "tasks": {"title": "Другая"},
    "comments": {"body": "другое"},
}


@pytest.fixture
def seeded(api):
    """По одной записи каждого вида; id у всех равен 1."""
    api.comment()
    api.label()
    return CREATE.keys()


@pytest.mark.parametrize("resource", CREATE)
def test_create_conflict(client, seeded, commit_fails, resource):
    rollbacks = commit_fails()
    response = client.post(f"/v1/{resource}", json=CREATE[resource])
    assert response.status_code == 409
    assert response.json() == CONFLICT
    assert rollbacks == [1]


@pytest.mark.parametrize("resource", PATCH)
def test_patch_conflict(client, seeded, commit_fails, resource):
    before = client.get(f"/v1/{resource}/1").json()
    rollbacks = commit_fails()
    response = client.patch(f"/v1/{resource}/1", json=PATCH[resource])
    assert response.status_code == 409
    assert response.json() == CONFLICT
    assert rollbacks == [1]
    client.app.dependency_overrides.clear()
    assert client.get(f"/v1/{resource}/1").json() == before


@pytest.mark.parametrize("resource", PATCH)
def test_delete_conflict(client, seeded, commit_fails, resource):
    rollbacks = commit_fails()
    response = client.delete(f"/v1/{resource}/1")
    assert response.status_code == 409
    assert response.json() == CONFLICT
    assert rollbacks == [1]
    client.app.dependency_overrides.clear()
    assert client.get(f"/v1/{resource}/1").status_code == 200
