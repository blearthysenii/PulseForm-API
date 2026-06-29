from typing import List, Literal, Optional

from pydantic import BaseModel


class SummaryKpis(BaseModel):
    totalResponses: int
    totalResponsesDeltaPct: Optional[int] = None
    completionRatePct: Optional[int] = None
    completionRateDeltaPct: Optional[int] = None
    nps: Optional[int] = None
    npsDelta: Optional[int] = None


class SurveySummaryResponse(BaseModel):
    id: str
    title: str
    status: Literal["draft", "live"]
    openedAt: Optional[str] = None
    closesAt: Optional[str] = None
    kpis: SummaryKpis


class TimePoint(BaseModel):
    date: str
    count: int


class ResponsesOverTimeResponse(BaseModel):
    range: str
    bucket: Literal["day", "week"]
    points: List[TimePoint]


class NpsSegment(BaseModel):
    count: int
    pct: int


class NpsSegments(BaseModel):
    promoters: NpsSegment
    passives: NpsSegment
    detractors: NpsSegment


class NpsResponse(BaseModel):
    score: int
    total: int
    segments: NpsSegments


class ChoiceOption(BaseModel):
    label: str
    count: int
    pct: int


class RatingDistributionPoint(BaseModel):
    value: int
    pct: int


class ChoiceQuestionBreakdown(BaseModel):
    id: str
    order: int
    label: str
    type: Literal["mcq", "single_choice", "multiple_choice"]
    totalAnswers: int
    options: List[ChoiceOption]


class RatingQuestionBreakdown(BaseModel):
    id: str
    order: int
    label: str
    type: Literal["rating"]
    totalAnswers: int
    scaleMax: int
    average: Optional[float] = None
    distribution: List[RatingDistributionPoint]


class TextQuestionBreakdown(BaseModel):
    id: str
    order: int
    label: str
    type: Literal["text"]
    totalAnswers: int
    textAnswers: List[str]


QuestionBreakdown = ChoiceQuestionBreakdown | RatingQuestionBreakdown | TextQuestionBreakdown


class QuestionsResponse(BaseModel):
    questions: List[QuestionBreakdown]


class Respondent(BaseModel):
    name: str
    initials: str
    avatarColor: str


class FeedItem(BaseModel):
    id: str
    respondent: Respondent
    submittedAt: Optional[str] = None
    ratingScore: Optional[int] = None
    comment: Optional[str] = None


class FeedResponse(BaseModel):
    items: List[FeedItem]
    nextCursor: Optional[str] = None
