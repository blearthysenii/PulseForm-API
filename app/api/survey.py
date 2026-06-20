import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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
from app.models.question import Question
from app.models.question_option import QuestionOption
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


@router.post("/{survey_id}/questions/import-csv")
async def import_questions_from_csv(
    survey_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400, detail="Only CSV files are allowed")

    survey = get_survey(db=db, survey_id=survey_id, creator_id=current_user.id)

    content = await file.read()

    try:
        decoded_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="Invalid CSV encoding. Please use UTF-8")

    csv_reader = csv.DictReader(io.StringIO(decoded_content))

    required_columns = {"question_text", "type", "is_required", "options"}

    if not csv_reader.fieldnames or not required_columns.issubset(set(csv_reader.fieldnames)):
        raise HTTPException(
            status_code=400,
            detail="CSV must contain columns: question_text,type,is_required,options"
        )

    allowed_types = {"mcq", "rating", "text"}
    imported_count = 0

    for index, row in enumerate(csv_reader, start=1):
        question_text = (row.get("question_text") or "").strip()
        question_type = (row.get("type") or "").strip().lower()
        is_required_value = (row.get("is_required") or "").strip().lower()
        options_value = (row.get("options") or "").strip()

        if not question_text:
            raise HTTPException(
                status_code=400, detail=f"Row {index}: question_text is required")

        if question_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Row {index}: type must be one of mcq, rating, text"
            )

        is_required = is_required_value in ["true", "1", "yes"]

        question = Question(
            survey_id=survey.id,
            text=question_text,
            type=question_type,
            is_required=is_required,
            position=index
        )

        db.add(question)
        db.flush()

        if question_type == "mcq":
            options = [option.strip()
                       for option in options_value.split("|") if option.strip()]

            if not options:
                raise HTTPException(
                    status_code=400,
                    detail=f"Row {index}: mcq questions must have options"
                )

            for option_text in options:
                db.add(QuestionOption(question_id=question.id, text=option_text))

        imported_count += 1

    db.commit()

    return {
        "message": "Questions imported successfully",
        "imported_questions": imported_count
    }
