import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.dashboard import (
    _build_feed_item,
    _first_question_of_type,
    _get_owned_survey,
    get_feed,
    get_nps,
    get_question_breakdowns,
    get_responses_over_time,
    get_summary,
)
from app.core.security import decode_token
from app.database import SessionLocal, get_db
from app.models.response import Response as ResponseModel
from app.models.user import User
from app.schemas.dashboard import (
    FeedResponse,
    NpsResponse,
    QuestionsResponse,
    ResponsesOverTimeResponse,
    SurveySummaryResponse,
)

router = APIRouter(prefix="/surveys/{survey_id}/dashboard", tags=["Dashboard"])

POLL_INTERVAL_SECONDS = 3


@router.get("/summary", response_model=SurveySummaryResponse)
def summary_endpoint(
    survey_id: int,
    range_param: str = Query("7d", alias="range"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_summary(db, survey_id, current_user.id, range_param)


@router.get("/responses-over-time", response_model=ResponsesOverTimeResponse)
def responses_over_time_endpoint(
    survey_id: int,
    range_param: str = Query("7d", alias="range"),
    bucket: str = Query("day"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_responses_over_time(db, survey_id, current_user.id, range_param, bucket)


@router.get("/nps", response_model=NpsResponse)
def nps_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_nps(db, survey_id, current_user.id)


@router.get("/questions", response_model=QuestionsResponse)
def questions_endpoint(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_question_breakdowns(db, survey_id, current_user.id)


@router.get("/feed", response_model=FeedResponse)
def feed_endpoint(
    survey_id: int,
    limit: int = Query(5, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_feed(db, survey_id, current_user.id, limit, cursor)


@router.get("/stream")
async def stream_endpoint(survey_id: int, request: Request, token: str = Query(...)):
    """
    Server-Sent Events stream of live response/kpi updates.

    Auth is a query param (not the usual Authorization header) because the
    browser's native EventSource API cannot set custom request headers.
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    setup_db = SessionLocal()
    try:
        user = setup_db.query(User).filter(User.id == int(payload.get("sub"))).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        _get_owned_survey(setup_db, survey_id, user.id)
        creator_id = user.id

        nps_question = _first_question_of_type(setup_db, survey_id, "rating")
        text_question = _first_question_of_type(setup_db, survey_id, "text")

        latest = (
            setup_db.query(ResponseModel.id)
            .filter(ResponseModel.survey_id == survey_id)
            .order_by(ResponseModel.id.desc())
            .first()
        )
        last_seen_id = latest[0] if latest else 0
    finally:
        setup_db.close()

    async def event_generator():
        nonlocal last_seen_id

        while True:
            if await request.is_disconnected():
                break

            poll_db = SessionLocal()
            try:
                new_responses = (
                    poll_db.query(ResponseModel)
                    .filter(ResponseModel.survey_id == survey_id, ResponseModel.id > last_seen_id)
                    .order_by(ResponseModel.id.asc())
                    .all()
                )

                if new_responses:
                    for response in new_responses:
                        feed_item = _build_feed_item(poll_db, response, nps_question, text_question)
                        total = (
                            poll_db.query(ResponseModel)
                            .filter(ResponseModel.survey_id == survey_id)
                            .count()
                        )
                        data = json.dumps({"totalResponses": total, "response": feed_item})
                        yield f"event: response.created\ndata: {data}\n\n"
                        last_seen_id = response.id

                    summary = get_summary(poll_db, survey_id, creator_id, "7d")
                    yield f"event: kpis.updated\ndata: {json.dumps(summary['kpis'])}\n\n"
            finally:
                poll_db.close()

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
