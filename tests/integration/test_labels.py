CONFLICT = {"detail": "Дубликат значения или неверная ссылка"}


def test_create_with_default_color(client):
    response = client.post("/v1/labels", json={"name": "bug"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "bug", "color": "#6b7280"}


def test_create_with_color(api):
    assert api.label(color="#ff0000")["color"] == "#ff0000"


def test_list_and_get(client, api):
    first = api.label(name="bug")
    second = api.label(name="idea")
    assert client.get("/v1/labels").json() == [first, second]
    assert client.get(f"/v1/labels/{second['id']}").json() == second


def test_get_missing_is_404(client):
    response = client.get("/v1/labels/3")
    assert response.status_code == 404
    assert response.json() == {"detail": "Метка не найдена"}


def test_patch_color_and_name(client, api):
    label = api.label()
    response = client.patch(
        f"/v1/labels/{label['id']}", json={"name": "defect", "color": "#00ff00"}
    )
    assert response.json() == {"id": label["id"], "name": "defect", "color": "#00ff00"}


def test_patch_missing_is_404(client):
    assert client.patch("/v1/labels/3", json={"name": "x"}).status_code == 404


def test_duplicate_name_is_409(client, api):
    api.label(name="bug")
    response = client.post("/v1/labels", json={"name": "bug"})
    assert response.status_code == 409
    assert response.json() == CONFLICT


def test_patch_to_taken_name_is_409(client, api):
    api.label(name="bug")
    other = api.label(name="idea")
    response = client.patch(f"/v1/labels/{other['id']}", json={"name": "bug"})
    assert response.status_code == 409


def test_patch_required_field_to_null_is_409(client, api):
    label = api.label()
    for field in ("name", "color"):
        response = client.patch(f"/v1/labels/{label['id']}", json={field: None})
        assert response.status_code == 409, field


def test_bad_color_is_422(client, api):
    label = api.label()
    for color in ("red", "#12", "#gggggg", "ff0000"):
        assert client.post("/v1/labels", json={"name": color, "color": color}).status_code == 422
        assert client.patch(f"/v1/labels/{label['id']}", json={"color": color}).status_code == 422


def test_delete(client, api):
    label = api.label()
    assert client.delete(f"/v1/labels/{label['id']}").status_code == 204
    assert client.get(f"/v1/labels/{label['id']}").status_code == 404


def test_delete_missing_is_404(client):
    assert client.delete("/v1/labels/3").status_code == 404


def test_delete_clears_label_on_tasks(client, api):
    label = api.label()
    task = api.task(label_id=label["id"])

    client.delete(f"/v1/labels/{label['id']}")

    assert client.get(f"/v1/tasks/{task['id']}").json()["label_id"] is None
