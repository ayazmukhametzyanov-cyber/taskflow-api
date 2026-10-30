def test_create_comment(client, api):
    task = api.task()
    user = api.user()
    response = client.post(
        "/v1/comments",
        json={"task_id": task["id"], "author_id": user["id"], "body": "привет"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["body"] == "привет"
    assert body["task_id"] == task["id"] and body["author_id"] == user["id"]
    assert body["created_at"]


def test_get_and_missing(client, api):
    comment = api.comment()
    assert client.get(f"/v1/comments/{comment['id']}").json() == comment
    response = client.get("/v1/comments/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Комментарий не найден"}


def test_list_filtered_by_task(client, api):
    user = api.user()
    first, second = api.task(title="a"), api.task(title="b")
    c1 = api.comment(task_id=first["id"], author_id=user["id"], body="1")
    c2 = api.comment(task_id=second["id"], author_id=user["id"], body="2")
    c3 = api.comment(task_id=first["id"], author_id=user["id"], body="3")

    everything = client.get("/v1/comments").json()
    assert [c["id"] for c in everything] == [c1["id"], c2["id"], c3["id"]]
    only_first = client.get(f"/v1/comments?task_id={first['id']}").json()
    assert [c["id"] for c in only_first] == [c1["id"], c3["id"]]
    assert client.get("/v1/comments?task_id=999").json() == []


def test_patch_body(client, api):
    comment = api.comment()
    response = client.patch(f"/v1/comments/{comment['id']}", json={"body": "новый"})
    assert response.status_code == 200
    assert response.json() == comment | {"body": "новый"}


def test_patch_without_body_changes_nothing(client, api):
    comment = api.comment()
    assert client.patch(f"/v1/comments/{comment['id']}", json={}).json() == comment


def test_patch_cannot_change_task_or_author(client, api):
    comment = api.comment()
    other = api.task(title="другая")
    response = client.patch(f"/v1/comments/{comment['id']}", json={"task_id": other["id"]})
    assert response.json()["task_id"] == comment["task_id"]


def test_patch_missing_is_404(client):
    assert client.patch("/v1/comments/999", json={"body": "x"}).status_code == 404


def test_patch_body_to_null_is_409(client, api):
    comment = api.comment()
    response = client.patch(f"/v1/comments/{comment['id']}", json={"body": None})
    assert response.status_code == 409
    assert client.get(f"/v1/comments/{comment['id']}").json() == comment


def test_empty_body_is_422(client, api):
    comment = api.comment()
    ids = {"task_id": comment["task_id"], "author_id": comment["author_id"]}
    assert client.post("/v1/comments", json=ids | {"body": ""}).status_code == 422
    assert client.patch(f"/v1/comments/{comment['id']}", json={"body": ""}).status_code == 422


def test_missing_task_or_author_is_409(client, api):
    task, user = api.task(), api.user()
    for ids in (
        {"task_id": 999, "author_id": user["id"]},
        {"task_id": task["id"], "author_id": 999},
    ):
        response = client.post("/v1/comments", json=ids | {"body": "x"})
        assert response.status_code == 409, ids
        assert response.json() == {"detail": "Дубликат значения или неверная ссылка"}


def test_delete(client, api):
    comment = api.comment()
    assert client.delete(f"/v1/comments/{comment['id']}").status_code == 204
    assert client.get(f"/v1/comments/{comment['id']}").status_code == 404


def test_delete_missing_is_404(client):
    assert client.delete("/v1/comments/999").status_code == 404


def test_author_becomes_deletable_after_comment_is_removed(client, api):
    comment = api.comment()
    assert client.delete(f"/v1/users/{comment['author_id']}").status_code == 409
    client.delete(f"/v1/comments/{comment['id']}")
    assert client.delete(f"/v1/users/{comment['author_id']}").status_code == 204
