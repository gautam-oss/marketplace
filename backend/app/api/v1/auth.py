from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.crud.user import create_user, get_user_by_email, get_user_by_id, update_user
from app.core.deps import get_current_active_user
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 60


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Register a new buyer account")
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await create_user(db, data, role="buyer")
    payload = {"sub": str(user.id), "role": user.role}
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
    )


@router.post("/login", response_model=TokenResponse, summary="Login and get access + refresh tokens")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login_attempts:{client_ip}"
    attempts = await redis.incr(rate_key)
    if attempts == 1:
        await redis.expire(rate_key, _LOGIN_WINDOW_SECONDS)
    if attempts > _MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts. Try again later.")
    user = await get_user_by_email(db, data.email)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    await redis.delete(rate_key)
    payload = {"sub": str(user.id), "role": user.role}
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
    )


@router.post("/refresh", response_model=TokenResponse, summary="Exchange refresh token for new access token")
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    import uuid as _uuid
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = await get_user_by_id(db, _uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    new_payload = {"sub": str(user.id), "role": user.role}
    return TokenResponse(
        access_token=create_access_token(new_payload),
        refresh_token=create_refresh_token(new_payload),
    )


@router.post("/logout", response_model=dict, summary="Logout (client should discard tokens)")
async def logout(current_user=Depends(get_current_active_user)):
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user")
async def get_me(current_user=Depends(get_current_active_user)):
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Update current user's profile")
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await update_user(db, current_user, data)
