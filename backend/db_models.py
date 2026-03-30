from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AnalysisHistory(Base):
    __tablename__ = "analysis_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, index=True)
    trade_style = Column(String)
    signal = Column(String)
    total_score = Column(Float, nullable=True)
    max_score = Column(Float)
    analysis_mode = Column(String)
    result_json = Column(String)  # JSON string of the full AnalysisResult
    created_at = Column(DateTime(timezone=True), server_default=func.now())
