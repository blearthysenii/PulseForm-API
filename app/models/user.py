from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="creator", nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    surveys = relationship("Survey", back_populates="creator", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="user")