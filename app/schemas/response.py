from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
 
 
class AnswerSubmit(BaseModel):
    question_id: int
    value_text: Optional[str] = None
    value_number: Optional[int] = None
    option_id: Optional[int] = None
 
 
class ResponseSubmit(BaseModel):
    answers: List[AnswerSubmit]
    session_id: Optional[str] = None
 
 
class AnswerResponse(BaseModel):
    id: int
    question_id: int
    value_text: Optional[str] = None
    value_number: Optional[int] = None
    option_id: Optional[int] = None
 
    class Config:
        from_attributes = True
 
 
class ResponseResponse(BaseModel):
    id: int
    survey_id: int
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    answers: List[AnswerResponse] = []
 
    class Config:
        from_attributes = True
 