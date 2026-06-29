from sqlalchemy.orm import Session
from fastapi import HTTPException
 
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.survey import Survey
from app.schemas.question import QuestionCreate, QuestionUpdate
 
 
ALLOWED_TYPES = {
    "single_choice",
    "multiple_choice",
    "mcq",
    "checkbox",
    "dropdown",
    "rating",
    "linear_scale",
    "text",
    "short_answer",
    "paragraph",
    "date",
    "time",
    "file_upload",
    "section",
}
CHOICE_TYPES = {"single_choice", "multiple_choice", "mcq", "checkbox", "dropdown"}


def _clean_options(options: list[str] | None) -> list[str]:
    if not options:
        return []

    return [option.strip() for option in options if option and option.strip()]


def _replace_question_options(db: Session, question_id: int, options: list[str]) -> None:
    db.query(QuestionOption).filter(QuestionOption.question_id == question_id).delete()

    for option_text in options:
        db.add(QuestionOption(question_id=question_id, text=option_text))
 
 
def _get_survey_or_404(db: Session, survey_id: int, creator_id: int) -> Survey:
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id
    ).first()
 
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
 
    return survey
 
 
def _get_question_or_404(db: Session, question_id: int, survey_id: int) -> Question:
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.survey_id == survey_id
    ).first()
 
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
 
    return question
 
 
def create_question(db: Session, survey_id: int, data: QuestionCreate, creator_id: int) -> Question:
    _get_survey_or_404(db, survey_id, creator_id)
 
    if data.type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Question type must be one of: {', '.join(ALLOWED_TYPES)}"
        )

    clean_options = _clean_options(data.options)

    if data.type in CHOICE_TYPES and len(clean_options) < 2:
        raise HTTPException(
            status_code=422,
            detail="Choice questions need at least 2 options"
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
        _replace_question_options(db, question.id, clean_options)

    db.commit()
    db.refresh(question)
    return question
 
 
def get_questions(db: Session, survey_id: int, creator_id: int) -> list[Question]:
    _get_survey_or_404(db, survey_id, creator_id)
 
    return (
        db.query(Question)
        .filter(Question.survey_id == survey_id)
        .order_by(Question.position)
        .all()
    )
 
 
def get_question(db: Session, survey_id: int, question_id: int, creator_id: int) -> Question:
    _get_survey_or_404(db, survey_id, creator_id)
    return _get_question_or_404(db, question_id, survey_id)
 
 
def update_question(
    db: Session,
    survey_id: int,
    question_id: int,
    data: QuestionUpdate,
    creator_id: int
) -> Question:
    _get_survey_or_404(db, survey_id, creator_id)
    question = _get_question_or_404(db, question_id, survey_id)
 
    if data.type is not None and data.type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Question type must be one of: {', '.join(ALLOWED_TYPES)}"
        )

    next_type = data.type if data.type is not None else question.type
    clean_options = _clean_options(data.options)

    if next_type in CHOICE_TYPES and data.options is not None and len(clean_options) < 2:
        raise HTTPException(
            status_code=422,
            detail="Choice questions need at least 2 options"
        )
 
    if data.text is not None:
        question.text = data.text
    if data.type is not None:
        question.type = data.type
    if data.is_required is not None:
        question.is_required = data.is_required
    if data.position is not None:
        question.position = data.position

    if next_type not in CHOICE_TYPES:
        _replace_question_options(db, question.id, [])
    elif data.options is not None:
        _replace_question_options(db, question.id, clean_options)
 
    db.commit()
    db.refresh(question)
    return question
 
 
def delete_question(db: Session, survey_id: int, question_id: int, creator_id: int) -> dict:
    _get_survey_or_404(db, survey_id, creator_id)
    question = _get_question_or_404(db, question_id, survey_id)
 
    db.delete(question)
    db.commit()
    return {"message": "Question deleted successfully"}
