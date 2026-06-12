from pydantic import BaseModel
from typing import Optional


class SurveyCreate(BaseModel):
    title: str
    description: Optional[str] = None