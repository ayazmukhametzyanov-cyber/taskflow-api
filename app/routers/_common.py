import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("app.conflicts")


def raise_conflict(exc: IntegrityError) -> None:
    logger.warning("Конфликт при записи в БД: %s", exc)
    raise HTTPException(
        status_code=409,
        detail="Дубликат значения или неверная ссылка",
    ) from exc
