CONFLICT = {"detail": "Дубликат значения или неверная ссылка"}


def test_list_is_empty_at_start(client):
    response = client.get("/v1/users")
    assert response.status_code == 200
    assert response.json() == []


def test_create_returns_201_with_defaults(client):
    response = client.post(
        "/v1/users", json={"email": "ivan@example.com", "display_name": "Иван"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["role"] == "operator"
    assert body["created_at"]


def test_create_with_admin_role(client):
    body = client.post(
        "/v1/users",
        json={"email": "a@example.com", "display_name": "A", "role": "admin"},
    ).json()
    assert body["role"] == "admin"


def test_unknown_fields_are_ignored(client):
    body = client.post(
        "/v1/users",
        json={"email": "a@example.com", "display_name": "A", "id": 77, "created_at": "2000-01-01"},
    ).json()
    assert body["id"] == 1
    assert not body["created_at"].startswith("2000")


def test_list_is_ordered_by_id(client, api):
    api.user(email="b@example.com")
    api.user(email="a@example.com")
    emails = [u["email"] for u in client.get("/v1/users").json()]
    assert emails == ["b@example.com", "a@example.com"]


def test_get_returns_created_user(client, api):
    user = api.user()
    assert client.get(f"/v1/users/{user['id']}").json() == user


def test_get_missing_is_404(client):
    response = client.get("/v1/users/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Пользователь не найден"}


def test_patch_changes_only_given_fields(client, api):
    user = api.user()
    response = client.patch(f"/v1/users/{user['id']}", json={"display_name": "Пётр"})
    assert response.status_code == 200
    assert response.json() == user | {"display_name": "Пётр"}


def test_patch_role(client, api):
    user = api.user()
    response = client.patch(f"/v1/users/{user['id']}", json={"role": "admin"})
    assert response.json()["role"] == "admin"


def test_patch_missing_is_404(client):
    assert client.patch("/v1/users/999", json={"role": "admin"}).status_code == 404


def test_delete_removes_user(client, api):
    user = api.user()
    response = client.delete(f"/v1/users/{user['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/v1/users/{user['id']}").status_code == 404


def test_delete_missing_is_404(client):
    assert client.delete("/v1/users/999").status_code == 404


def test_duplicate_email_is_409(client, api):
    api.user()
    response = client.post(
        "/v1/users", json={"email": "ivan@example.com", "display_name": "Другой"}
    )
    assert response.status_code == 409
    assert response.json() == CONFLICT


def test_patch_to_taken_email_is_409(client, api):
    api.user(email="a@example.com")
    second = api.user(email="b@example.com")
    response = client.patch(f"/v1/users/{second['id']}", json={"email": "a@example.com"})
    assert response.status_code == 409
    assert response.json() == CONFLICT


def test_patch_required_field_to_null_is_409(client, api):
    user = api.user()
    for field in ("email", "display_name", "role"):
        response = client.patch(f"/v1/users/{user['id']}", json={field: None})
        assert response.status_code == 409, field


def test_failed_patch_leaves_user_unchanged(client, api):
    user = api.user()
    client.patch(f"/v1/users/{user['id']}", json={"email": None})
    assert client.get(f"/v1/users/{user['id']}").json() == user


def test_user_with_comments_cannot_be_deleted(client, api):
    comment = api.comment()
    response = client.delete(f"/v1/users/{comment['author_id']}")
    assert response.status_code == 409
    assert response.json() == CONFLICT
    assert client.get(f"/v1/users/{comment['author_id']}").status_code == 200
    assert client.get(f"/v1/comments/{comment['id']}").json() == comment


def test_invalid_input_is_422(client):
    for body in (
        {"email": "a@example.com", "display_name": ""},
        {"email": "a@example.com", "display_name": "A", "role": "root"},
        {"email": "x" * 256, "display_name": "A"},
        {"display_name": "A"},
        {"email": "a@example.com"},
    ):
        assert client.post("/v1/users", json=body).status_code == 422, body


def test_patch_invalid_input_is_422(client, api):
    user = api.user()
    for body in ({"role": "root"}, {"display_name": ""}):
        assert client.patch(f"/v1/users/{user['id']}", json=body).status_code == 422


def test_non_numeric_id_is_422(client):
    assert client.get("/v1/users/abc").status_code == 422
