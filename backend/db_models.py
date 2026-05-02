import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Uuid
from sqlalchemy.sql import func
from database import Base

from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # リレーションシップとカスケード削除の設定
    histories = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")

class AnalysisHistory(Base):
    __tablename__ = "analysis_histories"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"))
    
    # 逆方向のリレーションシップ
    user = relationship("User", back_populates="histories")
    symbol = Column(String, index=True)
    symbol_name = Column(String, index=True)
    trade_style = Column(String)
    signal = Column(String)
    total_score = Column(Float, nullable=True)
    max_score = Column(Float)
    analysis_mode = Column(String)
    result_json = Column(String)  # JSON string of the full AnalysisResult
    created_at = Column(DateTime(timezone=True), server_default=func.now())
