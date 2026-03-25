import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-backend-env")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


def _pbkdf2(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return base64.b64encode(digest).decode("utf-8")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    encoded_salt = base64.b64encode(salt).decode("utf-8")
    encoded_hash = _pbkdf2(password, salt)
    return f"{encoded_salt}${encoded_hash}"


def verify_password(password: str, stored_password: str) -> bool:
    try:
        encoded_salt, encoded_hash = stored_password.split("$", 1)
        salt = base64.b64decode(encoded_salt.encode("utf-8"))
    except ValueError:
        return False

    password_hash = _pbkdf2(password, salt)
    return hmac.compare_digest(password_hash, encoded_hash)


def serialize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "department": user.get("department"),
    }


def create_access_token(user: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["email"],
        "role": user["role"],
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    from db import users_col

    user = users_col.find_one({"email": email.lower()})
    if not user or not verify_password(password, user["password"]):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    from db import users_col

    payload = decode_access_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject",
        )

    user = users_col.find_one({"email": email.lower()})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
