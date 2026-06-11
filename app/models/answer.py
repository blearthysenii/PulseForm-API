from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database.db import Base


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    response_id = Column(Integer, ForeignKey(
        "responses.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey(
        "questions.id", ondelete="CASCADE"), nullable=False)
    option_id = Column(Integer, ForeignKey(
        "question_options.id", ondelete="SET NULL"), nullable=True)

    value_text = Column(Text, nullable=True)
    value_number = Column(Integer, nullable=True)

    response = relationship("Response", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    option = relationship("QuestionOption", back_populates="answers")
