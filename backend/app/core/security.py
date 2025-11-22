from datetime import datetime
from typing import Optional
import uuid
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import DBAPIError, OperationalError

from app.core.config import settings
from app.db.session import get_session
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify Supabase JWT token and extract payload.
    
    This function validates tokens issued by Supabase Auth using the JWT secret.
    Supabase uses HS256 algorithm and includes 'authenticated' in the audience.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],  # Supabase uses HS256
            audience="authenticated"  # Supabase JWT audience
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT validation failed: {str(e)}, token: {token[:20] if token else 'None'}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    payload: dict = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_session)
) -> UserProfile:
    """
    Get or create user profile from Supabase JWT payload.
    
    Supabase JWT contains:
    - 'sub': User UUID (matches auth.users.id)
    - 'email': User email
    - 'user_metadata': Additional user data from Supabase
    """
    user_id_str = payload.get("sub")  # Supabase uses 'sub' for user ID
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload: missing sub")
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")

    try:
        # Check if user exists in our DB
        result = await session.execute(select(UserProfile).where(UserProfile.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            # Auto-create profile if it doesn't exist (first login)
            # This syncs with Supabase auth.users table
            email = payload.get("email")
            user_metadata = payload.get("user_metadata", {})
            
            user = UserProfile(
                id=user_id,  # Matches Supabase auth.users.id
                email=email,
                display_name=user_metadata.get("full_name") or user_metadata.get("name"),
                avatar_url=user_metadata.get("avatar_url")
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user
    except (DBAPIError, OperationalError) as e:
        error_str = str(e)
        logger.warning(f"Database connection error in get_current_user (possibly during shutdown): {error_str}")
        
        # Check for connection-related errors
        if "ConnectionDoesNotExistError" in error_str or "connection was closed" in error_str.lower():
            # Database connection was closed mid-operation (likely during server shutdown)
            # Return a 503 Service Unavailable error
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again in a moment.",
            )
        else:
            # Other database errors
            logger.error(f"Database error in get_current_user: {error_str}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error. Please try again.",
            )
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request.",
        )
