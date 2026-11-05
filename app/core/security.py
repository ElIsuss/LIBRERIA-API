from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Response
from pydantic import AfterValidator

from app.core.config import settings

_bcrypt_semaphore: asyncio.Semaphore | None = None


def get_bcrypt_semaphore() -> asyncio.Semaphore:
    global _bcrypt_semaphore
    if _bcrypt_semaphore is None:
        _bcrypt_semaphore = asyncio.Semaphore(settings.bcrypt_max_concurrency)
    return _bcrypt_semaphore


def validar_longitud_password_bytes(v: str) -> str:
    if not v:
        raise ValueError("La contraseña no puede estar vacía")
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar los 72 bytes en UTF-8")
    return v


PasswordStr = Annotated[str, AfterValidator(validar_longitud_password_bytes)]


async def hash_password(password: str) -> str:
    """Calcula el hash de la contraseña usando bcrypt fuera del event loop y limitado por semáforo."""
    async with get_bcrypt_semaphore():
        return await asyncio.to_thread(
            lambda: bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(rounds=settings.bcrypt_rounds),
            ).decode("utf-8")
        )


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash usando bcrypt."""
    try:
        async with get_bcrypt_semaphore():
            return await asyncio.to_thread(
                lambda: bcrypt.checkpw(
                    plain_password.encode("utf-8"),
                    hashed_password.encode("utf-8"),
                )
            )
    except Exception:
        return False


def create_access_token(
    *,
    subject: str | int,
    roles: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Genera un token JWT firmado conteniendo el sub (ID), exp y lista informativa de roles."""
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(seconds=settings.jwt_expire_seconds)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "roles": roles or [],
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodifica y valida la firma y expiración de un token JWT. Devuelve el payload o None."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.PyJWTError:
        return None


def set_auth_cookie(response: Response, token: str) -> None:
    """Configura la cookie HttpOnly access_token en la respuesta HTTP."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_expire_seconds,
        secure=settings.cookie_secure,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Elimina la cookie access_token expirándola."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
