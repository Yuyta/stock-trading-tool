import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

# Secret key for JWT. For production, use environment variables.
SECRET_KEY = os.environ.get("JWT_SECRET")
if not SECRET_KEY:
    # Renderなどのデプロイ環境では必須とする
    if os.environ.get("RENDER") or os.environ.get("VERCEL"):
        raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET environment variable must be set in production.")
    SECRET_KEY = "dev-secret-key-change-this-in-production"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def verify_password(plain_password: str, hashed_password: str):
    # plain_password.encode('utf-8') を使用してバイトに変換する
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str):
    # bcrypt.hashpw はバイトを受け取る
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
