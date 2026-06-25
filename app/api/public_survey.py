from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.response import PublicResponseSubmit, ResponseResponse
from app.core.survey import get_survey_by_token
from app.core.response import submit_response
from app.models.question import Question
from app.models.question_option import QuestionOption

router = APIRouter(prefix="/s", tags=["Public Surveys"])


@router.get("/{share_token}")
def get_public_survey_endpoint(
    share_token: str,
    db: Session = Depends(get_db)
):
    """
    Public, unauthenticated view of a published survey, looked up by its
    share token. Used to render the respondent-facing form.
    """
    survey = get_survey_by_token(db, share_token)

    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey.id)
        .order_by(Question.position.asc(), Question.id.asc())
        .all()
    )

    return {
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "questions": [
            {
                "id": question.id,
                "question_text": question.text,
                "type": question.type,
                "is_required": question.is_required,
                "position": question.position,
                "options": [
                    option.text
                    for option in db.query(QuestionOption)
                    .filter(QuestionOption.question_id == question.id)
                    .order_by(QuestionOption.id.asc())
                    .all()
                ],
            }
            for question in questions
        ],
    }


@router.post("/{share_token}/responses", response_model=ResponseResponse)
def submit_public_response_endpoint(
    share_token: str,
    data: PublicResponseSubmit,
    db: Session = Depends(get_db)
):
    """
    Submit a response to a published survey via its public share link.
    Always anonymous. A response is uniquely identified by
    (survey, session_id) to prevent the same respondent from submitting
    more than once, unless the survey allows multiple responses.
    """
    survey = get_survey_by_token(db, share_token)
    return submit_response(
        db=db,
        survey_id=survey.id,
        data=data,
        user_id=None
    )
