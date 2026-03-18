import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# deprecated="auto" ensures old hash schemes are transparently re-hashed on next login
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    # "sub" identifies the principal; "iat" lets receivers detect token age independently of "exp"
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(UTC)}
    if extra:
        # Callers can embed role or scope claims without modifying this function
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT. Raises JWTError on any failure."""
    # algorithms is a list so the setting can be rotated without a breaking change
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def generate_refresh_token() -> str:
    # 64 bytes of URL-safe randomness gives ~512 bits of entropy — far beyond brute-force range
    return secrets.token_urlsafe(64)


def refresh_token_redis_key(user_id: str, token_hash: str) -> str:
    # Namespaced key allows all refresh tokens for a user to be scanned and revoked at once
    return f"refresh:{user_id}:{token_hash}"
