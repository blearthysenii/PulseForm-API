from collections import Counter

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.survey import Survey
from app.models.question import Question
from app.models.response import Response
from app.models.answer import Answer


CHOICE_TYPES = {"mcq", "single_choice", "multiple_choice", "checkbox", "dropdown"}
TEXT_TYPES = {"text", "short_answer", "paragraph", "date", "time", "file_upload"}
NUMBER_TYPES = {"rating", "linear_scale"}


def _answer_value(answer: Answer) -> str | int | None:
    if answer.value_text is not None:
        return answer.value_text
    if answer.value_number is not None:
        return answer.value_number
    if answer.option_id is not None:
        return f"Option {answer.option_id}"
    return None


def get_results(db: Session, survey_id: int, creator_id: int) -> dict:
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id,
    ).first()

    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey_id)
        .order_by(Question.position.asc(), Question.id.asc())
        .all()
    )
    question_map = {question.id: question for question in questions}

    responses = (
        db.query(Response)
        .filter(Response.survey_id == survey_id)
        .options(joinedload(Response.answers))
        .order_by(Response.submitted_at.desc())
        .all()
    )

    total_responses = len(responses)
    question_results = []

    for question in questions:
        answers = [
            answer
            for response in responses
            for answer in response.answers
            if answer.question_id == question.id
        ]
        answer_count = len({answer.response_id for answer in answers})

        result = {
            "question_id": question.id,
            "text": question.text,
            "type": question.type,
            "answer_count": answer_count,
        }

        if question.type in CHOICE_TYPES:
            option_counts = Counter()
            for answer in answers:
                label = answer.value_text or (
                    f"Option {answer.option_id}" if answer.option_id is not None else "Unknown"
                )
                option_counts[label] += 1
            result["chart_data"] = [
                {"label": label, "count": count}
                for label, count in option_counts.most_common()
            ]

        elif question.type in NUMBER_TYPES:
            rating_counts = Counter(
                answer.value_number
                for answer in answers
                if answer.value_number is not None
            )
            result["chart_data"] = [
                {"label": str(value), "count": rating_counts.get(value, 0)}
                for value in range(1, 6)
            ]
            values = [
                answer.value_number
                for answer in answers
                if answer.value_number is not None
            ]
            result["average"] = round(sum(values) / len(values), 1) if values else None

        elif question.type in TEXT_TYPES:
            result["text_answers"] = [
                answer.value_text
                for answer in answers
                if answer.value_text and answer.value_text.strip()
            ]

        question_results.append(result)

    individual_responses = []
    for response in responses:
        individual_responses.append(
            {
                "response_id": response.id,
                "submitted_at": response.submitted_at,
                "answers": [
                    {
                        "question_id": answer.question_id,
                        "question_text": question_map.get(answer.question_id).text
                        if question_map.get(answer.question_id)
                        else "",
                        "type": question_map.get(answer.question_id).type
                        if question_map.get(answer.question_id)
                        else "text",
                        "value": _answer_value(answer),
                    }
                    for answer in response.answers
                ],
            }
        )

    return {
        "survey_id": survey_id,
        "survey_title": survey.title,
        "total_responses": total_responses,
        "questions": question_results,
        "responses": individual_responses,
    }
