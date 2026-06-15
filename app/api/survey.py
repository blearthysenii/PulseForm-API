from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.auth import get_current_user
from app.database import get_db
from app.models.survey import Survey
from app.models.user import User
from app.core.dependencies import require_roles
from app.schemas.survey import SurveyCreate   

router = APIRouter(prefix="/surveys", tags=["Surveys"])


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

