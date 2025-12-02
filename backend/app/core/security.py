from datetime import datetime
from typing import Optional
import uuid
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import DBAPIError, OperationalError, IntegrityError
from sqlalchemy import text

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
        # Check if user exists in our DB by ID
        result = await session.execute(select(UserProfile).where(UserProfile.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            # User doesn't exist by ID - check if they exist by email (re-registration case)
            email = payload.get("email")
            user_metadata = payload.get("user_metadata", {})
            
            if email:
                # Check if user exists with same email but different ID
                result = await session.execute(select(UserProfile).where(UserProfile.email == email))
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # User re-registered with same email but new Supabase ID
                    # Strategy: Create new user profile, update foreign keys, then delete old profile
                    old_user_id = existing_user.id
                    logger.info(f"👤 [SECURITY] User RE-REGISTERED: email={email}, old_id={old_user_id}, new_id={user_id}")
                    logger.info(f"ℹ️  [SECURITY] Account migration detected - will fire CompleteRegistration after migration")
                    
                    try:
                        # Step 1: Create a new user profile with the new ID and a temporary email
                        # We'll use a temporary email to avoid unique constraint violation
                        temp_email = f"{email}.temp.{user_id}"
                        await session.execute(
                            text("""
                                INSERT INTO user_profiles (id, email, display_name, avatar_url, created_at, updated_at)
                                VALUES (:new_id, :temp_email, :display_name, :avatar_url, NOW(), NOW())
                            """),
                            {
                                "new_id": str(user_id),
                                "temp_email": temp_email,
                                "display_name": user_metadata.get("full_name") or user_metadata.get("name") or existing_user.display_name,
                                "avatar_url": user_metadata.get("avatar_url") or existing_user.avatar_url
                            }
                        )
                        logger.debug(f"Created temporary user profile with new ID {user_id}")
                        
                        # Step 2: Update all foreign key references to point to the new ID
                        tables_to_update = [
                            "credit_wallets",
                            "credit_transactions",
                            "api_keys",
                            "audit_logs",
                            "render_jobs",
                            "assets",
                            "subscriptions",
                            "payments"
                        ]
                        
                        for table in tables_to_update:
                            try:
                                # SECURITY: Safe dynamic SQL usage
                                # 'table' is from the hardcoded whitelist above (tables_to_update)
                                # 'new_id' and 'old_id' are passed as bound parameters
                                result = await session.execute(
                                    text(f"UPDATE {table} SET user_id = :new_id WHERE user_id = :old_id"),
                                    {"new_id": str(user_id), "old_id": str(old_user_id)}
                                )
                                if result.rowcount > 0:
                                    logger.debug(f"Updated {result.rowcount} rows in {table} from {old_user_id} to {user_id}")
                            except Exception as e:
                                logger.warning(f"Failed to update {table}: {str(e)}")
                                raise  # Re-raise to trigger rollback
                        
                        # Step 3: Delete the old user profile
                        await session.execute(
                            text("DELETE FROM user_profiles WHERE id = :old_id"),
                            {"old_id": str(old_user_id)}
                        )
                        logger.debug(f"Deleted old user profile {old_user_id}")
                        
                        # Step 4: Update the new user profile's email to the correct email
                        await session.execute(
                            text("UPDATE user_profiles SET email = :email WHERE id = :new_id"),
                            {"email": email, "new_id": str(user_id)}
                        )
                        logger.debug(f"Updated email for new user profile to {email}")
                        
                        # Step 5: Update user metadata if provided
                        if user_metadata.get("full_name") or user_metadata.get("name"):
                            display_name = user_metadata.get("full_name") or user_metadata.get("name")
                            await session.execute(
                                text("UPDATE user_profiles SET display_name = :display_name WHERE id = :user_id"),
                                {"display_name": display_name, "user_id": str(user_id)}
                            )
                        
                        if user_metadata.get("avatar_url"):
                            await session.execute(
                                text("UPDATE user_profiles SET avatar_url = :avatar_url WHERE id = :user_id"),
                                {"avatar_url": user_metadata.get("avatar_url"), "user_id": str(user_id)}
                            )
                        
                        await session.commit()
                        
                        # Refresh to get the updated user
                        result = await session.execute(select(UserProfile).where(UserProfile.id == user_id))
                        user = result.scalar_one()
                        logger.info(f"Successfully migrated user {email} from {old_user_id} to {user_id}")
                        
                        # NOTE: CompleteRegistration event is NOT fired here because:
                        # 1. This code runs during OAuth exchange (get_current_user)
                        # 2. At this point, we don't have access to real browser data (IP, user agent, fbp, fbc)
                        # 3. Frontend will call POST /auth/oauth/complete-registration AFTER OAuth exchange
                        # 4. That endpoint will have access to real browser data for accurate tracking
                        logger.info(f"🎯 [SECURITY] Migrated user detected: {user.email} - CompleteRegistration will be fired from frontend POST request")
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"Failed to migrate user {email} from {old_user_id} to {user_id}: {str(e)}", exc_info=True)
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to update user account. Please contact support.",
                        )
                else:
                    # New user - create profile
                    logger.info(f"🆕 [SECURITY] NEW OAuth user detected: {email} (ID: {user_id})")
                    
                    user = UserProfile(
                        id=user_id,  # Matches Supabase auth.users.id
                        email=email,
                        display_name=user_metadata.get("full_name") or user_metadata.get("name"),
                        avatar_url=user_metadata.get("avatar_url")
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    
                    # NOTE: CompleteRegistration event is NOT fired here because:
                    # 1. This code runs during OAuth exchange (get_current_user)
                    # 2. At this point, we don't have access to real browser data (IP, user agent, fbp, fbc)
                    # 3. Frontend will call POST /auth/oauth/complete-registration AFTER OAuth exchange
                    # 4. That endpoint will have access to real browser data for accurate tracking
                    logger.info(f"🎯 [SECURITY] New OAuth user created: {user.email} - CompleteRegistration will be fired from frontend POST request")
            else:
                raise HTTPException(status_code=401, detail="Invalid token payload: missing email")

        return user
    except IntegrityError as e:
        error_str = str(e)
        # Check if it's a unique constraint violation on email
        if "ix_user_profiles_email" in error_str or "duplicate key value violates unique constraint" in error_str.lower():
            logger.warning(f"Email unique constraint violation in get_current_user: {error_str}")
            # This shouldn't happen with our logic, but handle it gracefully
            # Try to find the user by email and return them
            email = payload.get("email")
            if email:
                result = await session.execute(select(UserProfile).where(UserProfile.email == email))
                existing_user = result.scalar_one_or_none()
                if existing_user:
                    logger.info(f"Found existing user by email after constraint violation: {email}")
                    return existing_user
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Please contact support.",
            )
        else:
            logger.error(f"Integrity error in get_current_user: {error_str}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database integrity error. Please try again.",
            )
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
