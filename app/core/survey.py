from sqlalchemy.orm import Session
from fastapi import HTTPException
import re
import secrets

from app.models.survey import Survey
from app.schemas.survey import SurveyCreate, SurveyUpdate


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "survey"


def ensure_public_slug(db: Session, survey: Survey) -> None:
    if survey.public_slug:
        return

    base_slug = _slugify(survey.title)

    for _ in range(20):
        candidate = f"{base_slug}-{secrets.token_hex(4)}"
        exists = db.query(Survey).filter(Survey.public_slug == candidate).first()

        if not exists:
            survey.public_slug = candidate
            return

    raise HTTPException(status_code=500, detail="Could not generate public survey link")


def create_survey(db: Session, data: SurveyCreate, creator_id: int):
    survey = Survey(
        title=data.title,
        description=data.description,
        creator_id=creator_id
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


def get_surveys(db: Session, creator_id: int):
    return db.query(Survey).filter(Survey.creator_id == creator_id).all()


def get_survey(db: Session, survey_id: int, creator_id: int):
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.creator_id == creator_id
    ).first()

    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    return survey


def update_survey(db: Session, survey_id: int, data: SurveyUpdate, creator_id: int):
    survey = get_survey(db, survey_id, creator_id)

    if data.title is not None:
        survey.title = data.title
    if data.description is not None:
        survey.description = data.description
    if data.is_published is not None:
        survey.is_published = data.is_published
        if data.is_published:
            ensure_public_slug(db, survey)

    db.commit()
    db.refresh(survey)
    return survey


def delete_survey(db: Session, survey_id: int, creator_id: int):
    survey = get_survey(db, survey_id, creator_id)
    db.delete(survey)
    db.commit()
    return {"message": "Survey deleted successfully"}


def publish_survey(db: Session, survey_id: int, creator_id: int):
    survey = get_survey(db, survey_id, creator_id)
    survey.is_published = True
    ensure_public_slug(db, survey)
    db.commit()
    db.refresh(survey)
    return survey


def unpublish_survey(db: Session, survey_id: int, creator_id: int):
    survey = get_survey(db, survey_id, creator_id)
    survey.is_published = False
    db.commit()
    db.refresh(survey)
    return survey
