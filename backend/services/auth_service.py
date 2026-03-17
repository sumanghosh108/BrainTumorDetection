"""Firebase Authentication service and FastAPI dependency."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

from backend.utils.logger import get_logger

if TYPE_CHECKING:
    from fastapi import Request

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Firebase initialisation (once per process)
# ---------------------------------------------------------------------------

_FIREBASE_CRED_PATH = os.getenv("FIREBASE_CREDENTIALS", "firebase-credentials.json")

if not firebase_admin._apps:  # noqa: SLF001
    cred = credentials.Certificate(_FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Raised when token verification fails."""

    def __init__(self, detail: str, status_code: int = 401) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


async def verify_firebase_token(token: str) -> str:
    """Verify a Firebase ID token and return the ``uid``.

    Raises:
        AuthError: If the token is invalid or expired.
    """
    try:
        decoded = firebase_auth.verify_id_token(token, check_revoked=True)
    except firebase_auth.RevokedIdTokenError:
        raise AuthError("Token has been revoked", 401)
    except firebase_auth.ExpiredIdTokenError:
        raise AuthError("Token has expired", 401)
    except Exception as exc:
        logger.warning("firebase_token_invalid", error=str(exc))
        raise AuthError("Invalid authentication token", 401) from exc

    uid: str = decoded["uid"]
    return uid


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_current_user(request: Request) -> str:
    """Extract and verify the Firebase bearer token from the request.

    Usage::

        @router.get("/protected")
        async def protected(user_id: str = Depends(get_current_user)):
            ...

    Returns:
        The Firebase ``uid`` of the authenticated user.
    """
    from fastapi import HTTPException

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        user_id = await verify_firebase_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return user_id
