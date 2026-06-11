from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database.db import Base


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey(
        "surveys.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="SET NULL"), nullable=True)

    session_id = Column(String(255), nullable=True)
    submitted_at = Column(DateTime, server_default=func.now())

    survey = relationship("Survey", back_populates="responses")
    user = relationship("User", back_populates="responses")
    answers = relationship(
        "Answer", back_populates="response", cascade="all, delete-orphan")
