"""Security utilities for authentication and authorization"""

from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated=["bcrypt"],
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    verified = pwd_context.verify(plain_password, hashed_password)
    if not isinstance(verified, bool):
        raise TypeError("Password verifier returned a non-boolean result")
    return verified


def get_password_hash(password: str) -> str:
    """Hash a password"""
    password_hash = pwd_context.hash(password)
    if not isinstance(password_hash, str):
        raise TypeError("Password hasher returned a non-string result")
    return password_hash


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    if not isinstance(encoded_jwt, str):
        raise TypeError("JWT encoder returned a non-string result")
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """Decode and verify a JWT access token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if not isinstance(payload, dict):
            return None
        return payload
    except JWTError:
        return None
