from pydantic import BaseModel, Field
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
    allow_multiple_responses: bool = False
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


class PublicQuestionOptionResponse(BaseModel):
    id: int
    text: str


class PublicQuestionResponse(BaseModel):
    id: int
    text: str
    question_text: str
    type: str
    is_required: bool
    position: int
    options: list[PublicQuestionOptionResponse] = Field(default_factory=list)


class PublicSurveyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    public_slug: str
    questions: list[PublicQuestionResponse] = Field(default_factory=list)


class PublicAnswerCreate(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None
    selected_option_ids: Optional[list[int]] = None
    text_answer: Optional[str] = None
    value_number: Optional[int] = None


class PublicResponseCreate(BaseModel):
    answers: list[PublicAnswerCreate] = Field(default_factory=list)


class PublicResponseCreated(BaseModel):
    id: int
    survey_id: int
    submitted_at: Optional[datetime] = None
    answers_saved: int

    class Config:
        from_attributes = True

