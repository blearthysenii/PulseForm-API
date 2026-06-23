from sqlalchemy.orm import Session
from fastapi import HTTPException
from collections import Counter

from app.models.survey import Survey
from app.models.question import Question
from app.models.response import Response
from app.models.answer import Answer


def get_results(db: Session, survey_id: int, creator_id: int) -> dict:
    # Verify ownership
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id
    ).first()

    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey_id)
        .order_by(Question.position)
        .all()
    )

    total_responses = db.query(Response).filter(
        Response.survey_id == survey_id
    ).count()

    question_results = []

    for question in questions:
        answers = (
            db.query(Answer)
            .join(Response)
            .filter(
                Response.survey_id == survey_id,
                Answer.question_id == question.id
            )
            .all()
        )

        answer_count = len(answers)

        if question.type == "mcq":
            # Count by option_id, fall back to value_text
            option_counts = Counter()
            for a in answers:
                key = a.value_text or f"Option {a.option_id}" or "Unknown"
                option_counts[key] += 1

            chart_data = [
                {"label": label, "count": count}
                for label, count in option_counts.most_common()
            ]

            question_results.append({
                "question_id": question.id,
                "text": question.text,
                "type": "mcq",
                "answer_count": answer_count,
                "chart_data": chart_data,
            })

        elif question.type == "rating":
            rating_counts = Counter()
            for a in answers:
                if a.value_number is not None:
                    rating_counts[a.value_number] += 1

            # Fill in missing ratings with 0
            chart_data = [
                {"label": str(i), "count": rating_counts.get(i, 0)}
                for i in range(1, 6)
            ]

            values = [a.value_number for a in answers if a.value_number is not None]
            average = round(sum(values) / len(values), 1) if values else None

            question_results.append({
                "question_id": question.id,
                "text": question.text,
                "type": "rating",
                "answer_count": answer_count,
                "average": average,
                "chart_data": chart_data,
            })

        elif question.type == "text":
            text_answers = [
                a.value_text for a in answers if a.value_text and a.value_text.strip()
            ]

            question_results.append({
                "question_id": question.id,
                "text": question.text,
                "type": "text",
                "answer_count": answer_count,
                "text_answers": text_answers,
            })

    return {
        "survey_id": survey_id,
        "survey_title": survey.title,
        "total_responses": total_responses,
        "questions": question_results,
    }