from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers._common import raise_conflict

router = APIRouter()


def _get_or_404(db: Session, comment_id: int) -> models.Comment:
    comment = db.get(models.Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    return comment


@router.get("", response_model=list[schemas.CommentRead])
def list_comments(
    task_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(models.Comment)
    if task_id is not None:
        stmt = stmt.where(models.Comment.task_id == task_id)
    return db.scalars(stmt.order_by(models.Comment.id)).all()


@router.get("/{comment_id}", response_model=schemas.CommentRead)
def get_comment(comment_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, comment_id)


@router.post("", response_model=schemas.CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(payload: schemas.CommentCreate, db: Session = Depends(get_db)):
    comment = models.Comment(**payload.model_dump())
    db.add(comment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise_conflict(exc)
    db.refresh(comment)
    return comment


@router.patch("/{comment_id}", response_model=schemas.CommentRead)
def update_comment(
    comment_id: int, payload: schemas.CommentUpdate, db: Session = Depends(get_db)
):
    comment = _get_or_404(db, comment_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(comment, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise_conflict(exc)
    db.refresh(comment)
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, db: Session = Depends(get_db)) -> None:
    comment = _get_or_404(db, comment_id)
    db.delete(comment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise_conflict(exc)