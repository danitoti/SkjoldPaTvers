from fastapi import FastAPI

from backend.app.database.init_db import init_db

app = FastAPI(title="Skjold på tvers")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def read_root():
    return {
        "app": "Skjold på tvers",
        "status": "ok",
        "database": "initialized",
    }
