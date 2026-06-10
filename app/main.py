from fastapi import FastAPI
from app.database.db import engine

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-test")
def db_test():
    try:
        conn = engine.connect()
        conn.close()
        return {"db": "connected"}
    except Exception as e:
        return {"db": "failed", "error": str(e)}