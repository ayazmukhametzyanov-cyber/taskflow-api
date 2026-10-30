import time

import pytest
from psycopg2.errors import (
    ForeignKeyViolation,
    NotNullViolation,
    RestrictViolation,
    UniqueViolation,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Comment, Label, Project, Task, User


def violation(session, *objects):
    """Сохраняет объекты и возвращает исходную ошибку psycopg2."""
    session.add_all(objects)
    with pytest.raises(IntegrityError) as error:
        session.commit()
    session.rollback()
    return error.value.orig


def make_user(session, email="ivan@example.com"):
    user = User(email=email, display_name="Иван")
    session.add(user)
    session.commit()
    return user


def make_task(session, **fields):
    project = Project(name="P")
    session.add(project)
    session.flush()
    task = Task(project_id=project.id, title="T", **fields)
    session.add(task)
    session.commit()
    return task


def test_defaults_are_filled_by_database(session):
    user = make_user(session)
    label = Label(name="bug")
    task = make_task(session)
    session.add(label)
    session.commit()
    session.refresh(task)

    assert user.role == "operator"
    assert user.created_at is not None
    assert label.color == "#6b7280"
    assert (task.status, task.priority) == ("open", "medium")
    assert task.created_at is not None and task.updated_at is not None


def test_user_email_is_unique(session):
    make_user(session)
    error = violation(session, User(email="ivan@example.com", display_name="Другой"))
    assert isinstance(error, UniqueViolation)
    assert error.diag.constraint_name == "users_email_key"


def test_user_email_is_required(session):
    assert isinstance(violation(session, User(display_name="A")), NotNullViolation)


def test_user_display_name_is_required(session):
    assert isinstance(violation(session, User(email="a@example.com")), NotNullViolation)


def test_label_name_is_unique(session):
    session.add(Label(name="bug"))
    session.commit()
    error = violation(session, Label(name="bug"))
    assert isinstance(error, UniqueViolation)
    assert error.diag.constraint_name == "labels_name_key"


def test_project_name_is_required(session):
    assert isinstance(violation(session, Project()), NotNullViolation)


def test_task_requires_title_and_project(session):
    project = Project(name="P")
    session.add(project)
    session.commit()
    assert isinstance(violation(session, Task(project_id=project.id)), NotNullViolation)
    assert isinstance(violation(session, Task(title="T")), NotNullViolation)


def test_task_requires_existing_project(session):
    error = violation(session, Task(project_id=999, title="T"))
    assert isinstance(error, ForeignKeyViolation)
    assert error.diag.constraint_name == "tasks_project_id_fkey"


def test_task_requires_existing_assignee_and_label(session):
    project = Project(name="P")
    session.add(project)
    session.commit()
    assert isinstance(
        violation(session, Task(project_id=project.id, title="T", assignee_id=999)),
        ForeignKeyViolation,
    )
    assert isinstance(
        violation(session, Task(project_id=project.id, title="T", label_id=999)),
        ForeignKeyViolation,
    )


def test_comment_requires_body_task_and_author(session):
    user = make_user(session)
    task = make_task(session)
    assert isinstance(
        violation(session, Comment(task_id=task.id, author_id=user.id)), NotNullViolation
    )
    assert isinstance(
        violation(session, Comment(task_id=999, author_id=user.id, body="x")),
        ForeignKeyViolation,
    )
    assert isinstance(
        violation(session, Comment(task_id=task.id, author_id=999, body="x")),
        ForeignKeyViolation,
    )


def test_deleting_project_removes_tasks_and_comments(session):
    user = make_user(session)
    task = make_task(session)
    session.add(Comment(task_id=task.id, author_id=user.id, body="x"))
    session.commit()

    session.delete(session.get(Project, task.project_id))
    session.commit()

    assert session.scalars(select(Task)).all() == []
    assert session.scalars(select(Comment)).all() == []
    assert session.get(User, user.id) is not None


def test_deleting_task_removes_its_comments(session):
    user = make_user(session)
    task = make_task(session)
    session.add(Comment(task_id=task.id, author_id=user.id, body="x"))
    session.commit()

    session.delete(task)
    session.commit()

    assert session.scalars(select(Comment)).all() == []


def test_deleting_assignee_clears_task_field(session):
    user = make_user(session)
    task = make_task(session, assignee_id=user.id)

    session.delete(user)
    session.commit()
    session.refresh(task)

    assert task.assignee_id is None


def test_deleting_label_clears_task_field(session):
    label = Label(name="bug")
    session.add(label)
    session.commit()
    task = make_task(session, label_id=label.id)

    session.delete(label)
    session.commit()
    session.refresh(task)

    assert task.label_id is None


def test_user_with_comments_cannot_be_deleted(session):
    user = make_user(session)
    task = make_task(session)
    session.add(Comment(task_id=task.id, author_id=user.id, body="x"))
    session.commit()

    session.delete(user)
    with pytest.raises(IntegrityError) as error:
        session.commit()
    session.rollback()

    # PostgreSQL 16 сообщает об этом как о нарушении внешнего ключа, 18 — как restrict_violation
    assert isinstance(error.value.orig, ForeignKeyViolation | RestrictViolation | NotNullViolation)
    assert session.get(User, user.id) is not None


def test_task_updated_at_moves_on_update(session):
    task = make_task(session)
    created, first_update = task.created_at, task.updated_at
    time.sleep(0.05)

    task.title = "Новое название"
    session.commit()
    session.refresh(task)

    assert task.created_at == created
    assert task.updated_at > first_update


def test_ids_restart_after_clean_db(session):
    session.add(Label(name="a"))
    session.commit()
    assert session.scalars(select(Label.id)).one() == 1
