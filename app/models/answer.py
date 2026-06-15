from sqlalchemy import Column, Integer, Text, ForeignKey

from app.database import Base


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("responses.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    value_text = Column(Text, nullable=True)
    value_number = Column(Integer, nullable=True)
    option_id = Column(Integer, ForeignKey("question_options.id", ondelete="SET NULL"), nullable=True)