from fastapi import FastAPI

app = FastAPI(title="Skjold på tvers")

@app.get("/")
def read_root():
    return {
        "app": "Skjold på tvers",
        "status": "ok"
    }
