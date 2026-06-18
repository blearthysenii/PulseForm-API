from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.survey import Survey
from app.schemas.survey import SurveyCreate, SurveyUpdate


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
    db.commit()
    db.refresh(survey)
    return survey


def unpublish_survey(db: Session, survey_id: int, creator_id: int):
    survey = get_survey(db, survey_id, creator_id)
    survey.is_published = False
    db.commit()
    db.refresh(survey)
    return survey