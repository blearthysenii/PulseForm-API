from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
 
from app.database import get_db
from app.schemas.question import QuestionCreate, QuestionUpdate, QuestionResponse
from app.core.question import (
    create_question,
    get_questions,
    get_question,
    update_question,
    delete_question,
)
from app.api.auth import get_current_user
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.user import User
from app.core.dependencies import require_roles
 
router = APIRouter(prefix="/surveys/{survey_id}/questions", tags=["Questions"])


def serialize_question(db: Session, question: Question) -> dict:
    options = (
        db.query(QuestionOption)
        .filter(QuestionOption.question_id == question.id)
        .order_by(QuestionOption.id.asc())
        .all()
    )

    return {
        "id": question.id,
        "survey_id": question.survey_id,
        "text": question.text,
        "type": question.type,
        "is_required": question.is_required,
        "position": question.position,
        "options": [option.text for option in options],
    }
 
 
@router.post("/", response_model=QuestionResponse)
def create_question_endpoint(
    survey_id: int,
    data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["creator", "admin"]))
):
    question = create_question(db=db, survey_id=survey_id, data=data, creator_id=current_user.id)
    return serialize_question(db, question)
 
 
@router.get("/", response_model=List[QuestionResponse])
def list_questions_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    questions = get_questions(db=db, survey_id=survey_id, creator_id=current_user.id)
    return [serialize_question(db, question) for question in questions]
 
 
@router.get("/{question_id}", response_model=QuestionResponse)
def get_question_endpoint(
    survey_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = get_question(db=db, survey_id=survey_id, question_id=question_id, creator_id=current_user.id)
    return serialize_question(db, question)
 
 
@router.put("/{question_id}", response_model=QuestionResponse)
def update_question_endpoint(
    survey_id: int,
    question_id: int,
    data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = update_question(
        db=db,
        survey_id=survey_id,
        question_id=question_id,
        data=data,
        creator_id=current_user.id
    )
    return serialize_question(db, question)
 
 
@router.delete("/{question_id}")
def delete_question_endpoint(
    survey_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return delete_question(
        db=db,
        survey_id=survey_id,
        question_id=question_id,
        creator_id=current_user.id
    )
 
