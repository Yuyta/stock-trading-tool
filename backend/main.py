import logging
import os
import uuid
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List

from models import AnalyzeRequest, AnalysisResult, UserCreate, UserLogin, UserOut, Token, HistoryCreate, HistoryOut, SearchResponse
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
CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS", "")
if CORS_ORIGINS_RAW:
    ALLOWED_ORIGINS = CORS_ORIGINS_RAW.split(",")
else:
    # 開発環境向けのデフォルト設定
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

app = FastAPI(title="Stock Analyzer API", version="1.0.0")

# --- セキュリティミドルウェア: セキュリティヘッダの追加 ---
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; object-src 'none';"
    return response

# --- セキュリティミドルウェア: 簡易レート制限 ---
# 注意: 本番環境で大規模なトラフィックがある場合は Redis 等を使用した本格的な実装を推奨
request_counts = {}

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    client_ip = request.client.host
    import time
    now = time.time()
    
    # 60秒間に100リクエストを制限
    if client_ip not in request_counts:
        request_counts[client_ip] = []
    
    # 古いリクエストを削除
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < 60]
    
    if len(request_counts[client_ip]) > 100:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})
    
    request_counts[client_ip].append(now)
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://stock-trading-tool-.*\.vercel\.app",
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
        symbol_name=history.symbol_name,
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
        query = query.filter(
            or_(
                db_models.AnalysisHistory.symbol.ilike(f"%{symbol}%"),
                db_models.AnalysisHistory.symbol_name.ilike(f"%{symbol}%")
            )
        )
    
    # ソート設定
    attr = getattr(db_models.AnalysisHistory, sort_by, db_models.AnalysisHistory.created_at)
    if order == "desc":
        query = query.order_by(attr.desc())
    else:
        query = query.order_by(attr.asc())
    
    return query.all()


@app.delete("/api/history/{history_id}")
def delete_history(history_id: uuid.UUID, current_user: Optional[db_models.User] = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="認証が必要です")
    
    db_history = db.query(db_models.AnalysisHistory).filter(
        db_models.AnalysisHistory.id == history_id,
        db_models.AnalysisHistory.user_id == current_user.id
    ).first()
    
    if not db_history:
        raise HTTPException(status_code=404, detail="履歴が見つかりません")
    
    db.delete(db_history)
    db.commit()
    return {"status": "success", "message": "履歴を削除しました"}


@app.delete("/api/user")
def delete_user(current_user: Optional[db_models.User] = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="認証が必要です")
    
    logger.info(f"User withdrawal request: {current_user.username}")
    
    # 関連データは db_models.py の cascade="all, delete-orphan" により自動削除されます
    db.delete(current_user)
    db.commit()
    
    logger.info(f"User deleted: {current_user.username}")
    return {"status": "success", "message": "ユーザーアカウントと関連データを全て削除しました"}


@app.get("/api/search", response_model=SearchResponse)
def search_ticker(q: str):
    logger.info(f"Search request: q='{q}'")
    if not q:
        return {"results": []}

    import yfinance as yf
    
    results = []
    # 銘柄名やコードで検索
    try:
        search = yf.Search(q, max_results=8)
        raw_results = getattr(search, 'quotes', [])
        
        for r in raw_results:
            symbol = r.get("symbol", "")
            name = r.get("longname") or r.get("shortname") or symbol
            exchange = r.get("exchange", "")
            quote_type = r.get("quoteType", "")
            
            # 日本株判定用の情報を一時的に保持
            exch_disp = r.get("exchDisp", "").lower()
            
            results.append({
                "symbol": symbol,
                "name": name,
                "exchange": exchange,
                "type": quote_type,
                "_is_jp": (
                    symbol.upper().endswith((".T", ".O")) or
                    exchange.upper() in ("JPX", "TYO", "OSA", "TSE") or
                    any(kw in exch_disp for kw in ("tokyo", "osaka", "nagoya", "sapporo", "fukuoka", "jpx"))
                )
            })

        # 日本株を優先的にソート
        results.sort(key=lambda x: x.get("_is_jp", False), reverse=True)
        
        # 不要な内部フラグを削除
        for r in results:
            r.pop("_is_jp", None)

    except Exception as e:
        logger.error(f"yfinance search failed for '{q}': {str(e)}")

    # もし入力が4桁の数字なら、Yahoo!の検索結果に無くても .T を付けて候補に出す
    import re
    if re.match(r"^\d{4}$", q):
        found_jp = any(r["symbol"] == f"{q}.T" for r in results)
        if not found_jp:
            results.insert(0, {
                "symbol": f"{q}.T",
                "name": f"日本株 {q}",
                "exchange": "TSE",
                "type": "EQUITY"
            })

    # 日本語が含まれていて、かつ検索結果が0件の場合、英語名での入力を促すヒントを出す
    is_cjk = bool(re.search(r"[\u3000-\u30ff\u4e00-\u9faf]", q))
    if not results and is_cjk:
        results.append({
            "symbol": "NOTICE",
            "name": "日本語名での検索不可。会社名（英語）や銘柄コードを入力してください。",
            "exchange": "HELP",
            "type": "HINT"
        })

    logger.info(f"Found {len(results)} search results for '{q}'")
    return {"results": results}
