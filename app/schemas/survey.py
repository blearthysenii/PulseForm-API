from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SurveyCreate(BaseModel):
    title: str
    description: Optional[str] = None


class SurveyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    creator_id: int
    is_published: bool
    allow_multiple_responses: bool

    public_slug: Optional[str] = None
    share_token: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SurveyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None
