from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.survey import Survey
from app.schemas.question import QuestionCreate, QuestionUpdate


CHOICE_TYPES = {"mcq", "single_choice", "multiple_choice"}
ALLOWED_TYPES = {*CHOICE_TYPES, "rating", "text"}


def _serialize_question(question: Question) -> dict:
    return {
        "id": question.id,
        "survey_id": question.survey_id,
        "text": question.text,
        "type": question.type,
        "is_required": question.is_required,
        "position": question.position,
        "options": [option.text for option in question.options],
    }


def _clean_options(options: list[str] | None) -> list[str]:
    if not options:
        return []

    return [option.strip() for option in options if option.strip()]


def _get_survey_or_404(db: Session, survey_id: int, creator_id: int) -> Survey:
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id
    ).first()

    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    return survey


def _ensure_survey_is_unpublished(survey: Survey) -> None:
    if survey.is_published:
        raise HTTPException(
            status_code=400,
            detail="Questions can only be changed before the survey is published"
        )


def _get_question_or_404(db: Session, question_id: int, survey_id: int) -> Question:
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.survey_id == survey_id
    ).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return question


def create_question(db: Session, survey_id: int, data: QuestionCreate, creator_id: int) -> dict:
    survey = _get_survey_or_404(db, survey_id, creator_id)
    _ensure_survey_is_unpublished(survey)

    if data.type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Question type must be one of: {', '.join(ALLOWED_TYPES)}"
        )

    clean_options = _clean_options(data.options)

    if data.type in CHOICE_TYPES and len(clean_options) < 2:
        raise HTTPException(
            status_code=422,
            detail="Choice questions must have at least 2 options"
        )

    question = Question(
        survey_id=survey_id,
        text=data.text,
        type=data.type,
        is_required=data.is_required,
        position=data.position
    )

    db.add(question)
    db.flush()

    if data.type in CHOICE_TYPES:
        for option_text in clean_options:
            db.add(QuestionOption(question_id=question.id, text=option_text))

    db.commit()
    db.refresh(question)

    return _serialize_question(question)


def get_questions(db: Session, survey_id: int, creator_id: int) -> list[dict]:
    _get_survey_or_404(db, survey_id, creator_id)

    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey_id)
        .order_by(Question.position)
        .all()
    )

    return [_serialize_question(question) for question in questions]


def get_question(db: Session, survey_id: int, question_id: int, creator_id: int) -> dict:
    _get_survey_or_404(db, survey_id, creator_id)
    question = _get_question_or_404(db, question_id, survey_id)

    return _serialize_question(question)


def update_question(
    db: Session,
    survey_id: int,
    question_id: int,
    data: QuestionUpdate,
    creator_id: int
) -> dict:
    survey = _get_survey_or_404(db, survey_id, creator_id)
    _ensure_survey_is_unpublished(survey)
    question = _get_question_or_404(db, question_id, survey_id)

    next_type = data.type if data.type is not None else question.type

    if next_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Question type must be one of: {', '.join(ALLOWED_TYPES)}"
        )

    clean_options = _clean_options(data.options)

    if next_type in CHOICE_TYPES and data.options is not None and len(clean_options) < 2:
        raise HTTPException(
            status_code=422,
            detail="Choice questions must have at least 2 options"
        )

    if data.text is not None:
        question.text = data.text
    if data.type is not None:
        question.type = data.type
    if data.is_required is not None:
        question.is_required = data.is_required
    if data.position is not None:
        question.position = data.position

    if data.options is not None:
        db.query(QuestionOption).filter(
            QuestionOption.question_id == question.id
        ).delete()

        if next_type in CHOICE_TYPES:
            for option_text in clean_options:
                db.add(QuestionOption(question_id=question.id, text=option_text))

    if question.type not in CHOICE_TYPES:
        db.query(QuestionOption).filter(
            QuestionOption.question_id == question.id
        ).delete()

    db.commit()
    db.refresh(question)

    return _serialize_question(question)


def delete_question(db: Session, survey_id: int, question_id: int, creator_id: int) -> dict:
    survey = _get_survey_or_404(db, survey_id, creator_id)
    _ensure_survey_is_unpublished(survey)
    question = _get_question_or_404(db, question_id, survey_id)

    db.delete(question)
    db.commit()

    return {"message": "Question deleted successfully"}
