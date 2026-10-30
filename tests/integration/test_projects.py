def test_create_and_read_back(client):
    created = client.post(
        "/v1/projects", json={"name": "Онбординг", "description": "первая неделя"}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Онбординг"
    assert body["description"] == "первая неделя"
    assert client.get(f"/v1/projects/{body['id']}").json() == body


def test_description_is_optional(api):
    assert api.project()["description"] is None


def test_same_name_is_allowed_twice(api):
    assert api.project(name="Один")["id"] != api.project(name="Один")["id"]


def test_list_returns_all_in_id_order(client, api):
    api.project(name="Б")
    api.project(name="А")
    assert [p["name"] for p in client.get("/v1/projects").json()] == ["Б", "А"]


def test_get_missing_is_404(client):
    response = client.get("/v1/projects/5")
    assert response.status_code == 404
    assert response.json() == {"detail": "Проект не найден"}


def test_patch_name(client, api):
    project = api.project(description="текст")
    response = client.patch(f"/v1/projects/{project['id']}", json={"name": "Новое"})
    assert response.status_code == 200
    assert response.json() == project | {"name": "Новое"}


def test_patch_can_clear_description(client, api):
    project = api.project(description="текст")
    response = client.patch(f"/v1/projects/{project['id']}", json={"description": None})
    assert response.json()["description"] is None


def test_patch_empty_body_changes_nothing(client, api):
    project = api.project()
    assert client.patch(f"/v1/projects/{project['id']}", json={}).json() == project


def test_patch_name_to_null_is_409(client, api):
    project = api.project()
    response = client.patch(f"/v1/projects/{project['id']}", json={"name": None})
    assert response.status_code == 409
    assert client.get(f"/v1/projects/{project['id']}").json() == project


def test_patch_missing_is_404(client):
    assert client.patch("/v1/projects/5", json={"name": "x"}).status_code == 404


def test_delete(client, api):
    project = api.project()
    assert client.delete(f"/v1/projects/{project['id']}").status_code == 204
    assert client.get("/v1/projects").json() == []


def test_delete_missing_is_404(client):
    assert client.delete("/v1/projects/5").status_code == 404


def test_delete_cascades_to_tasks_and_comments(client, api):
    task = api.task()
    comment = api.comment(task_id=task["id"])

    assert client.delete(f"/v1/projects/{task['project_id']}").status_code == 204

    assert client.get(f"/v1/tasks/{task['id']}").status_code == 404
    assert client.get(f"/v1/comments/{comment['id']}").status_code == 404
    assert client.get(f"/v1/users/{comment['author_id']}").status_code == 200


def test_invalid_input_is_422(client):
    for body in ({}, {"name": ""}, {"name": "x" * 201}):
        assert client.post("/v1/projects", json=body).status_code == 422, body
