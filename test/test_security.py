import asyncio
import sys
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import Response
from pydantic import BaseModel, ValidationError

from app.core.security import (
    PasswordStr,
    clear_auth_cookie,
    create_access_token,
    decode_access_token,
    hash_password,
    set_auth_cookie,
    verify_password,
)


class DummySchema(BaseModel):
    password: PasswordStr


async def run_tests():
    print("Testing PasswordStr validator...")
    # 72 bytes OK
    p72 = "x" * 72
    assert DummySchema(password=p72).password == p72, "72 bytes failed"

    # 73 bytes FAILS
    try:
        DummySchema(password="x" * 73)
        assert False, "73 bytes should have failed"
    except ValidationError:
        pass

    # Empty FAILS
    try:
        DummySchema(password="")
        assert False, "empty password should have failed"
    except ValidationError:
        pass

    # Multibyte UTF-8 (ñ is 2 bytes)
    p_36_ñ = "ñ" * 36
    assert len(p_36_ñ.encode("utf-8")) == 72
    assert DummySchema(password=p_36_ñ).password == p_36_ñ

    try:
        DummySchema(password="ñ" * 37)
        assert False, "74 bytes UTF-8 should have failed"
    except ValidationError:
        pass

    print("Testing hash_password and verify_password...")
    plain = "MiClaveSecreta123!"
    hashed = await hash_password(plain)
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$"), f"Invalid hash: {hashed}"
    assert await verify_password(plain, hashed) is True, "Password verification failed"
    assert await verify_password("ClaveErronea", hashed) is False, "Wrong password accepted"

    print("Testing JWT token creation and decoding...")
    token = create_access_token(subject=42, roles=["ADMIN", "CLIENTE"])
    payload = decode_access_token(token)
    assert payload is not None, "Decoded payload is None"
    assert payload["sub"] == "42", f"Wrong sub: {payload['sub']}"
    assert payload["roles"] == ["ADMIN", "CLIENTE"], f"Wrong roles: {payload['roles']}"

    # Expired token test
    expired_token = create_access_token(
        subject=10,
        roles=["VENDEDOR"],
        expires_delta=timedelta(seconds=-10),
    )
    assert decode_access_token(expired_token) is None, "Expired token should return None"

    # Invalid token test
    assert decode_access_token("token.invalido.falso") is None, "Invalid token should return None"

    print("Testing cookie helpers...")
    res = Response()
    set_auth_cookie(res, token)
    cookie_header = res.headers.get("set-cookie")
    assert cookie_header is not None, "Set-Cookie header missing"
    assert "access_token=" in cookie_header, "access_token cookie missing"
    assert "HttpOnly" in cookie_header or "httponly" in cookie_header, "HttpOnly flag missing"
    assert "SameSite=lax" in cookie_header or "samesite=lax" in cookie_header, "SameSite flag missing"

    res_logout = Response()
    clear_auth_cookie(res_logout)
    clear_header = res_logout.headers.get("set-cookie")
    assert clear_header is not None, "Clear cookie header missing"
    assert 'access_token=""' in clear_header or 'access_token=;' in clear_header or 'Max-Age=0' in clear_header, "Cookie not cleared"

    print("ALL SECURITY TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_tests())
