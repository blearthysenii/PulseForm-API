from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.survey import SurveyCreate, SurveyResponse, SurveyUpdate
from app.core.survey import (
    create_survey,
    get_surveys,
    get_survey,
    update_survey,
    delete_survey,
    publish_survey,
    unpublish_survey
)
from app.api.auth import get_current_user
from app.models.user import User
from app.core.dependencies import require_roles

router = APIRouter(prefix="/surveys", tags=["Surveys"])


@router.post("/", response_model=SurveyResponse)
def create_survey_endpoint(
    survey: SurveyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["creator", "admin"]))
):
    return create_survey(
        db=db,
        data=survey,
        creator_id=current_user.id
    )


@router.get("/", response_model=List[SurveyResponse])
def list_surveys_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_surveys(db=db, creator_id=current_user.id)


@router.get("/{survey_id}", response_model=SurveyResponse)
def get_survey_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_survey(db=db, survey_id=survey_id, creator_id=current_user.id)


@router.put("/{survey_id}", response_model=SurveyResponse)
def update_survey_endpoint(
    survey_id: int,
    data: SurveyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return update_survey(
        db=db,
        survey_id=survey_id,
        data=data,
        creator_id=current_user.id
    )


@router.delete("/{survey_id}")
def delete_survey_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return delete_survey(
        db=db,
        survey_id=survey_id,
        creator_id=current_user.id
    )


@router.patch("/{survey_id}/publish", response_model=SurveyResponse)
def publish_survey_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return publish_survey(db, survey_id, current_user.id)


@router.patch("/{survey_id}/unpublish", response_model=SurveyResponse)
def unpublish_survey_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return unpublish_survey(db, survey_id, current_user.id)