"""
firefly-scheduler · 安全工具
JWT 签发/验证 + 密码哈希
"""
import time
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.config import settings


# ── 密码哈希 ──────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """明文密码 → bcrypt 哈希"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配"""
    return pwd_context.verify(plain, hashed)


# ── JWT ────────────────────────────────
def create_access_token(user_id: str, username: str) -> str:
    """签发 access_token（默认 24 小时）"""
    payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.jwt_access_expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    """签发 refresh_token（默认 7 天）"""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.jwt_refresh_expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """解码并验证 JWT，失败抛 401"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
