"""
API endpoints for user authentication.

This module contains endpoints for user registration and login.
For now, it includes a placeholder for Firebase login and a basic
user creation endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db import get_async_session

router = APIRouter()


@router.post("/firebase_login", response_model=schemas.User)
async def firebase_login(
    login_data: schemas.UserCreate, db: AsyncSession = Depends(get_async_session)
):
    """
    Handles user login/registration via Firebase ID token.

    1.  (TODO) Verify the Firebase ID token.
    2.  Check if a user with the Firebase UID already exists.
    3.  If not, check if the student_id is already taken.
    4.  If the user is new, create them in the database.
    5.  (TODO) Return a JWT session token.
    """
    # In a real application, you would first verify the idToken with Firebase Admin SDK
    # to get the firebase_uid and other details. For now, we'll trust the input.

    # Check if user already exists by firebase_uid
    db_user = await crud.get_user_by_firebase_uid(db, firebase_uid=login_data.firebase_uid)
    if db_user:
        # TODO: Update last_login timestamp
        return db_user

    # If user does not exist, we are creating a new one.
    # Check if the student_id is already registered.
    existing_student = await crud.get_user_by_student_id(
        db, student_id=login_data.student_id
    )
    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this student ID already exists.",
        )

    # Create the new user
    try:
        new_user = await crud.create_user(db=db, user=login_data)
        return new_user
    except Exception:
        # This could catch database integrity errors, e.g., if a unique constraint is violated
        # due to a race condition.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user. An unexpected error occurred.",
        )