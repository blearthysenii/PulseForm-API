from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)

    survey_id = Column(Integer, ForeignKey("surveys.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    answers = Column(Text, nullable=False)  # JSON string of all answers

    created_at = Column(DateTime, server_default=func.now())

    survey = relationship("Survey", back_populates="responses")
    user = relationship("User", back_populates="responses")