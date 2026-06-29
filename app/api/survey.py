import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func
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
from app.models.answer import Answer
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.response import Response as SurveyResponseModel
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


@router.get("/{survey_id}/questions")
def get_survey_questions_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    survey = get_survey(db=db, survey_id=survey_id, creator_id=current_user.id)

    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey.id)
        .order_by(Question.position.asc(), Question.id.asc())
        .all()
    )

    return [
        {
            "id": question.id,
            "question_text": question.text,
            "type": question.type,
            "is_required": question.is_required,
            "position": question.position,
            "options": [
                option.text
                for option in db.query(QuestionOption)
                .filter(QuestionOption.question_id == question.id)
                .order_by(QuestionOption.id.asc())
                .all()
            ],
        }
        for question in questions
    ]


@router.get("/{survey_id}/results")
def get_survey_results_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    survey = get_survey(db=db, survey_id=survey_id, creator_id=current_user.id)
    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey.id)
        .order_by(Question.position.asc(), Question.id.asc())
        .all()
    )
    total_responses = (
        db.query(SurveyResponseModel)
        .filter(SurveyResponseModel.survey_id == survey.id)
        .count()
    )
    response_rows = (
        db.query(SurveyResponseModel)
        .filter(SurveyResponseModel.survey_id == survey.id)
        .order_by(SurveyResponseModel.submitted_at.desc(), SurveyResponseModel.id.desc())
        .all()
    )
    response_ids = [response.id for response in response_rows]
    options_by_id = {
        option.id: option.text
        for option in db.query(QuestionOption)
        .join(Question, QuestionOption.question_id == Question.id)
        .filter(Question.survey_id == survey.id)
        .all()
    }
    questions_by_id = {question.id: question for question in questions}
    answer_rows = (
        db.query(Answer)
        .filter(Answer.response_id.in_(response_ids))
        .order_by(Answer.id.asc())
        .all()
        if response_ids
        else []
    )
    answers_by_response_id = {}

    for answer in answer_rows:
        question = questions_by_id.get(answer.question_id)
        if not question:
            continue

        if answer.option_id is not None:
            value = options_by_id.get(answer.option_id, "Selected option")
        elif answer.value_number is not None:
            value = answer.value_number
        else:
            value = answer.value_text

        answers_by_response_id.setdefault(answer.response_id, []).append(
            {
                "question_id": answer.question_id,
                "question_text": question.text,
                "type": question.type,
                "value": value,
            }
        )

    results = []

    for question in questions:
        answer_count = db.query(Answer).filter(Answer.question_id == question.id).count()
        question_result = {
            "question_id": question.id,
            "text": question.text,
            "type": question.type,
            "answer_count": answer_count,
        }

        if question.type in {"single_choice", "multiple_choice", "mcq", "checkbox", "dropdown"}:
            options = (
                db.query(QuestionOption)
                .filter(QuestionOption.question_id == question.id)
                .order_by(QuestionOption.id.asc())
                .all()
            )
            counts = dict(
                db.query(Answer.option_id, func.count(Answer.id))
                .filter(Answer.question_id == question.id, Answer.option_id.isnot(None))
                .group_by(Answer.option_id)
                .all()
            )
            question_result["chart_data"] = [
                {"label": option.text, "count": counts.get(option.id, 0)}
                for option in options
            ]

        elif question.type in {"rating", "linear_scale"}:
            counts = dict(
                db.query(Answer.value_number, func.count(Answer.id))
                .filter(Answer.question_id == question.id, Answer.value_number.isnot(None))
                .group_by(Answer.value_number)
                .all()
            )
            average = (
                db.query(func.avg(Answer.value_number))
                .filter(Answer.question_id == question.id, Answer.value_number.isnot(None))
                .scalar()
            )
            question_result["chart_data"] = [
                {"label": str(value), "count": counts.get(value, 0)}
                for value in range(1, 6)
            ]
            question_result["average"] = round(float(average), 2) if average is not None else None

        elif question.type in {"text", "short_answer", "paragraph", "date", "time", "file_upload"}:
            text_answers = (
                db.query(Answer.value_text)
                .filter(Answer.question_id == question.id, Answer.value_text.isnot(None))
                .order_by(Answer.id.asc())
                .all()
            )
            question_result["text_answers"] = [answer.value_text for answer in text_answers]

        results.append(question_result)

    return {
        "survey_id": survey.id,
        "survey_title": survey.title,
        "total_responses": total_responses,
        "questions": results,
        "responses": [
            {
                "response_id": response.id,
                "submitted_at": response.submitted_at,
                "answers": answers_by_response_id.get(response.id, []),
            }
            for response in response_rows
        ],
    }


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

    if survey.is_published:
        raise HTTPException(
            status_code=400,
            detail="Questions can only be changed before the survey is published"
        )

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

    choice_types = {"mcq", "single_choice", "multiple_choice"}
    allowed_types = {*choice_types, "rating", "text"}
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
                detail=f"Row {index}: type must be one of single_choice, multiple_choice, mcq, rating, text"
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

        if question_type in choice_types:
            options = [option.strip()
                       for option in options_value.split("|") if option.strip()]

            if not options:
                raise HTTPException(
                    status_code=400,
                    detail=f"Row {index}: choice questions must have options"
                )

            for option_text in options:
                db.add(QuestionOption(question_id=question.id, text=option_text))

        imported_count += 1

    db.commit()

    return {
        "message": "Questions imported successfully",
        "imported_questions": imported_count
    }
