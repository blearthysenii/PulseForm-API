from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.answer import Answer
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.response import Response
from app.models.survey import Survey
from app.schemas.survey import (
    PublicResponseCreate,
    PublicResponseCreated,
    PublicSurveyResponse,
)

router = APIRouter(prefix="/public", tags=["Public Surveys"])

CHOICE_TYPES = {"single_choice", "multiple_choice", "mcq", "checkbox", "dropdown"}
TEXT_TYPES = {"text", "short_answer", "paragraph", "date", "time", "file_upload"}
RATING_TYPES = {"rating", "linear_scale"}


def get_published_survey(db: Session, public_slug: str) -> Survey:
    survey = (
        db.query(Survey)
        .filter(Survey.public_slug == public_slug, Survey.is_published.is_(True))
        .first()
    )

    if not survey:
        raise HTTPException(status_code=404, detail="Published survey not found")

    return survey


def serialize_public_survey(db: Session, survey: Survey) -> dict:
    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey.id)
        .order_by(Question.position.asc(), Question.id.asc())
        .all()
    )

    serialized_questions = []

    for question in questions:
        options = (
            db.query(QuestionOption)
            .filter(QuestionOption.question_id == question.id)
            .order_by(QuestionOption.id.asc())
            .all()
        )

        serialized_questions.append(
            {
                "id": question.id,
                "text": question.text,
                "question_text": question.text,
                "type": question.type,
                "is_required": question.is_required,
                "position": question.position,
                "options": [{"id": option.id, "text": option.text} for option in options],
            }
        )

    return {
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "public_slug": survey.public_slug,
        "questions": serialized_questions,
    }


@router.get("/surveys/{public_slug}", response_model=PublicSurveyResponse)
def get_public_survey(public_slug: str, db: Session = Depends(get_db)):
    survey = get_published_survey(db, public_slug)
    return serialize_public_survey(db, survey)


@router.post(
    "/surveys/{public_slug}/responses",
    response_model=PublicResponseCreated,
    status_code=status.HTTP_201_CREATED,
)
def submit_public_response(
    public_slug: str,
    data: PublicResponseCreate,
    db: Session = Depends(get_db),
):
    survey = get_published_survey(db, public_slug)
    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey.id)
        .order_by(Question.position.asc(), Question.id.asc())
        .all()
    )
    questions_by_id = {question.id: question for question in questions}
    answers_by_question_id = {}

    for answer in data.answers:
        if answer.question_id not in questions_by_id:
            raise HTTPException(
                status_code=400,
                detail=f"Question {answer.question_id} does not belong to this survey",
            )

        if answer.question_id in answers_by_question_id:
            raise HTTPException(
                status_code=400,
                detail=f"Question {answer.question_id} was submitted more than once",
            )

        answers_by_question_id[answer.question_id] = answer

    options = (
        db.query(QuestionOption)
        .filter(QuestionOption.question_id.in_(list(questions_by_id.keys())))
        .all()
        if questions_by_id
        else []
    )
    valid_option_ids_by_question_id: dict[int, set[int]] = {}

    for option in options:
        valid_option_ids_by_question_id.setdefault(option.question_id, set()).add(option.id)

    response = Response(survey_id=survey.id)
    db.add(response)
    db.flush()

    saved_answers = 0

    for question in questions:
        submitted_answer = answers_by_question_id.get(question.id)

        if not submitted_answer:
            if question.is_required:
                raise HTTPException(status_code=400, detail=f"Question {question.id} is required")
            continue

        if question.type == "section":
            continue

        if question.type in TEXT_TYPES:
            text_answer = (submitted_answer.text_answer or "").strip()

            if not text_answer:
                if question.is_required:
                    raise HTTPException(status_code=400, detail=f"Question {question.id} is required")
                continue

            db.add(
                Answer(
                    response_id=response.id,
                    question_id=question.id,
                    value_text=text_answer,
                )
            )
            saved_answers += 1
            continue

        if question.type in RATING_TYPES:
            value_number = submitted_answer.value_number

            if value_number is None:
                if question.is_required:
                    raise HTTPException(status_code=400, detail=f"Question {question.id} is required")
                continue

            if value_number < 1 or value_number > 5:
                raise HTTPException(status_code=400, detail="Rating answers must be between 1 and 5")

            db.add(
                Answer(
                    response_id=response.id,
                    question_id=question.id,
                    value_number=value_number,
                )
            )
            saved_answers += 1
            continue

        if question.type in CHOICE_TYPES:
            valid_option_ids = valid_option_ids_by_question_id.get(question.id, set())

            if question.type in {"multiple_choice", "checkbox"}:
                selected_option_ids = submitted_answer.selected_option_ids or []
                if submitted_answer.selected_option_id is not None:
                    selected_option_ids = [submitted_answer.selected_option_id, *selected_option_ids]

                selected_option_ids = list(dict.fromkeys(selected_option_ids))
            else:
                selected_option_ids = (
                    [submitted_answer.selected_option_id]
                    if submitted_answer.selected_option_id is not None
                    else []
                )

            if not selected_option_ids:
                if question.is_required:
                    raise HTTPException(status_code=400, detail=f"Question {question.id} is required")
                continue

            invalid_option_ids = [
                option_id for option_id in selected_option_ids if option_id not in valid_option_ids
            ]

            if invalid_option_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Selected option does not belong to question {question.id}",
                )

            for selected_option_id in selected_option_ids:
                db.add(
                    Answer(
                        response_id=response.id,
                        question_id=question.id,
                        option_id=selected_option_id,
                    )
                )
                saved_answers += 1

            continue

        raise HTTPException(status_code=400, detail=f"Unsupported question type: {question.type}")

    db.commit()
    db.refresh(response)

    return {
        "id": response.id,
        "survey_id": response.survey_id,
        "submitted_at": response.submitted_at,
        "answers_saved": saved_answers,
    }
