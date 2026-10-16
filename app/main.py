from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import comments, labels, projects, tasks, users

app = FastAPI(title="TaskFlow API", version="1.0.0")


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "up"}


app.include_router(users.router, prefix="/v1/users", tags=["users"])
app.include_router(projects.router, prefix="/v1/projects", tags=["projects"])
app.include_router(labels.router, prefix="/v1/labels", tags=["labels"])
app.include_router(tasks.router, prefix="/v1/tasks", tags=["tasks"])
app.include_router(comments.router, prefix="/v1/comments", tags=["comments"])