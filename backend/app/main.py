from fastapi import FastAPI

from backend.app.api.athletes import router as athletes_router
from backend.app.api.events import router as events_router
from backend.app.api.imports import router as imports_router
from backend.app.api.races import router as races_router

app = FastAPI(title="Skjold på tvers")

app.include_router(races_router)
app.include_router(events_router)
app.include_router(imports_router)
app.include_router(athletes_router)


@app.get("/")
def read_root():
    return {
        "app": "Skjold på tvers",
        "status": "ok",
        "database": "managed by alembic",
    }
