from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.results import get_results
from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter(tags=["Results"])


@router.get("/surveys/{survey_id}/results")
def get_results_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_results(db=db, survey_id=survey_id, creator_id=current_user.id)