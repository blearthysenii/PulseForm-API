import os

from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine
from app.api.auth import router as auth_router
from app.api.public import router as public_router
from app.api.survey import router as survey_router

# Models
from app.models.user import User
from app.models.survey import Survey
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.response import Response as ResponseModel
from app.models.answer import Answer
from app.api.question import router as question_router

load_dotenv()


app = FastAPI(title="PulseForm API")


origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://pulse-form.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_database_schema():
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE surveys ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT FALSE")
        )
        connection.execute(
            text("UPDATE surveys SET is_published = FALSE WHERE is_published IS NULL")
        )
        connection.execute(
            text("ALTER TABLE surveys ALTER COLUMN is_published SET DEFAULT FALSE")
        )
        connection.execute(
            text("ALTER TABLE surveys ALTER COLUMN is_published SET NOT NULL")
        )
        connection.execute(
            text("ALTER TABLE surveys ADD COLUMN IF NOT EXISTS public_slug VARCHAR(255)")
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_surveys_public_slug "
                "ON surveys(public_slug) WHERE public_slug IS NOT NULL"
            )
        )


# Create tables if they do not exist
Base.metadata.create_all(bind=engine)
ensure_database_schema()


@app.get("/")
def root():
    return {"message": "PulseForm API is running"}


app.include_router(survey_router)
app.include_router(auth_router)
app.include_router(question_router)
app.include_router(public_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.head("/health")
def health_head():
    return Response(status_code=200)


@app.get("/db-test")
def db_test():
    try:
        conn = engine.connect()
        conn.close()
        return {"db": "connected"}
    except Exception as e:
        return {"db": "failed", "error": str(e)}


