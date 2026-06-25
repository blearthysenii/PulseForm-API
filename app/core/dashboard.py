import hashlib
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.percentages import largest_remainder_pct
from app.models.answer import Answer
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.response import Response
from app.models.survey import Survey
from app.models.user import User

AVATAR_PALETTE = ["#3b82f6", "#7c3aed", "#0d9488", "#ea580c", "#dc2626"]
RATING_BUCKETS = {1: "detractor", 2: "detractor", 3: "detractor", 4: "passive", 5: "promoter"}


def to_iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_owned_survey(db: Session, survey_id: int, creator_id: int) -> Survey:
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id
    ).first()

    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    return survey


def _range_window(range_param: str, survey_created_at: datetime) -> tuple[datetime, datetime, datetime | None]:
    """Returns (current_start, now, previous_start). previous_start is None for 'all'."""
    now = datetime.now(timezone.utc)

    if range_param == "7d":
        days = 7
    elif range_param == "30d":
        days = 30
    elif range_param == "all":
        start = survey_created_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return start, now, None
    else:
        raise HTTPException(status_code=422, detail="range must be one of: 7d, 30d, all")

    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)
    return current_start, now, previous_start


def _avatar_color(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(AVATAR_PALETTE)
    return AVATAR_PALETTE[index]


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "AN"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _first_question_of_type(db: Session, survey_id: int, q_type: str) -> Question | None:
    return (
        db.query(Question)
        .filter(Question.survey_id == survey_id, Question.type == q_type)
        .order_by(Question.position.asc(), Question.id.asc())
        .first()
    )


def _nps_for_question(db: Session, question_id: int, since: datetime | None, until: datetime | None):
    query = db.query(Answer.value_number).join(Response).filter(
        Answer.question_id == question_id,
        Answer.value_number.isnot(None),
    )
    if since is not None:
        query = query.filter(Response.submitted_at >= since)
    if until is not None:
        query = query.filter(Response.submitted_at < until)

    values = [row[0] for row in query.all()]
    total = len(values)

    if total == 0:
        return None

    bucket_counts = Counter(RATING_BUCKETS.get(v, "passive") for v in values)
    promoters = bucket_counts.get("promoter", 0)
    passives = bucket_counts.get("passive", 0)
    detractors = bucket_counts.get("detractor", 0)

    promoters_pct, passives_pct, detractors_pct = largest_remainder_pct(
        [promoters, passives, detractors]
    )

    return {
        "total": total,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
        "promoters_pct": promoters_pct,
        "passives_pct": passives_pct,
        "detractors_pct": detractors_pct,
        "score": promoters_pct - detractors_pct,
    }


def _completion_rate(db: Session, survey_id: int, total_questions: int, since: datetime | None, until: datetime | None) -> float | None:
    if total_questions == 0:
        return None

    query = db.query(Response.id).filter(Response.survey_id == survey_id)
    if since is not None:
        query = query.filter(Response.submitted_at >= since)
    if until is not None:
        query = query.filter(Response.submitted_at < until)
    response_ids = [row[0] for row in query.all()]

    if not response_ids:
        return None

    answered_counts = (
        db.query(Answer.response_id, Answer.question_id)
        .filter(Answer.response_id.in_(response_ids))
        .all()
    )
    per_response: dict[int, set[int]] = {}
    for response_id, question_id in answered_counts:
        per_response.setdefault(response_id, set()).add(question_id)

    ratios = [
        len(per_response.get(rid, set())) / total_questions for rid in response_ids
    ]
    return sum(ratios) / len(ratios) * 100


def get_summary(db: Session, survey_id: int, creator_id: int, range_param: str = "7d") -> dict:
    survey = _get_owned_survey(db, survey_id, creator_id)
    current_start, now, previous_start = _range_window(range_param, survey.created_at)

    total_questions = db.query(Question).filter(Question.survey_id == survey_id).count()

    current_total = db.query(Response).filter(
        Response.survey_id == survey_id, Response.submitted_at >= current_start
    ).count()

    total_responses_delta_pct = None
    completion_rate_delta_pct = None
    current_completion = _completion_rate(db, survey_id, total_questions, current_start, None)

    if previous_start is not None:
        previous_total = db.query(Response).filter(
            Response.survey_id == survey_id,
            Response.submitted_at >= previous_start,
            Response.submitted_at < current_start,
        ).count()

        if previous_total > 0:
            total_responses_delta_pct = round((current_total - previous_total) / previous_total * 100)
        elif current_total > 0:
            total_responses_delta_pct = None  # growth from zero is undefined, not "+100%"

        previous_completion = _completion_rate(db, survey_id, total_questions, previous_start, current_start)
        if current_completion is not None and previous_completion is not None:
            completion_rate_delta_pct = round(current_completion - previous_completion)

    nps_question = _first_question_of_type(db, survey_id, "rating")
    nps = None
    nps_delta = None

    if nps_question is not None:
        current_nps = _nps_for_question(db, nps_question.id, current_start, None)
        nps = current_nps["score"] if current_nps else None

        if previous_start is not None and current_nps is not None:
            previous_nps = _nps_for_question(db, nps_question.id, previous_start, current_start)
            if previous_nps is not None:
                nps_delta = current_nps["score"] - previous_nps["score"]

    return {
        "id": str(survey.id),
        "title": survey.title,
        "status": "live" if survey.is_published else "draft",
        "openedAt": to_iso_utc(survey.created_at),
        "closesAt": None,
        "kpis": {
            "totalResponses": current_total,
            "totalResponsesDeltaPct": total_responses_delta_pct,
            "completionRatePct": round(current_completion) if current_completion is not None else None,
            "completionRateDeltaPct": completion_rate_delta_pct,
            "nps": nps,
            "npsDelta": nps_delta,
        },
    }


def get_responses_over_time(db: Session, survey_id: int, creator_id: int, range_param: str, bucket: str) -> dict:
    survey = _get_owned_survey(db, survey_id, creator_id)

    if bucket not in ("day", "week"):
        raise HTTPException(status_code=422, detail="bucket must be 'day' or 'week'")

    start, now, _ = _range_window(range_param, survey.created_at)

    timestamps = [
        row[0] for row in db.query(Response.submitted_at).filter(
            Response.survey_id == survey_id,
            Response.submitted_at >= start,
        ).all()
    ]
    timestamps = [
        ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc) for ts in timestamps
    ]

    counts: Counter[str] = Counter()

    if bucket == "day":
        cursor = start.date()
        end_date = now.date()
        bucket_keys = []
        while cursor <= end_date:
            bucket_keys.append(cursor.isoformat())
            cursor += timedelta(days=1)
        for ts in timestamps:
            counts[ts.date().isoformat()] += 1
    else:
        week_start = start.date() - timedelta(days=start.date().weekday())
        end_week_start = now.date() - timedelta(days=now.date().weekday())
        bucket_keys = []
        cursor = week_start
        while cursor <= end_week_start:
            bucket_keys.append(cursor.isoformat())
            cursor += timedelta(days=7)
        for ts in timestamps:
            ts_week_start = ts.date() - timedelta(days=ts.date().weekday())
            counts[ts_week_start.isoformat()] += 1

    points = [{"date": key, "count": counts.get(key, 0)} for key in bucket_keys]

    return {"range": range_param, "bucket": bucket, "points": points}


def get_nps(db: Session, survey_id: int, creator_id: int) -> dict:
    _get_owned_survey(db, survey_id, creator_id)

    nps_question = _first_question_of_type(db, survey_id, "rating")
    if nps_question is None:
        raise HTTPException(
            status_code=404,
            detail="This survey has no rating question to compute an NPS-style score from",
        )

    result = _nps_for_question(db, nps_question.id, None, None)
    if result is None:
        raise HTTPException(status_code=404, detail="No answers yet for the NPS-proxy question")

    return {
        "score": result["score"],
        "total": result["total"],
        "segments": {
            "promoters": {"count": result["promoters"], "pct": result["promoters_pct"]},
            "passives": {"count": result["passives"], "pct": result["passives_pct"]},
            "detractors": {"count": result["detractors"], "pct": result["detractors_pct"]},
        },
    }


def get_question_breakdowns(db: Session, survey_id: int, creator_id: int) -> dict:
    _get_owned_survey(db, survey_id, creator_id)

    questions = (
        db.query(Question)
        .filter(Question.survey_id == survey_id)
        .order_by(Question.position.asc(), Question.id.asc())
        .all()
    )

    out = []

    for question in questions:
        answers = db.query(Answer).filter(Answer.question_id == question.id).all()
        total_answers = len(answers)

        if question.type in ("mcq", "single_choice", "multiple_choice"):
            options = (
                db.query(QuestionOption)
                .filter(QuestionOption.question_id == question.id)
                .order_by(QuestionOption.id.asc())
                .all()
            )
            answer_counts = Counter(a.value_text for a in answers if a.value_text)
            counts = [answer_counts.get(opt.text, 0) for opt in options]
            pcts = largest_remainder_pct(counts)

            out.append({
                "id": str(question.id),
                "order": question.position,
                "label": question.text,
                "type": question.type,
                "totalAnswers": total_answers,
                "options": [
                    {"label": opt.text, "count": count, "pct": pct}
                    for opt, count, pct in zip(options, counts, pcts)
                ],
            })

        elif question.type == "rating":
            values = [a.value_number for a in answers if a.value_number is not None]
            counts_by_value = Counter(values)
            counts = [counts_by_value.get(i, 0) for i in range(1, 6)]
            pcts = largest_remainder_pct(counts)
            average = round(sum(values) / len(values), 2) if values else None

            out.append({
                "id": str(question.id),
                "order": question.position,
                "label": question.text,
                "type": "rating",
                "totalAnswers": total_answers,
                "scaleMax": 5,
                "average": average,
                "distribution": [
                    {"value": i, "pct": pct} for i, pct in zip(range(1, 6), pcts)
                ],
            })

        else:  # text
            text_answers = [a.value_text for a in answers if a.value_text and a.value_text.strip()]
            out.append({
                "id": str(question.id),
                "order": question.position,
                "label": question.text,
                "type": "text",
                "totalAnswers": total_answers,
                "textAnswers": text_answers,
            })

    return {"questions": out}


def _build_feed_item(db: Session, response: Response, nps_question: Question | None, text_question: Question | None) -> dict:
    if response.user_id:
        user = db.query(User).filter(User.id == response.user_id).first()
        name = user.full_name if user else "Anonymous"
        seed = f"user-{response.user_id}"
    else:
        name = "Anonymous"
        seed = f"session-{response.session_id or response.id}"

    rating_score = None
    if nps_question is not None:
        answer = db.query(Answer).filter(
            Answer.response_id == response.id, Answer.question_id == nps_question.id
        ).first()
        if answer and answer.value_number is not None:
            rating_score = int((answer.value_number - 1) * 2.5 + 0.5)

    comment = None
    if text_question is not None:
        answer = db.query(Answer).filter(
            Answer.response_id == response.id, Answer.question_id == text_question.id
        ).first()
        if answer and answer.value_text:
            comment = answer.value_text

    return {
        "id": f"resp_{response.id}",
        "respondent": {
            "name": name,
            "initials": _initials(name),
            "avatarColor": _avatar_color(seed),
        },
        "submittedAt": to_iso_utc(response.submitted_at),
        "ratingScore": rating_score,
        "comment": comment,
    }


def get_feed(db: Session, survey_id: int, creator_id: int, limit: int, cursor: str | None) -> dict:
    _get_owned_survey(db, survey_id, creator_id)

    query = db.query(Response).filter(Response.survey_id == survey_id)
    if cursor:
        try:
            cursor_id = int(cursor)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid cursor")
        query = query.filter(Response.id < cursor_id)

    items = query.order_by(Response.id.desc()).limit(limit).all()

    nps_question = _first_question_of_type(db, survey_id, "rating")
    text_question = _first_question_of_type(db, survey_id, "text")

    feed_items = [_build_feed_item(db, r, nps_question, text_question) for r in items]
    next_cursor = str(items[-1].id) if len(items) == limit else None

    return {"items": feed_items, "nextCursor": next_cursor}
