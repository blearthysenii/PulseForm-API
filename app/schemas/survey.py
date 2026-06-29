from pydantic import BaseModel
from typing import Optional
from datetime import datetime
# create survey


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
    share_token: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True



class SurveyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None

