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
        # Return the same error for unknown email and wrong password to prevent email enumeration
        if not user or not user.hashed_password:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        tokens = await self._issue_tokens(user)
        return user, tokens

    async def refresh(self, db: AsyncSession, refresh_token: str) -> TokenResponse:
        # Reverse-lookup: the client sends the raw token; we hash it to find the Redis key.
        # A second "refresh_reverse" key maps hash → user_id so we don't need to scan all users.
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

        # Token rotation: delete the used token before issuing a fresh pair to prevent reuse
        await self.redis.delete(redis_key, reverse_key)
        return await self._issue_tokens(user)

    async def logout(self, user: User) -> None:
        # Scan-and-delete all refresh tokens for this user so every device is signed out
        pattern = f"refresh:{user.id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
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
            return user  # nothing to write; skip the DB round-trip
        return await self.user_repo.update(db, user, **updates)

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(str(user.id))
        refresh_token = generate_refresh_token()
        token_hash = _hash_token(refresh_token)
        ttl = settings.refresh_token_expire_days * 86400

        redis_key = refresh_token_redis_key(str(user.id), token_hash)
        # Reverse lookup key shares the same TTL so both expire together
        reverse_key = f"refresh_reverse:{token_hash}"

        # Pipeline ensures both keys are written atomically in one round-trip
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
    # SHA-256 so the raw token is never stored in Redis — a stolen Redis dump can't be replayed
    return hashlib.sha256(token.encode()).hexdigest()
