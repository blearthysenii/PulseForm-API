from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.survey import SurveyCreate, SurveyResponse, SurveyUpdate
from app.core.survey import create_survey, get_surveys, get_survey, update_survey, delete_survey
from app.api.auth import get_current_user
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.auth import get_current_user
from app.database import get_db
from app.models.survey import Survey
from app.models.user import User
from app.core.dependencies import require_roles
from app.schemas.survey import SurveyCreate   

router = APIRouter(prefix="/surveys", tags=["Surveys"])


@router.post("/", response_model=SurveyResponse)
def create_survey_endpoint(
    survey: SurveyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ["creator", "admin"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    return create_survey(db=db, data=survey, creator_id=current_user.id)


@router.get("/", response_model=List[SurveyResponse])
def list_surveys_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_surveys(db=db, creator_id=current_user.id)


@router.get("/{survey_id}", response_model=SurveyResponse)
def get_survey_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_survey(db=db, survey_id=survey_id, creator_id=current_user.id)


@router.put("/{survey_id}", response_model=SurveyResponse)
def update_survey_endpoint(
    survey_id: int,
    data: SurveyUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return update_survey(db=db, survey_id=survey_id, data=data, creator_id=current_user.id)


@router.delete("/{survey_id}")
def delete_survey_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return delete_survey(db=db, survey_id=survey_id, creator_id=current_user.id)
@router.post("/")
def create_survey(
    survey_data: SurveyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["creator", "admin"]))
):
    new_survey = Survey(
        title=survey_data.title,
        description=survey_data.description,
        user_id=current_user.id
    )

    db.add(new_survey)
    db.commit()
    db.refresh(new_survey)

    return new_survey


@router.get("/")
def get_surveys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # admin sees everything
    if current_user.role in ["admin"]:
        return db.query(Survey).all()

    # creator sees only their own surveys
    return db.query(Survey).filter(Survey.user_id == current_user.id).all()

