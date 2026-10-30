"""Сценарии «как у клиента»: настоящий сервер, настоящая база, только HTTP."""
import httpx


def post(http, path, **body):
    response = http.post(path, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_server_is_up_and_healthy(http):
    response = http.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}
    assert response.headers["content-type"] == "application/json"


def test_task_lifecycle_from_creation_to_removal(http):
    admin = post(http, "/v1/users", email="lead@example.com", display_name="Лид", role="admin")
    dev = post(http, "/v1/users", email="dev@example.com", display_name="Разработчик")
    project = post(http, "/v1/projects", name="Релиз", description="октябрьский релиз")
    label = post(http, "/v1/labels", name="bug", color="#ff0000")
    task = post(
        http,
        "/v1/tasks",
        project_id=project["id"],
        assignee_id=dev["id"],
        label_id=label["id"],
        title="Починить вход",
        priority="high",
    )
    assert task["status"] == "open"

    comment = post(
        http, "/v1/comments", task_id=task["id"], author_id=admin["id"], body="срочно"
    )
    assert comment["body"] == "срочно"

    started = http.patch(f"/v1/tasks/{task['id']}", json={"status": "in_progress"})
    assert started.json()["status"] == "in_progress"
    done = http.patch(f"/v1/tasks/{task['id']}", json={"status": "done"})
    assert done.json()["status"] == "done"

    assert [t["id"] for t in http.get("/v1/tasks", params={"status": "done"}).json()] == [
        task["id"]
    ]
    assert http.get("/v1/tasks", params={"status": "open"}).json() == []
    assert len(http.get("/v1/comments", params={"task_id": task["id"]}).json()) == 1

    assert http.delete(f"/v1/tasks/{task['id']}").status_code == 204
    assert http.get(f"/v1/tasks/{task['id']}").status_code == 404
    assert http.get("/v1/comments").json() == []


def test_deleting_project_removes_its_work_but_not_people(http):
    user = post(http, "/v1/users", email="a@example.com", display_name="A")
    project = post(http, "/v1/projects", name="Временный")
    task = post(http, "/v1/tasks", project_id=project["id"], title="T", assignee_id=user["id"])
    post(http, "/v1/comments", task_id=task["id"], author_id=user["id"], body="x")

    assert http.delete(f"/v1/projects/{project['id']}").status_code == 204

    assert http.get("/v1/tasks").json() == []
    assert http.get("/v1/comments").json() == []
    assert http.get(f"/v1/users/{user['id']}").status_code == 200


def test_author_cannot_be_removed_until_comments_are_gone(http):
    user = post(http, "/v1/users", email="a@example.com", display_name="A")
    project = post(http, "/v1/projects", name="P")
    task = post(http, "/v1/tasks", project_id=project["id"], title="T")
    comment = post(http, "/v1/comments", task_id=task["id"], author_id=user["id"], body="x")

    assert http.delete(f"/v1/users/{user['id']}").status_code == 409

    http.delete(f"/v1/comments/{comment['id']}")
    assert http.delete(f"/v1/users/{user['id']}").status_code == 204


def test_removing_assignee_and_label_keeps_the_task(http):
    user = post(http, "/v1/users", email="a@example.com", display_name="A")
    label = post(http, "/v1/labels", name="idea")
    project = post(http, "/v1/projects", name="P")
    task = post(
        http,
        "/v1/tasks",
        project_id=project["id"],
        title="T",
        assignee_id=user["id"],
        label_id=label["id"],
    )

    http.delete(f"/v1/users/{user['id']}")
    http.delete(f"/v1/labels/{label['id']}")

    after = http.get(f"/v1/tasks/{task['id']}").json()
    assert after["assignee_id"] is None and after["label_id"] is None
    assert after["title"] == "T"


def test_errors_look_the_same_over_the_wire(http):
    post(http, "/v1/labels", name="bug")

    duplicate = http.post("/v1/labels", json={"name": "bug"})
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Дубликат значения или неверная ссылка"}

    invalid = http.post("/v1/labels", json={"name": "x", "color": "red"})
    assert invalid.status_code == 422

    missing = http.get("/v1/tasks/12345")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Задача не найдена"}

    dangling = http.post("/v1/tasks", json={"project_id": 12345, "title": "T"})
    assert dangling.status_code == 409


def test_data_is_shared_between_connections(http, server):
    project = post(http, "/v1/projects", name="Общий")
    with httpx.Client(base_url=server, timeout=10, trust_env=False) as other:
        assert other.get(f"/v1/projects/{project['id']}").json() == project


def test_interactive_docs_are_available(http):
    assert http.get("/docs").status_code == 200
    schema = http.get("/openapi.json").json()
    assert schema["info"]["title"] == "TaskFlow API"
    assert "/v1/tasks" in schema["paths"]
