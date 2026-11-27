import logging

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import setup_logging
from app.routers import comments, labels, projects, tasks, users

setup_logging()
logger = logging.getLogger("app")

app = FastAPI(title="TaskFlow API", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    logger.info(
        "TaskFlow API запускается (log_level=%s)",
        logging.getLevelName(logger.getEffectiveLevel()),
    )


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    logger.debug("Health-check: проверяем БД")
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health-check: БД недоступна")
        raise
    logger.info("Health-check: БД в норме")
    return {"status": "ok", "database": "up"}


@app.get("/_log-demo", tags=["debug"])
def log_demo() -> dict[str, str]:
    logger.debug("Это DEBUG — детали для отладки")
    logger.info("Это INFO — обычное событие")
    logger.warning("Это WARNING — что-то подозрительное")
    logger.error("Это ERROR — ошибка, но приложение живо")
    logger.critical("Это CRITICAL — критический сбой")
    return {"status": "logged all levels"}


app.include_router(users.router, prefix="/v1/users", tags=["users"])
app.include_router(projects.router, prefix="/v1/projects", tags=["projects"])
app.include_router(labels.router, prefix="/v1/labels", tags=["labels"])
app.include_router(tasks.router, prefix="/v1/tasks", tags=["tasks"])
app.include_router(comments.router, prefix="/v1/comments", tags=["comments"])
