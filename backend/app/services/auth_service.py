"""
Authentication Service Module.

Handles Firebase token verification and internal JWT creation/decoding.
"""

from datetime import datetime, timedelta, timezone

import firebase_admin
import jwt
from firebase_admin import auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.config import settings
from app.db import get_async_session

# This scheme will be used in the API endpoints to extract the token from the
# "Authorization: Bearer <token>" header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/firebase_login")


def initialize_firebase():
    """
    Initializes the Firebase Admin SDK if it hasn't been already.
    Uses the credentials path from the application settings.
    """
    try:
        # The `get_app` call will raise a ValueError if the app is not initialized.
        firebase_admin.get_app()
    except ValueError:
        try:
            cred = credentials.Certificate(settings.FIREBASE_CRED_PATH)
            firebase_admin.initialize_app(cred)
        except FileNotFoundError:
            # This is a critical error, the application cannot function without it.
            # In a production environment, you might want to log this and exit.
            print(
                f"ERROR: Firebase credentials file not found at '{settings.FIREBASE_CRED_PATH}'"
            )
            # For development, we can allow the app to run, but auth will fail.
            # In production, you might `raise` here.


def verify_firebase_token(id_token: str) -> dict:
    """
    Verifies a Firebase ID token and returns the decoded claims.

    Raises:
        HTTPException: If the token is invalid, expired, or revoked.
    """
    if not firebase_admin._apps:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase Admin SDK not initialized. Check server configuration.",
        )
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase token has expired"
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase token"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during token verification.",
        )


def create_access_token(data: dict) -> str:
    """
    Creates a new JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_session)
) -> models.User:
    """
    Dependency to get the current user from a backend-issued JWT.
    This is used to protect endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (jwt.PyJWTError, ValidationError):
        raise credentials_exception

    user = await crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user