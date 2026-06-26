from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api.admin import router as admin_router
from backend.app.api.athletes import router as athletes_router
from backend.app.api.controls import router as controls_router
from backend.app.api.events import router as events_router
from backend.app.api.imports import router as imports_router
from backend.app.api.races import router as races_router

app = FastAPI(title="Skjold på tvers")

app.mount("/static", StaticFiles(directory="backend/app/static"), name="static")

app.include_router(admin_router)
app.include_router(races_router)
app.include_router(events_router)
app.include_router(imports_router)
app.include_router(athletes_router)
app.include_router(controls_router)


@app.get("/")
def read_root():
    return {
        "app": "Skjold på tvers",
        "status": "ok",
        "admin": "/admin",
        "api_docs": "/docs",
    }
