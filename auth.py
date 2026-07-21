from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import jwt
from jwt.exceptions import (
    InvalidTokenError,
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidSignatureError,
    MissingRequiredClaimError,
    DecodeError,
)
import os
from sqlalchemy import text
from sqlmodel import Session
from paper.db import get_db

ALGORITHM = "HS256"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "quant-run-secret-jwt-key-change-in-production-2026-secure")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def _is_token_revoked(token_str: str, session: Session) -> bool:
    try:
        result = session.execute(
            text("SELECT is_active FROM dashboard_apitoken WHERE token = :token LIMIT 1"),
            {"token": token_str}
        )
        row = result.first()
        if row is None:
            return True
        return not bool(row[0])
    except Exception:
        return False


def decode_token(token: str, session: Session) -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "user_id"]},
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except InvalidAlgorithmError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid algorithm")
    except InvalidSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
    except MissingRequiredClaimError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing required claims")
    except DecodeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if _is_token_revoked(token, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    return payload


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_db),
) -> dict:
    payload = decode_token(token, session)
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return {"user_id": user_id, "username": payload.get("username")}
