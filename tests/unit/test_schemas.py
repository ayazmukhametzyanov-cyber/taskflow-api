import pytest
from pydantic import ValidationError

from app import schemas


def test_user_create_defaults_role_to_operator():
    user = schemas.UserCreate(email="a@example.com", display_name="A")
    assert user.role == "operator"


def test_user_create_rejects_unknown_role():
    with pytest.raises(ValidationError):
        schemas.UserCreate(email="a@example.com", display_name="A", role="root")


@pytest.mark.parametrize("name, ok", [("", False), ("x", True), ("x" * 255, True), ("x" * 256, False)])
def test_user_display_name_length(name, ok):
    if ok:
        assert schemas.UserCreate(email="a@example.com", display_name=name)
    else:
        with pytest.raises(ValidationError):
            schemas.UserCreate(email="a@example.com", display_name=name)


def test_user_email_length_limit():
    assert schemas.UserCreate(email="x" * 255, display_name="A")
    with pytest.raises(ValidationError):
        schemas.UserCreate(email="x" * 256, display_name="A")
    with pytest.raises(ValidationError):
        schemas.UserUpdate(email="x" * 256)


def test_user_update_is_all_optional():
    assert schemas.UserUpdate().model_dump(exclude_unset=True) == {}
    assert schemas.UserUpdate(role="admin").model_dump(exclude_unset=True) == {"role": "admin"}
    with pytest.raises(ValidationError):
        schemas.UserUpdate(display_name="")


@pytest.mark.parametrize("name, ok", [("", False), ("x", True), ("x" * 200, True), ("x" * 201, False)])
def test_project_name_length(name, ok):
    if ok:
        assert schemas.ProjectCreate(name=name).name == name
        assert schemas.ProjectUpdate(name=name).name == name
    else:
        with pytest.raises(ValidationError):
            schemas.ProjectCreate(name=name)
        with pytest.raises(ValidationError):
            schemas.ProjectUpdate(name=name)


def test_project_update_distinguishes_missing_and_null_description():
    assert schemas.ProjectUpdate().model_dump(exclude_unset=True) == {}
    assert schemas.ProjectUpdate(description=None).model_dump(exclude_unset=True) == {
        "description": None
    }


@pytest.mark.parametrize("color", ["#000000", "#abcdef", "#ABCDEF", "#6b7280"])
def test_label_color_accepts_hex(color):
    assert schemas.LabelCreate(name="x", color=color).color == color
    assert schemas.LabelUpdate(color=color).color == color


@pytest.mark.parametrize("color", ["red", "#fff", "#12345g", "123456", "#1234567", ""])
def test_label_color_rejects_non_hex(color):
    with pytest.raises(ValidationError):
        schemas.LabelCreate(name="x", color=color)
    with pytest.raises(ValidationError):
        schemas.LabelUpdate(color=color)


def test_label_defaults_and_name_length():
    assert schemas.LabelCreate(name="x").color == "#6b7280"
    assert schemas.LabelCreate(name="x" * 64)
    with pytest.raises(ValidationError):
        schemas.LabelCreate(name="x" * 65)
    with pytest.raises(ValidationError):
        schemas.LabelUpdate(name="")


def test_task_create_defaults():
    task = schemas.TaskCreate(project_id=1, title="T")
    assert (task.status, task.priority) == ("open", "medium")
    assert task.assignee_id is None and task.label_id is None


@pytest.mark.parametrize("field, value", [("status", "closed"), ("priority", "urgent")])
def test_task_rejects_unknown_enum_values(field, value):
    with pytest.raises(ValidationError):
        schemas.TaskCreate(project_id=1, title="T", **{field: value})
    with pytest.raises(ValidationError):
        schemas.TaskUpdate(**{field: value})


@pytest.mark.parametrize("title, ok", [("", False), ("x" * 200, True), ("x" * 201, False)])
def test_task_title_length(title, ok):
    if ok:
        assert schemas.TaskCreate(project_id=1, title=title)
    else:
        with pytest.raises(ValidationError):
            schemas.TaskCreate(project_id=1, title=title)
        with pytest.raises(ValidationError):
            schemas.TaskUpdate(title=title)


def test_task_update_has_no_project_field():
    assert "project_id" not in schemas.TaskUpdate.model_fields


def test_comment_body_must_not_be_empty():
    assert schemas.CommentCreate(task_id=1, author_id=1, body="x").body == "x"
    with pytest.raises(ValidationError):
        schemas.CommentCreate(task_id=1, author_id=1, body="")
    with pytest.raises(ValidationError):
        schemas.CommentUpdate(body="")


def test_comment_update_body_is_optional():
    assert schemas.CommentUpdate().model_dump(exclude_unset=True) == {}


def test_output_schemas_read_from_attributes():
    class Row:
        id = 3
        name = "bug"
        color = "#6b7280"

    label = schemas.LabelRead.model_validate(Row())
    assert label.model_dump() == {"id": 3, "name": "bug", "color": "#6b7280"}
