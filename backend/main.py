import logging
import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from models import AnalyzeRequest, AnalysisResult, UserCreate, UserLogin, UserOut, Token, HistoryCreate, HistoryOut
from analyzer import analyze
from database import engine, get_db
import db_models
from auth_utils import get_password_hash, verify_password, create_access_token, decode_access_token

# DB初期化
db_models.Base.metadata.create_all(bind=engine)

# Bearerトークンの取得設定
auth_scheme = HTTPBearer()

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("stock-analyzer")

# デプロイ環境向けの設定
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

app = FastAPI(title="Stock Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(db_models.User).filter(db_models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="ユーザー名が既に存在します")
    
    hashed_pwd = get_password_hash(user.password)
    new_user = db_models.User(
        username=user.username,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/api/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(db_models.User).filter(db_models.User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="ユーザー名またはパスワードが正しくありません")
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        return None
    username = payload.get("sub")
    if username is None:
        return None
    user = db.query(db_models.User).filter(db_models.User.username == username).first()
    return user


@app.get("/api/me", response_model=UserOut)
def read_me(current_user: Optional[db_models.User] = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="認証が必要です")
    return current_user


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze_endpoint(request: AnalyzeRequest):
    return analyze(request)


@app.post("/api/history", response_model=HistoryOut)
def save_history(history: HistoryCreate, current_user: Optional[db_models.User] = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="認証が必要です")
    
    new_history = db_models.AnalysisHistory(
        user_id=current_user.id,
        symbol=history.symbol,
        trade_style=history.trade_style,
        signal=history.signal,
        total_score=history.total_score,
        max_score=history.max_score,
        analysis_mode=history.analysis_mode,
        result_json=history.result_json
    )
    db.add(new_history)
    db.commit()
    db.refresh(new_history)
    return new_history


@app.get("/api/history", response_model=List[HistoryOut])
def get_histories(
    symbol: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    current_user: Optional[db_models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="認証が必要です")
    
    query = db.query(db_models.AnalysisHistory).filter(db_models.AnalysisHistory.user_id == current_user.id)
    
    if symbol:
        query = query.filter(db_models.AnalysisHistory.symbol.ilike(f"%{symbol}%"))
    
    # ソート設定
    attr = getattr(db_models.AnalysisHistory, sort_by, db_models.AnalysisHistory.created_at)
    if order == "desc":
        query = query.order_by(attr.desc())
    else:
        query = query.order_by(attr.asc())
    
    return query.all()
