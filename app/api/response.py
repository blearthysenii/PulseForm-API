from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
 
from app.database import get_db
from app.schemas.response import ResponseSubmit, ResponseResponse
from app.core.response import submit_response, get_responses, get_response
from app.api.auth import get_current_user
from app.models.user import User
 
router = APIRouter(tags=["Responses"])
 
 
@router.post("/surveys/{survey_id}/respond", response_model=ResponseResponse)
def submit_response_endpoint(
    survey_id: int,
    data: ResponseSubmit,
    db: Session = Depends(get_db),
    # Optional auth — respondents can be anonymous
    current_user: Optional[User] = Depends(lambda: None)
):
    """
    Submit a response to a published survey.
    Authentication is optional — anonymous responses are allowed.
    """
    return submit_response(
        db=db,
        survey_id=survey_id,
        data=data,
        user_id=None  # anonymous by default; see note below
    )
 
 
@router.post("/surveys/{survey_id}/respond/authenticated", response_model=ResponseResponse)
def submit_response_authenticated_endpoint(
    survey_id: int,
    data: ResponseSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a response as a signed-in user.
    Enables duplicate-response checking per user.
    """
    return submit_response(
        db=db,
        survey_id=survey_id,
        data=data,
        user_id=current_user.id
    )
 
 
@router.get("/surveys/{survey_id}/responses", response_model=List[ResponseResponse])
def list_responses_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all responses for a survey. Only accessible by the survey creator.
    """
    return get_responses(db=db, survey_id=survey_id, creator_id=current_user.id)
 
 
@router.get("/surveys/{survey_id}/responses/{response_id}", response_model=ResponseResponse)
def get_response_endpoint(
    survey_id: int,
    response_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single response by ID. Only accessible by the survey creator.
    """
    return get_response(
        db=db,
        survey_id=survey_id,
        response_id=response_id,
        creator_id=current_user.id
    )
 