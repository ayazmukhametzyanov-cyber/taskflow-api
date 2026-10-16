from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def raise_conflict(exc: IntegrityError) -> None:
    raise HTTPException(
        status_code=409,
        detail="Дубликат значения или неверная ссылка",
    ) from exc