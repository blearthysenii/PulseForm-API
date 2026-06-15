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
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.api.auth import router as auth_router

# Models
from app.models.user import User
from app.models.survey import Survey
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.response import Response
from app.models.answer import Answer

load_dotenv()

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PulseForm API")

origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "PulseForm API is running"}

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

app.include_router(auth_router)
