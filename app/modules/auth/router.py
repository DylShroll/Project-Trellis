import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.redis import get_redis
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.core.config import get_settings
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.modules.auth.service import AuthService

_settings = get_settings()
_COOKIE_MAX_AGE = _settings.access_token_expire_minutes * 60

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(redis: aioredis.Redis) -> AuthService:
    return AuthService(UserRepository(), redis)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    _, tokens = await _service(redis).register(db, data)
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    _, tokens = await _service(redis).login(db, data.email, data.password)
    return tokens


@router.post("/login/web", include_in_schema=False)
async def login_web(
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> Response:
    from app.core.exceptions import UnauthorizedError
    try:
        _, tokens = await _service(redis).login(db, email, password)
    except UnauthorizedError:
        return HTMLResponse('<span class="text-warm-clay text-sm">Invalid email or password.</span>')
    response = Response(status_code=200, headers={"HX-Redirect": "/"})
    response.set_cookie(
        "access_token", tokens.access_token,
        max_age=_COOKIE_MAX_AGE, httponly=True, samesite="lax",
    )
    return response


@router.post("/register/web", include_in_schema=False)
async def register_web(
    display_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> Response:
    from app.core.exceptions import ConflictError
    try:
        _, tokens = await _service(redis).register(db, UserCreate(
            display_name=display_name, email=email, password=password
        ))
    except ConflictError:
        return HTMLResponse('<span class="text-warm-clay text-sm">An account with this email already exists.</span>')
    except Exception:
        return HTMLResponse('<span class="text-warm-clay text-sm">Something went wrong. Please try again.</span>')
    response = Response(status_code=200, headers={"HX-Redirect": "/"})
    response.set_cookie(
        "access_token", tokens.access_token,
        max_age=_COOKIE_MAX_AGE, httponly=True, samesite="lax",
    )
    return response


@router.post("/login/form", response_model=TokenResponse, include_in_schema=False)
async def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """OAuth2 password flow for Swagger UI compatibility."""
    _, tokens = await _service(redis).login(db, form.username, form.password)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    return await _service(redis).refresh(db, data.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    await _service(redis).logout(current_user)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    return await _service(redis).update_profile(db, current_user, data)
