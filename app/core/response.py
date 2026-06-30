from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.survey import Survey
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.response import Response
from app.models.answer import Answer
from app.schemas.response import ResponseSubmit


TEXT_TYPES = {"text", "short_answer", "paragraph", "date", "time", "file_upload"}
SINGLE_OPTION_TYPES = {"mcq", "single_choice", "dropdown"}
MULTI_OPTION_TYPES = {"multiple_choice", "checkbox"}
NUMBER_TYPES = {"rating", "linear_scale"}


def _get_published_survey(db: Session, survey_id: int) -> Survey:
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.is_published == True,
    ).first()

    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not published")

    return survey


def _answer_text(answer_data) -> str | None:
    value = answer_data.text_answer
    if value is None:
        value = answer_data.value_text
    if value is None:
        return None
    value = value.strip()
    return value or None


def _single_option_id(answer_data) -> int | None:
    return answer_data.selected_option_id or answer_data.option_id


def _answer_has_value(answer_data, question: Question) -> bool:
    if question.type == "section":
        return True
    if question.type in TEXT_TYPES:
        return _answer_text(answer_data) is not None
    if question.type in NUMBER_TYPES:
        return answer_data.value_number is not None
    if question.type in MULTI_OPTION_TYPES:
        return bool(answer_data.selected_option_ids)
    if question.type in SINGLE_OPTION_TYPES:
        return _single_option_id(answer_data) is not None
    return (
        _answer_text(answer_data) is not None
        or answer_data.value_number is not None
        or _single_option_id(answer_data) is not None
        or bool(answer_data.selected_option_ids)
    )


def _option_map_for_questions(db: Session, question_ids: list[int]) -> dict[int, dict[int, QuestionOption]]:
    options = (
        db.query(QuestionOption)
        .filter(QuestionOption.question_id.in_(question_ids))
        .all()
    )

    option_map: dict[int, dict[int, QuestionOption]] = {}
    for option in options:
        option_map.setdefault(option.question_id, {})[option.id] = option
    return option_map


def _build_answer_rows(db: Session, data: ResponseSubmit, questions: list[Question]) -> list[dict]:
    question_map = {question.id: question for question in questions}
    option_map = _option_map_for_questions(db, list(question_map.keys()))
    rows: list[dict] = []

    for answer_data in data.answers:
        question = question_map.get(answer_data.question_id)
        if not question:
            raise HTTPException(
                status_code=422,
                detail=f"Question {answer_data.question_id} does not belong to this survey",
            )

        if question.type == "section" or not _answer_has_value(answer_data, question):
            continue

        if question.type in TEXT_TYPES:
            rows.append(
                {
                    "question_id": question.id,
                    "value_text": _answer_text(answer_data),
                    "value_number": None,
                    "option_id": None,
                }
            )
            continue

        if question.type in NUMBER_TYPES:
            rows.append(
                {
                    "question_id": question.id,
                    "value_text": None,
                    "value_number": answer_data.value_number,
                    "option_id": None,
                }
            )
            continue

        if question.type in MULTI_OPTION_TYPES:
            for option_id in answer_data.selected_option_ids or []:
                option = option_map.get(question.id, {}).get(option_id)
                if not option:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Option {option_id} does not belong to question {question.id}",
                    )
                rows.append(
                    {
                        "question_id": question.id,
                        "value_text": option.text,
                        "value_number": None,
                        "option_id": option.id,
                    }
                )
            continue

        selected_option_id = _single_option_id(answer_data)
        if selected_option_id is not None:
            option = option_map.get(question.id, {}).get(selected_option_id)
            if not option:
                raise HTTPException(
                    status_code=422,
                    detail=f"Option {selected_option_id} does not belong to question {question.id}",
                )
            rows.append(
                {
                    "question_id": question.id,
                    "value_text": option.text,
                    "value_number": None,
                    "option_id": option.id,
                }
            )

    return rows


def submit_response(
    db: Session,
    survey_id: int,
    data: ResponseSubmit,
    user_id: int | None = None,
) -> Response:
    survey = _get_published_survey(db, survey_id)

    questions = db.query(Question).filter(Question.survey_id == survey_id).all()
    question_map = {question.id: question for question in questions}

    answers_by_question = {
        answer.question_id: answer
        for answer in data.answers
        if answer.question_id in question_map and _answer_has_value(answer, question_map[answer.question_id])
    }

    for question in questions:
        if question.type != "section" and question.is_required and question.id not in answers_by_question:
            raise HTTPException(
                status_code=422,
                detail=f"Question '{question.text}' is required",
            )

    answer_rows = _build_answer_rows(db, data, questions)

    if not survey.allow_multiple_responses:
        existing = None

        if user_id:
            existing = db.query(Response).filter(
                Response.survey_id == survey_id,
                Response.user_id == user_id,
            ).first()
        elif data.session_id:
            existing = db.query(Response).filter(
                Response.survey_id == survey_id,
                Response.session_id == data.session_id,
            ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="You have already submitted a response to this survey",
            )

    response = Response(
        survey_id=survey_id,
        user_id=user_id,
        session_id=data.session_id,
    )
    db.add(response)
    db.flush()

    for row in answer_rows:
        db.add(
            Answer(
                response_id=response.id,
                question_id=row["question_id"],
                value_text=row["value_text"],
                value_number=row["value_number"],
                option_id=row["option_id"],
            )
        )

    db.commit()
    db.refresh(response)
    return response


def get_responses(db: Session, survey_id: int, creator_id: int) -> list[Response]:
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id,
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
        Survey.creator_id == creator_id,
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
