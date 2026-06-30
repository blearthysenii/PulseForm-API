from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.response import PublicResponseSubmit, PublicResponseResult
from app.core.survey import get_survey_by_token
from app.core.response import submit_response
from app.models.question import Question
from app.models.question_option import QuestionOption

router = APIRouter(tags=["Public Surveys"])


def _public_survey_payload(db: Session, share_token: str) -> dict:
    survey = get_survey_by_token(db, share_token)

    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey.id)
        .order_by(Question.position.asc(), Question.id.asc())
        .all()
    )

    question_payloads = []
    for question in questions:
        options = (
            db.query(QuestionOption)
            .filter(QuestionOption.question_id == question.id)
            .order_by(QuestionOption.id.asc())
            .all()
        )

        question_payloads.append(
            {
                "id": question.id,
                "text": question.text,
                "question_text": question.text,
                "type": question.type,
                "is_required": question.is_required,
                "position": question.position,
                "options": [
                    {"id": option.id, "text": option.text}
                    for option in options
                ],
            }
        )

    return {
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "public_slug": survey.public_slug,
        "questions": question_payloads,
    }


@router.get("/s/{share_token}")
@router.get("/public/surveys/{share_token}")
def get_public_survey_endpoint(
    share_token: str,
    db: Session = Depends(get_db),
):
    return _public_survey_payload(db, share_token)


@router.post("/s/{share_token}/responses", response_model=PublicResponseResult)
@router.post("/public/surveys/{share_token}/responses", response_model=PublicResponseResult)
def submit_public_response_endpoint(
    share_token: str,
    data: PublicResponseSubmit,
    db: Session = Depends(get_db),
):
    survey = get_survey_by_token(db, share_token)
    response = submit_response(
        db=db,
        survey_id=survey.id,
        data=data,
        user_id=None,
    )

    return {
        "id": response.id,
        "survey_id": response.survey_id,
        "submitted_at": response.submitted_at,
        "answers_saved": len(response.answers),
    }
