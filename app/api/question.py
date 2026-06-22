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
from app.models.user import User
from app.core.dependencies import require_roles
 
router = APIRouter(prefix="/surveys/{survey_id}/questions", tags=["Questions"])
 
 
@router.post("/", response_model=QuestionResponse)
def create_question_endpoint(
    survey_id: int,
    data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["creator", "admin"]))
):
    return create_question(db=db, survey_id=survey_id, data=data, creator_id=current_user.id)
 
 
@router.get("/", response_model=List[QuestionResponse])
def list_questions_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_questions(db=db, survey_id=survey_id, creator_id=current_user.id)
 
 
@router.get("/{question_id}", response_model=QuestionResponse)
def get_question_endpoint(
    survey_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_question(db=db, survey_id=survey_id, question_id=question_id, creator_id=current_user.id)
 
 
@router.put("/{question_id}", response_model=QuestionResponse)
def update_question_endpoint(
    survey_id: int,
    question_id: int,
    data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return update_question(
        db=db,
        survey_id=survey_id,
        question_id=question_id,
        data=data,
        creator_id=current_user.id
    )
 
 
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
 