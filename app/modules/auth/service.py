import hashlib
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    refresh_token_redis_key,
    verify_password,
)
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import TokenResponse, UserCreate, UserUpdate

settings = get_settings()


class AuthService:
    def __init__(self, user_repo: UserRepository, redis: aioredis.Redis) -> None:
        self.user_repo = user_repo
        self.redis = redis

    async def register(self, db: AsyncSession, data: UserCreate) -> tuple[User, TokenResponse]:
        existing = await self.user_repo.get_by_email(db, data.email)
        if existing:
            raise ConflictError("An account with this email already exists")
        hashed = hash_password(data.password)
        user = await self.user_repo.create(db, data, hashed)
        tokens = await self._issue_tokens(user)
        return user, tokens

    async def login(
        self, db: AsyncSession, email: str, password: str
    ) -> tuple[User, TokenResponse]:
        user = await self.user_repo.get_by_email(db, email)
        if not user or not user.hashed_password:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        tokens = await self._issue_tokens(user)
        return user, tokens

    async def refresh(self, db: AsyncSession, refresh_token: str) -> TokenResponse:
        # Find the user_id by scanning for this token hash across all users
        # (we encode user_id in the token to avoid a full scan)
        # Token format: {user_id}:{random} — we embed user_id at generation time
        # For simplicity in v1, we store user_id in the token value in Redis
        # Redis key: refresh:{user_id}:{token_hash} with value = ""
        # We can't look up by hash alone without user_id, so we store a reverse lookup too
        reverse_key = f"refresh_reverse:{_hash_token(refresh_token)}"
        user_id_str = await self.redis.get(reverse_key)
        if not user_id_str:
            raise UnauthorizedError("Invalid or expired refresh token")

        redis_key = refresh_token_redis_key(user_id_str, _hash_token(refresh_token))
        exists = await self.redis.exists(redis_key)
        if not exists:
            raise UnauthorizedError("Invalid or expired refresh token")

        user = await self.user_repo.get_by_id(db, UUID(user_id_str))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        # Rotate: delete old token, issue new pair
        await self.redis.delete(redis_key, reverse_key)
        return await self._issue_tokens(user)

    async def logout(self, user: User) -> None:
        # Delete all refresh tokens for this user
        pattern = f"refresh:{user.id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                # Also delete reverse lookups
                pipe = self.redis.pipeline()
                for key in keys:
                    pipe.delete(key)
                await pipe.execute()
            if cursor == 0:
                break

    async def update_profile(
        self, db: AsyncSession, user: User, data: UserUpdate
    ) -> User:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return user
        return await self.user_repo.update(db, user, **updates)

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(str(user.id))
        refresh_token = generate_refresh_token()
        token_hash = _hash_token(refresh_token)
        ttl = settings.refresh_token_expire_days * 86400

        redis_key = refresh_token_redis_key(str(user.id), token_hash)
        reverse_key = f"refresh_reverse:{token_hash}"

        pipe = self.redis.pipeline()
        pipe.set(redis_key, "", ex=ttl)
        pipe.set(reverse_key, str(user.id), ex=ttl)
        await pipe.execute()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
