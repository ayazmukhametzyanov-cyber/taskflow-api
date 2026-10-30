def test_create_with_defaults(client, api):
    project = api.project()
    response = client.post(
        "/v1/tasks", json={"project_id": project["id"], "title": "Поднять окружение"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["priority"] == "medium"
    assert body["assignee_id"] is None and body["label_id"] is None
    assert body["description"] is None
    assert body["created_at"] and body["updated_at"]


def test_create_with_all_fields(api):
    project = api.project()
    user = api.user()
    label = api.label()
    task = api.task(
        project_id=project["id"],
        assignee_id=user["id"],
        label_id=label["id"],
        description="подробности",
        status="in_progress",
        priority="high",
    )
    assert task["assignee_id"] == user["id"]
    assert task["label_id"] == label["id"]
    assert (task["status"], task["priority"]) == ("in_progress", "high")
    assert task["description"] == "подробности"


def test_get_and_missing(client, api):
    task = api.task()
    assert client.get(f"/v1/tasks/{task['id']}").json() == task
    response = client.get("/v1/tasks/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Задача не найдена"}


def test_list_filters(client, api):
    first, second = api.project(name="A"), api.project(name="B")
    a_open = api.task(project_id=first["id"], title="a1")
    a_done = api.task(project_id=first["id"], title="a2", status="done")
    b_open = api.task(project_id=second["id"], title="b1")

    def ids(query):
        return [t["id"] for t in client.get(f"/v1/tasks{query}").json()]

    assert ids("") == [a_open["id"], a_done["id"], b_open["id"]]
    assert ids(f"?project_id={first['id']}") == [a_open["id"], a_done["id"]]
    assert ids("?status=open") == [a_open["id"], b_open["id"]]
    assert ids(f"?project_id={first['id']}&status=done") == [a_done["id"]]
    assert ids("?project_id=999") == []


def test_list_rejects_unknown_status(client):
    assert client.get("/v1/tasks?status=closed").status_code == 422


def test_patch_status(client, api):
    task = api.task()
    response = client.patch(f"/v1/tasks/{task['id']}", json={"status": "done"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["title"] == task["title"]
    assert body["updated_at"] >= task["updated_at"]


def test_patch_cannot_move_task_to_another_project(client, api):
    task = api.task()
    other = api.project(name="Другой")
    response = client.patch(f"/v1/tasks/{task['id']}", json={"project_id": other["id"]})
    assert response.status_code == 200
    assert response.json()["project_id"] == task["project_id"]


def test_patch_can_assign_and_clear_assignee(client, api):
    user = api.user()
    task = api.task()
    assigned = client.patch(f"/v1/tasks/{task['id']}", json={"assignee_id": user["id"]})
    assert assigned.json()["assignee_id"] == user["id"]
    cleared = client.patch(f"/v1/tasks/{task['id']}", json={"assignee_id": None})
    assert cleared.json()["assignee_id"] is None


def test_patch_missing_is_404(client):
    assert client.patch("/v1/tasks/999", json={"status": "done"}).status_code == 404


def test_patch_required_field_to_null_is_409(client, api):
    task = api.task()
    for field in ("title", "status", "priority"):
        response = client.patch(f"/v1/tasks/{task['id']}", json={field: None})
        assert response.status_code == 409, field
    assert client.get(f"/v1/tasks/{task['id']}").json() == task


def test_patch_to_missing_assignee_or_label_is_409(client, api):
    task = api.task()
    for body in ({"assignee_id": 999}, {"label_id": 999}):
        assert client.patch(f"/v1/tasks/{task['id']}", json=body).status_code == 409, body


def test_create_in_missing_project_is_409(client):
    response = client.post("/v1/tasks", json={"project_id": 999, "title": "T"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Дубликат значения или неверная ссылка"}


def test_create_with_missing_assignee_or_label_is_409(client, api):
    project = api.project()
    for extra in ({"assignee_id": 999}, {"label_id": 999}):
        response = client.post(
            "/v1/tasks", json={"project_id": project["id"], "title": "T"} | extra
        )
        assert response.status_code == 409, extra


def test_invalid_input_is_422(client, api):
    project = api.project()
    base = {"project_id": project["id"], "title": "T"}
    for bad in (
        {"title": ""},
        {"title": "x" * 201},
        {"status": "closed"},
        {"priority": "urgent"},
        {"project_id": "abc"},
    ):
        assert client.post("/v1/tasks", json=base | bad).status_code == 422, bad
    assert client.post("/v1/tasks", json={"title": "T"}).status_code == 422


def test_delete(client, api):
    task = api.task()
    assert client.delete(f"/v1/tasks/{task['id']}").status_code == 204
    assert client.get(f"/v1/tasks/{task['id']}").status_code == 404


def test_delete_missing_is_404(client):
    assert client.delete("/v1/tasks/999").status_code == 404


def test_delete_removes_comments_but_keeps_author(client, api):
    comment = api.comment()
    client.delete(f"/v1/tasks/{comment['task_id']}")
    assert client.get(f"/v1/comments/{comment['id']}").status_code == 404
    assert client.get(f"/v1/users/{comment['author_id']}").status_code == 200


def test_delete_assignee_clears_field(client, api):
    user = api.user()
    task = api.task(assignee_id=user["id"])
    assert client.delete(f"/v1/users/{user['id']}").status_code == 204
    assert client.get(f"/v1/tasks/{task['id']}").json()["assignee_id"] is None
