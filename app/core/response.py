from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
 
from app.models.survey import Survey
from app.models.question import Question
from app.models.response import Response
from app.models.answer import Answer
from app.schemas.response import ResponseSubmit
 
 
def _get_published_survey(db: Session, survey_id: int) -> Survey:
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.is_published == True
    ).first()
 
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not published")
 
    return survey
 
 
def submit_response(
    db: Session,
    survey_id: int,
    data: ResponseSubmit,
    user_id: int | None = None
) -> Response:
    survey = _get_published_survey(db, survey_id)
 
    # Load all questions for this survey
    questions = db.query(Question).filter(Question.survey_id == survey_id).all()
    question_map = {q.id: q for q in questions}
 
    # Check all required questions are answered
    answered_question_ids = {a.question_id for a in data.answers}
    for question in questions:
        if question.is_required and question.id not in answered_question_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Question '{question.text}' is required"
            )
 
    # Validate each answer belongs to this survey
    for answer in data.answers:
        if answer.question_id not in question_map:
            raise HTTPException(
                status_code=422,
                detail=f"Question {answer.question_id} does not belong to this survey"
            )
 
    # Check multiple responses if not allowed
    if not survey.allow_multiple_responses:
        existing = None

        if user_id:
            existing = db.query(Response).filter(
                Response.survey_id == survey_id,
                Response.user_id == user_id
            ).first()
        elif data.session_id:
            existing = db.query(Response).filter(
                Response.survey_id == survey_id,
                Response.session_id == data.session_id
            ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="You have already submitted a response to this survey"
            )
 
    # Create response
    response = Response(
        survey_id=survey_id,
        user_id=user_id,
        session_id=data.session_id
    )
    db.add(response)
    db.flush()
 
    # Create answers
    for answer_data in data.answers:
        answer = Answer(
            response_id=response.id,
            question_id=answer_data.question_id,
            value_text=answer_data.value_text,
            value_number=answer_data.value_number,
            option_id=answer_data.option_id
        )
        db.add(answer)
 
    db.commit()
    db.refresh(response)
    return response
 
 
def get_responses(db: Session, survey_id: int, creator_id: int) -> list[Response]:
    # Verify survey belongs to creator
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id
    ).first()
 
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
 
    return (
        db.query(Response)
        .filter(Response.survey_id == survey_id)
        .options(joinedload(Response.answers))
        .order_by(Response.submitted_at.desc())
        .all()
    )
 
 
def get_response(db: Session, survey_id: int, response_id: int, creator_id: int) -> Response:
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id
    ).first()
 
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
 
    response = (
        db.query(Response)
        .filter(Response.id == response_id, Response.survey_id == survey_id)
        .options(joinedload(Response.answers))
        .first()
    )
 
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
 
    return response