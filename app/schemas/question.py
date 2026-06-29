from pydantic import BaseModel, Field
from typing import Optional
 
 
class QuestionCreate(BaseModel):
    text: str
    type: str  # mcq | rating | text
    is_required: Optional[bool] = False
    position: Optional[int] = 0
    options: Optional[list[str]] = None
 
 
class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    type: Optional[str] = None
    is_required: Optional[bool] = None
    position: Optional[int] = None
    options: Optional[list[str]] = None
 
 
class QuestionResponse(BaseModel):
    id: int
    survey_id: int
    text: str
    type: str
    is_required: bool
    position: int
    options: list[str] = Field(default_factory=list)
 
    class Config:
        from_attributes = True
 
