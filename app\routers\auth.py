"""
firefly-scheduler · Router · Auth
注册 / 登录 / Token 刷新
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册，自动签发 token"""
    # 检查用户名是否已存在
    existing = await db.execute(
        User.__table__.select().where(User.username == body.username)
    )
    if existing.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        id=str(uuid.uuid4()),
        username=body.username,
        password_hash=hash_password(body.password),
        total_contribution=0,
    )
    db.add(user)
    await db.flush()

    access = create_access_token(user.id, user.username)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        username=user.username,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(
        User.__table__.select().where(User.username == body.username)
    )
    user = result.first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token(user.id, user.username)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        username=user.username,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """用 refresh_token 换取新的 access_token"""
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload["sub"]
    result = await db.execute(
        User.__table__.select().where(User.id == user_id)
    )
    user = result.first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    access = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=access,
        refresh_token=body.refresh_token,  # 不刷新 refresh
        user_id=user.id,
        username=user.username,
    )
