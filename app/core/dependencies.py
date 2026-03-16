from dataclasses import dataclass
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.redis import get_redis
from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass
class PaginationParams:
    limit: int = Query(default=20, ge=1, le=100)
    offset: int = Query(default=0, ge=0)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> "User":  # type: ignore[name-defined]  # avoids circular import
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise UnauthorizedError("Invalid token")
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    # Import here to avoid circular dependency at module load time
    from app.modules.auth.repository import UserRepository
    from app.modules.auth.models import User

    user = await UserRepository().get_by_id(db, UUID(user_id))
    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("Account is inactive")
    return user
