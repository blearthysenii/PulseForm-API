from sqlalchemy import Column, Integer, String, Boolean, ForeignKey

from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # mcq | rating | text
    is_required = Column(Boolean, default=False)
    position = Column(Integer, default=0)