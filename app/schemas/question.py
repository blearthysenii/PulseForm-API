from pydantic import BaseModel
from typing import Optional
 
 
class QuestionCreate(BaseModel):
    text: str
    type: str  # mcq | rating | text
    is_required: Optional[bool] = False
    position: Optional[int] = 0
 
 
class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    type: Optional[str] = None
    is_required: Optional[bool] = None
    position: Optional[int] = None
 
 
class QuestionResponse(BaseModel):
    id: int
    survey_id: int
    text: str
    type: str
    is_required: bool
    position: int
 
    class Config:
        from_attributes = True
 