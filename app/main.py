from fastapi import FastAPI

from app.database.db import Base, engine
from app.models import User, Survey, Question, QuestionOption, Response, Answer

app = FastAPI()

Base.metadata.create_all(bind=engine)


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