from pydantic import BaseModel
from typing import Optional, List


class QuestionCreate(BaseModel):
    text: str
    type: str  # single_choice | multiple_choice | mcq | rating | text
    is_required: Optional[bool] = False
    position: Optional[int] = 0
    options: Optional[List[str]] = []


class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    type: Optional[str] = None
    is_required: Optional[bool] = None
    position: Optional[int] = None
    options: Optional[List[str]] = None


class QuestionResponse(BaseModel):
    id: int
    survey_id: int
    text: str
    type: str
    is_required: bool
    position: int
    options: List[str] = []

    class Config:
        from_attributes = True
