from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response, Request as FastAPIRequest
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserMe, UserProfileUpdate
from app.core.security import get_current_user
from app.models.user import UserProfile, PasswordResetCode
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.services.credits_service import CreditsService
from supabase import create_client, Client
from app.core.config import settings
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Initialize Supabase client for auth operations
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordConfirmRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

class AuthResponse(BaseModel):
    token: str
    user: UserMe

@router.post("/signup", response_model=AuthResponse)
async def signup(
    signup_request: SignUpRequest,
    http_request: FastAPIRequest,
    session: AsyncSession = Depends(get_session)
):
    """Sign up a new user via Supabase."""
    try:
        # Create user in Supabase with display_name in user metadata
        auth_response = supabase.auth.sign_up({
            "email": signup_request.email,
            "password": signup_request.password,
            "options": {
                "data": {
                    "display_name": signup_request.display_name,
                    "full_name": signup_request.display_name  # Also set full_name for compatibility
                }
            }
        })
        
        logger.info(f"Supabase signup response: user={auth_response.user}, session={auth_response.session}")
        
        # Check if user was created
        if not auth_response.user:
            error_msg = "Failed to create user"
            # Check for error message
            if hasattr(auth_response, 'message'):
                error_msg = auth_response.message
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        user_id = auth_response.user.id
        
        # If email confirmation is required, session might be None
        # In that case, we still create the profile but return a message
        if not auth_response.session:
            # Create user profile even without session (for email verification flow)
            from sqlalchemy.future import select
            result = await session.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            user_profile = result.scalar_one_or_none()
            
            # Get tracking context for later use (email verification webhook)
            client_ip = None
            client_user_agent = None
            fbp = None
            fbc = None
            if http_request:
                client_ip = http_request.client.host if http_request.client else None
                client_user_agent = http_request.headers.get("user-agent")
                fbp = http_request.cookies.get("_fbp")
                fbc = http_request.cookies.get("_fbc")
            
            if not user_profile:
                user_profile = UserProfile(
                    id=user_id,
                    email=signup_request.email,
                    display_name=signup_request.display_name,
                    # Store tracking context for CompleteRegistration on email verification
                    signup_ip=client_ip,
                    signup_user_agent=client_user_agent,
                    signup_fbp=fbp,
                    signup_fbc=fbc,
                )
                session.add(user_profile)
                await session.commit()
            elif not user_profile.display_name:
                # Update display name and tracking context if not already set
                user_profile.display_name = signup_request.display_name
                user_profile.signup_ip = client_ip
                user_profile.signup_user_agent = client_user_agent
                user_profile.signup_fbp = fbp
                user_profile.signup_fbc = fbc
                session.add(user_profile)
                await session.commit()
            
            # Track CompleteRegistration event for users requiring email verification
            try:
                from app.services.facebook_conversions import FacebookConversionsService
                
                conversions_service = FacebookConversionsService()
                
                # Extract first and last name from display_name if available
                first_name = None
                last_name = None
                if user_profile.display_name:
                    name_parts = user_profile.display_name.split(maxsplit=1)
                    first_name = name_parts[0] if name_parts else None
                    last_name = name_parts[1] if len(name_parts) > 1 else None
                
                # Tracking context was already saved above when creating user profile
                
                # Track CompleteRegistration (fire and forget - don't block response)
                import asyncio
                import time
                # Generate unique event_id for deduplication
                event_id = f"registration_{user_profile.id}_{int(time.time())}"
                logger.info(f"🎯 Triggering CompleteRegistration for user: {user_profile.email} (event_id: {event_id})")
                asyncio.create_task(conversions_service.track_complete_registration(
                    email=user_profile.email,
                    first_name=first_name,
                    last_name=last_name,
                    external_id=str(user_profile.id),
                    client_ip=client_ip,
                    client_user_agent=client_user_agent,
                    fbp=fbp,
                    fbc=fbc,
                    event_source_url=f"{settings.FRONTEND_URL}/signup-password",
                    event_id=event_id,
                ))
            except Exception as e:
                logger.warning(f"Failed to track CompleteRegistration event for user: {str(e)}")
            
            # Return success response indicating email verification needed
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=200,
                content={
                    "message": "User created. Please check your email to verify your account before logging in.",
                    "requires_verification": True
                }
            )
        
        token = auth_response.session.access_token
        
        # Create user profile in our database
        credits_service = CreditsService(session)
        
        # Check if profile already exists
        from sqlalchemy.future import select
        result = await session.execute(
            select(UserProfile).where(UserProfile.id == user_id)
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            user_profile = UserProfile(
                id=user_id,
                email=signup_request.email,
                display_name=signup_request.display_name,
            )
            session.add(user_profile)
            await session.commit()
            await session.refresh(user_profile)
            
            # Verify and create Backblaze B2 folders if they don't exist (same logic as login/OAuth)
            try:
                from app.services.storage_service import get_storage_service
                storage_service = get_storage_service()
                if storage_service.verify_and_create_user_folders(user_id):
                    logger.info(f"Verified/created Backblaze folders for user {user_id}")
                else:
                    logger.warning(f"Could not verify/create Backblaze folders for user {user_id} - B2 not configured or credentials invalid")
            except Exception as e:
                logger.error(f"Failed to verify/create Backblaze folders for user {user_id}: {e}", exc_info=True)
                # Don't fail signup if storage setup fails, but log the error
        elif not user_profile.display_name:
            # Update display name if not already set
            user_profile.display_name = signup_request.display_name
            session.add(user_profile)
            await session.commit()
            await session.refresh(user_profile)
        
        # Get wallet
        wallet = await credits_service.get_wallet(user_id)
        
        # Get subscription and plan info (if any)
        plan_name = None
        plan_interval = None
        credits_per_month = None
        from app.models.billing import Subscription, Plan
        
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == "active"
            )
        )
        subscription = result.scalar_one_or_none()
        
        if subscription and subscription.plan_id:
            plan_result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                plan_name = plan.display_name  # Use display_name for user-friendly display
                plan_interval = plan.interval
                credits_per_month = plan.credits_per_month
        
        # Track CompleteRegistration event for Facebook Conversions API
        try:
            from app.services.facebook_conversions import FacebookConversionsService
            
            conversions_service = FacebookConversionsService()
            
            # Extract first and last name from display_name if available
            first_name = None
            last_name = None
            if user_profile.display_name:
                name_parts = user_profile.display_name.split(maxsplit=1)
                first_name = name_parts[0] if name_parts else None
                last_name = name_parts[1] if len(name_parts) > 1 else None
            
            # Get client IP and user agent from HTTP request
            client_ip = None
            client_user_agent = None
            fbp = None
            fbc = None
            if http_request:
                client_ip = http_request.client.host if http_request.client else None
                client_user_agent = http_request.headers.get("user-agent")
                # Get Facebook cookies if available
                fbp = http_request.cookies.get("_fbp")
                fbc = http_request.cookies.get("_fbc")
            
            # Track registration (fire and forget - don't block response)
            import asyncio
            import uuid
            import time
            # Generate unique event_id for deduplication (if user also has Meta Pixel)
            event_id = f"registration_{user_profile.id}_{int(time.time())}"
            logger.info(f"🎯 Triggering CompleteRegistration for verified user: {user_profile.email} (event_id: {event_id})")
            asyncio.create_task(conversions_service.track_complete_registration(
                email=user_profile.email,
                first_name=first_name,
                last_name=last_name,
                external_id=str(user_profile.id),
                client_ip=client_ip,
                client_user_agent=client_user_agent,
                fbp=fbp,
                fbc=fbc,
                event_source_url=f"{settings.FRONTEND_URL}/signup-password",
                event_id=event_id,
            ))
        except Exception as e:
            logger.warning(f"Failed to track CompleteRegistration event: {str(e)}")
        
        # Track ViewContent event for signup page
        try:
            from app.services.facebook_conversions import FacebookConversionsService
            
            conversions_service = FacebookConversionsService()
            
            # Get client IP and user agent from HTTP request if available
            client_ip = None
            client_user_agent = None
            fbp = None
            fbc = None
            try:
                if http_request:
                    client_ip = http_request.client.host if http_request.client else None
                    client_user_agent = http_request.headers.get("user-agent")
                    fbp = http_request.cookies.get("_fbp")
                    fbc = http_request.cookies.get("_fbc")
            except:
                pass
            
            # Track ViewContent (fire and forget - don't block response)
            import asyncio
            asyncio.create_task(conversions_service.track_view_content(
                email=user_profile.email,
                external_id=str(user_profile.id),
                client_ip=client_ip,
                client_user_agent=client_user_agent,
                fbp=fbp,
                fbc=fbc,
                event_source_url=f"{settings.FRONTEND_URL}/signup",
            ))
            logger.info(f"Triggered ViewContent event tracking for signup - user {user_profile.id}")
        except Exception as e:
            logger.warning(f"Failed to track ViewContent event for signup: {str(e)}")
        
        return AuthResponse(
            token=token,
            user=UserMe(
                **user_profile.model_dump(),
                credit_balance=wallet.balance_credits,
                plan_name=plan_name,
                plan_interval=plan_interval,
                credits_per_month=credits_per_month
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signup failed: {str(e)}"
        )

@router.post("/login", response_model=AuthResponse)
async def login(
    login_request: SignInRequest,
    http_request: FastAPIRequest,
    session: AsyncSession = Depends(get_session)
):
    """Sign in user via Supabase."""
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": login_request.email,
            "password": login_request.password,
        })
        
        logger.info(f"Supabase login response: user={auth_response.user}, session={auth_response.session}")
        
        # Check for errors
        if not auth_response.user:
            error_msg = "Invalid email or password"
            if hasattr(auth_response, 'message'):
                error_msg = auth_response.message
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg
            )
        
        if not auth_response.session:
            error_msg = "Invalid credentials or email not verified"
            if hasattr(auth_response, 'message'):
                error_msg = auth_response.message
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg
            )
        
        token = auth_response.session.access_token
        user_id = auth_response.user.id
        
        # Get user profile
        credits_service = CreditsService(session)
        
        try:
            result = await session.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            user_profile = result.scalar_one_or_none()
            
            if not user_profile:
                # Auto-create if doesn't exist
                user_profile = UserProfile(
                    id=user_id,
                    email=login_request.email,
                )
                session.add(user_profile)
                await session.commit()
                await session.refresh(user_profile)
        except Exception as db_error:
            # Handle database connection errors (e.g., during server shutdown)
            error_str = str(db_error)
            if "ConnectionDoesNotExistError" in error_str or "connection was closed" in error_str.lower():
                logger.warning(f"Database connection error during login (possibly during shutdown): {db_error}")
                # Return a more user-friendly error
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable. Please try again in a moment."
                )
            # Re-raise other database errors
            raise
        
        # Verify and create Backblaze B2 folders if they don't exist
        try:
            from app.services.storage_service import get_storage_service
            storage_service = get_storage_service()
            if storage_service.verify_and_create_user_folders(user_id):
                logger.info(f"Verified/created Backblaze folders for user {user_id}")
            else:
                logger.warning(f"Could not verify/create Backblaze folders for user {user_id} - B2 not configured or credentials invalid")
        except Exception as e:
            logger.error(f"Failed to verify/create Backblaze folders for user {user_id}: {e}", exc_info=True)
            # Don't fail login if storage setup fails, but log the error
        
        # Fetch wallet with error handling for connection issues
        try:
            wallet = await credits_service.get_wallet(user_id)
            wallet_balance = wallet.balance_credits
        except Exception as wallet_error:
            # Handle database connection errors when fetching wallet
            error_str = str(wallet_error)
            if "ConnectionDoesNotExistError" in error_str or "connection was closed" in error_str.lower():
                logger.warning(f"Database connection error when fetching wallet (possibly during shutdown): {wallet_error}")
                # Return wallet with 0 credits as fallback
                wallet_balance = 0
            else:
                # For other errors, log and use 0 as fallback
                logger.error(f"Error fetching wallet for user {user_id}: {wallet_error}")
                wallet_balance = 0
        
        # Get subscription and plan info
        plan_name = None
        plan_interval = None
        credits_per_month = None
        from app.models.billing import Subscription, Plan
        
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == "active"
            )
        )
        subscription = result.scalar_one_or_none()
        
        if subscription and subscription.plan_id:
            plan_result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                plan_name = plan.display_name
                plan_interval = plan.interval
                credits_per_month = plan.credits_per_month
        
        # Track ViewContent event for login page
        try:
            from app.services.facebook_conversions import FacebookConversionsService
            
            conversions_service = FacebookConversionsService()
            
            # Get client IP and user agent from HTTP request if available
            client_ip = None
            client_user_agent = None
            fbp = None
            fbc = None
            try:
                if http_request:
                    client_ip = http_request.client.host if http_request.client else None
                    client_user_agent = http_request.headers.get("user-agent")
                    fbp = http_request.cookies.get("_fbp")
                    fbc = http_request.cookies.get("_fbc")
            except:
                pass
            
            # Track ViewContent (fire and forget - don't block response)
            import asyncio
            asyncio.create_task(conversions_service.track_view_content(
                email=user_profile.email,
                external_id=str(user_profile.id),
                client_ip=client_ip,
                client_user_agent=client_user_agent,
                fbp=fbp,
                fbc=fbc,
                event_source_url=f"{settings.FRONTEND_URL}/login",
            ))
            logger.info(f"Triggered ViewContent event tracking for login - user {user_profile.id}")
        except Exception as e:
            logger.warning(f"Failed to track ViewContent event for login: {str(e)}")
        
        return AuthResponse(
            token=token,
            user=UserMe(
                **user_profile.model_dump(),
                credit_balance=wallet_balance,
                plan_name=plan_name,
                plan_interval=plan_interval,
                credits_per_month=credits_per_month
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session)
):
    """Generate and send password reset code."""
    try:
        # Generate a 6-digit code
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Set expiration to 15 minutes from now
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        # Mark any existing codes for this email as used
        result = await session.execute(
            select(PasswordResetCode).where(
                and_(
                    PasswordResetCode.email == request.email,
                    PasswordResetCode.used == False,
                    PasswordResetCode.expires_at > datetime.utcnow()
                )
            )
        )
        existing_codes = result.scalars().all()
        for existing_code in existing_codes:
            existing_code.used = True
            session.add(existing_code)
        
        # Create new reset code
        reset_code = PasswordResetCode(
            email=request.email,
            code=code,
            expires_at=expires_at
        )
        session.add(reset_code)
        await session.commit()
        
        # TODO: Send email with code via email service
        # For now, log it (in production, send via email service)
        logger.info(f"Password reset code for {request.email}: {code}")
        
        # In production, send email here:
        # await email_service.send_password_reset_code(request.email, code)
        
        return {"message": "Password reset code sent to your email"}
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send reset code: {str(e)}"
        )

@router.post("/reset-password/confirm")
async def reset_password_confirm(
    request: ResetPasswordConfirmRequest,
    session: AsyncSession = Depends(get_session)
):
    """Confirm password reset with code and update password."""
    try:
        # Verify the reset code
        result = await session.execute(
            select(PasswordResetCode).where(
                and_(
                    PasswordResetCode.email == request.email,
                    PasswordResetCode.code == request.code,
                    PasswordResetCode.used == False,
                    PasswordResetCode.expires_at > datetime.utcnow()
                )
            )
        )
        reset_code = result.scalar_one_or_none()
        
        if not reset_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code. Please request a new code."
            )
        
        # Mark code as used
        reset_code.used = True
        session.add(reset_code)
        await session.commit()
        
        # Update password in Supabase
        try:
            # Get user from Supabase
            users = supabase.auth.admin.list_users()
            user = None
            for u in users.users:
                if u.email == request.email:
                    user = u
                    break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Update password using Supabase Admin API
            supabase.auth.admin.update_user_by_id(
                user.id,
                {"password": request.new_password}
            )
            
            return {"message": "Password reset successfully"}
            
        except Exception as supabase_error:
            logger.error(f"Supabase password update error: {str(supabase_error)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update password: {str(supabase_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password confirm error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reset password: {str(e)}"
        )

@router.get("/me", response_model=UserMe)
async def read_users_me(
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user profile with account settings (cached for 5 minutes)."""
    from app.models.billing import Subscription, Plan
    from app.utils.cache import get_cached, set_cached, cache_key
    
    cache_key_str = cache_key("cache", "user", str(current_user.id), "profile")
    
    # Try cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return UserMe(**cached)
    
    # Cache miss - fetch from database
    credits_service = CreditsService(session)
    wallet = await credits_service.get_wallet(current_user.id)
    
    # Get subscription and plan info
    plan_name = None
    plan_interval = None
    credits_per_month = None
    
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active"
        )
    )
    subscription = result.scalar_one_or_none()
    
    if subscription and subscription.plan_id:
        plan_result = await session.execute(
            select(Plan).where(Plan.id == subscription.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
            plan_name = plan.display_name  # Use display_name for user-friendly display
            plan_interval = plan.interval
            credits_per_month = plan.credits_per_month
    
    user_data = UserMe(
        **current_user.model_dump(),
        credit_balance=wallet.balance_credits,
        plan_name=plan_name,
        plan_interval=plan_interval,
        credits_per_month=credits_per_month
    )
    
    # Cache for 5 minutes (profile doesn't change often)
    # Use mode='json' to serialize UUIDs and datetimes properly
    await set_cached(cache_key_str, user_data.model_dump(mode='json'), ttl=300)
    
    return user_data

@router.put("/me", response_model=UserMe)
async def update_user_profile(
    update_data: UserProfileUpdate,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update current user's profile and invalidate cache."""
    from app.models.billing import Subscription, Plan
    from app.utils.cache import invalidate_user_cache
    
    credits_service = CreditsService(session)
    
    # Update fields if provided
    if update_data.display_name is not None:
        current_user.display_name = update_data.display_name
    if update_data.avatar_url is not None:
        current_user.avatar_url = update_data.avatar_url
    
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    
    # Invalidate user cache after update
    await invalidate_user_cache(str(current_user.id))
    
    wallet = await credits_service.get_wallet(current_user.id)
    
    # Get subscription and plan info
    plan_name = None
    plan_interval = None
    credits_per_month = None
    
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active"
        )
    )
    subscription = result.scalar_one_or_none()
    
    if subscription and subscription.plan_id:
        plan_result = await session.execute(
            select(Plan).where(Plan.id == subscription.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
            plan_name = plan.display_name  # Use display_name for user-friendly display
            plan_interval = plan.interval
            credits_per_month = plan.credits_per_month
    
    return UserMe(
        **current_user.model_dump(),
        credit_balance=wallet.balance_credits,
        plan_name=plan_name,
        plan_interval=plan_interval,
        credits_per_month=credits_per_month
    )

@router.get("/oauth/{provider}")
async def oauth_redirect(
    provider: str,
    redirect_uri: str = Query(..., description="Frontend redirect URI after OAuth"),
    request: Request = None
):
    """
    Initiate OAuth flow with the specified provider.
    Supports: google, apple, azure (Microsoft)
    
    This endpoint redirects to Supabase OAuth, which handles:
    - New users: Creates account and logs them in
    - Existing users: Logs them in
    """
    valid_providers = ["google", "apple", "azure"]
    if provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Supported: {', '.join(valid_providers)}"
        )
    
    try:
        logger.info("=" * 80)
        logger.info(f"[OAUTH] Starting OAuth flow for provider: {provider}")
        logger.info(f"[OAUTH] Frontend redirect URI received: {redirect_uri}")
        
        # Redirect to frontend homepage - Supabase will redirect there with the code
        # Frontend will then exchange the code for a token via backend API
        frontend_callback_url = redirect_uri.rstrip('/') + '/'
        logger.info(f"[OAUTH] Normalized frontend callback URL: {frontend_callback_url}")
        
        # Construct Supabase OAuth URL
        # Format: {SUPABASE_URL}/auth/v1/authorize?provider={provider}&redirect_to={frontend_url}
        # redirect_to should be the frontend homepage URL, URL-encoded
        # For Azure, we need to request 'email' scope (required by Supabase)
        from urllib.parse import quote, urlencode
        encoded_frontend = quote(frontend_callback_url, safe='')
        
        # Azure requires 'email' scope - add it as query parameter
        # See: https://supabase.com/docs/guides/auth/social-login/auth-azure
        query_params = {
            "provider": provider,
            "redirect_to": encoded_frontend
        }
        
        # Add scopes for Azure (email is required)
        if provider == "azure":
            query_params["scopes"] = "email"
        
        oauth_url = f"{settings.SUPABASE_URL}/auth/v1/authorize?{urlencode(query_params)}"
        
        logger.info(f"[OAUTH] Constructed Supabase OAuth URL: {oauth_url}")
        logger.info(f"[OAUTH] Redirecting user to Supabase for {provider} authentication...")
        logger.info("=" * 80)
        
        # Redirect to Supabase OAuth
        return RedirectResponse(url=oauth_url)
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"OAuth redirect error for {provider}: {error_msg}", exc_info=True)
        
        # Check if it's a provider not found error
        if "unsupported provider" in error_msg.lower() or "could not be found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth provider '{provider}' is not enabled in Supabase. Please enable it in your Supabase Dashboard > Authentication > Providers."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth flow: {error_msg}"
        )

class OAuthExchangeRequest(BaseModel):
    code: str
    redirect_to: str  # The exact redirect_to URL that was used in the authorize request

@router.post("/oauth/exchange", response_model=AuthResponse)
async def oauth_exchange(
    request: OAuthExchangeRequest,
    http_request: Request = None,
    session: AsyncSession = Depends(get_session)
):
    """
    Exchange OAuth authorization code for access token.
    Called by frontend after Supabase redirects with code.
    Creates user profile if new, or logs in existing user.
    Returns token that frontend can use to set cookie.
    """
    try:
        # Exchange code for session using Supabase API
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            exchange_url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=authorization_code"
            exchange_data = {
                "code": request.code,
                "redirect_to": request.redirect_to  # Must match exactly what was used in authorize request
            }
            
            response = await client.post(
                exchange_url,
                json=exchange_data,
                headers={
                    "apikey": settings.SUPABASE_KEY,
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error("=" * 80)
                logger.error(f"[OAUTH EXCHANGE] ❌ FAILED - Status: {response.status_code}")
                logger.error(f"[OAUTH EXCHANGE] Error response: {error_text}")
                logger.error("=" * 80)
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error_description") or error_json.get("error") or "Failed to exchange authorization code"
                    logger.error(f"[OAUTH EXCHANGE] Error message: {error_msg}")
                except:
                    error_msg = "Failed to exchange authorization code"
                    logger.error(f"[OAUTH EXCHANGE] Could not parse error response as JSON")
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            user_data = token_data.get("user", {})
            
            if not access_token or not user_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token response from authentication provider"
                )
            
            user_id = user_data.get("id")
            email = user_data.get("email")
            
            # Get or create user profile in our database
            credits_service = CreditsService(session)
            
            result = await session.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            user_profile = result.scalar_one_or_none()
            
            is_new_user = False
            if not user_profile:
                is_new_user = True
                logger.info(f"🆕 [OAUTH EXCHANGE] NEW USER detected: {email} (ID: {user_id})")
                
                # Create new user profile in our database
                display_name = user_data.get("user_metadata", {}).get("full_name") or \
                              user_data.get("user_metadata", {}).get("name") or \
                              email or "User"
                
                # Get avatar URL from Supabase
                avatar_url = user_data.get("avatar_url") or \
                            user_data.get("user_metadata", {}).get("avatar_url") or \
                            user_data.get("user_metadata", {}).get("picture") or \
                            None
                
                user_profile = UserProfile(
                    id=user_id,
                    email=email or "",
                    display_name=display_name,
                    avatar_url=avatar_url
                )
                session.add(user_profile)
                await session.commit()
                await session.refresh(user_profile)
                
                # Create wallet for new user (fast operation)
                wallet = await credits_service.get_or_create_wallet(user_id)
                
                # Track CompleteRegistration for OAuth signup (OAuth users are pre-verified)
                try:
                    from app.services.facebook_conversions import FacebookConversionsService
                    
                    conversions_service = FacebookConversionsService()
                    
                    # Extract first and last name from display_name
                    first_name = None
                    last_name = None
                    if user_profile.display_name:
                        name_parts = user_profile.display_name.split(maxsplit=1)
                        first_name = name_parts[0] if name_parts else None
                        last_name = name_parts[1] if len(name_parts) > 1 else None
                    
                    # Get client info from HTTP request
                    client_ip = None
                    client_user_agent = None
                    fbp = None
                    fbc = None
                    if http_request:
                        client_ip = http_request.client.host if http_request.client else None
                        client_user_agent = http_request.headers.get("user-agent")
                        fbp = http_request.cookies.get("_fbp")
                        fbc = http_request.cookies.get("_fbc")
                    
                    # Generate unique event_id for deduplication
                    import asyncio
                    import time
                    event_id = f"registration_{user_profile.id}_{int(time.time())}"
                    
                    logger.info(f"🎯 [OAUTH EXCHANGE] Triggering CompleteRegistration for NEW OAuth user: {user_profile.email} (event_id: {event_id})")
                    
                    # Fire CompleteRegistration event (fire and forget)
                    asyncio.create_task(conversions_service.track_complete_registration(
                        email=user_profile.email,
                        first_name=first_name,
                        last_name=last_name,
                        external_id=str(user_profile.id),
                        client_ip=client_ip,
                        client_user_agent=client_user_agent,
                        fbp=fbp,
                        fbc=fbc,
                        event_source_url=f"{settings.FRONTEND_URL}/",
                        event_id=event_id,
                    ))
                except Exception as e:
                    logger.warning(f"❌ [OAUTH EXCHANGE] Failed to track CompleteRegistration for OAuth user: {str(e)}")
            else:
                # Existing user - update email if it changed (only if needed)
                logger.info(f"👤 [OAUTH EXCHANGE] EXISTING USER login: {email} (ID: {user_id})")
                logger.info(f"ℹ️  [OAUTH EXCHANGE] CompleteRegistration NOT fired - user already exists")
                
                if email and user_profile.email != email:
                    user_profile.email = email
                    session.add(user_profile)
                    await session.commit()
                    await session.refresh(user_profile)
                
                # Update avatar URL if available and different
                avatar_url = user_data.get("avatar_url") or \
                            user_data.get("user_metadata", {}).get("avatar_url") or \
                            user_data.get("user_metadata", {}).get("picture") or \
                            None
                if avatar_url and user_profile.avatar_url != avatar_url:
                    user_profile.avatar_url = avatar_url
                    session.add(user_profile)
                    await session.commit()
                    await session.refresh(user_profile)
                
                # Get wallet for existing user (fast operation)
                wallet = await credits_service.get_or_create_wallet(user_id)
            
            # Get subscription and plan info
            plan_name = None
            plan_interval = None
            credits_per_month = None
            from app.models.billing import Subscription, Plan
            
            subscription_result = await session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.status == "active"
                    )
                )
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if subscription and subscription.plan_id:
                plan_result = await session.execute(
                    select(Plan).where(Plan.id == subscription.plan_id)
                )
                plan = plan_result.scalar_one_or_none()
                if plan:
                    plan_name = plan.display_name
                    plan_interval = plan.interval
                    credits_per_month = plan.credits_per_month
            
            # Return response immediately (fast path)
            return AuthResponse(
                token=access_token,
                user=UserMe(
                    **user_profile.model_dump(),
                    credit_balance=wallet.balance_credits,
                    plan_name=plan_name,
                    plan_interval=plan_interval,
                    credits_per_month=credits_per_month
                )
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"[OAUTH EXCHANGE] ❌ EXCEPTION: {str(e)}")
        logger.error(f"[OAUTH EXCHANGE] Exception type: {type(e).__name__}")
        logger.error("=" * 80, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth exchange failed: {str(e)}"
        )

@router.post("/oauth/callback")
async def oauth_callback_post(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Handle OAuth callback POST (for some providers).
    Supabase sends the session data here.
    """
    try:
        body = await request.json()
        access_token = body.get("access_token")
        refresh_token = body.get("refresh_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing access_token in OAuth callback"
            )
        
        # Verify token and get user info
        from jose import jwt
        payload = jwt.decode(
            access_token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token: missing user ID"
            )
        
        # Get or create user profile
        credits_service = CreditsService(session)
        
        result = await session.execute(
            select(UserProfile).where(UserProfile.id == user_id)
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            # Create new user profile
            user_profile = UserProfile(
                id=user_id,
                email=email or "",
                display_name=payload.get("name") or email or "User"
            )
            session.add(user_profile)
            await session.commit()
            await session.refresh(user_profile)
            
            # Create Backblaze B2 folder structure for new user
            try:
                from app.services.storage_service import get_storage_service
                storage_service = get_storage_service()
                if storage_service.create_user_folders(user_id):
                    logger.info(f"Created Backblaze folders for OAuth user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create Backblaze folders for user {user_id}: {e}", exc_info=True)
            
            logger.info(f"Created new user profile via OAuth: {user_id}")
        else:
            # Update email if it changed
            if email and user_profile.email != email:
                user_profile.email = email
                session.add(user_profile)
                await session.commit()
                await session.refresh(user_profile)
            
            logger.info(f"Existing user logged in via OAuth: {user_id}")
        
        # Get wallet
        wallet = await credits_service.get_wallet(user_id)
        
        # Get subscription and plan info
        plan_name = None
        plan_interval = None
        credits_per_month = None
        from app.models.billing import Subscription, Plan
        
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == "active"
            )
        )
        subscription = result.scalar_one_or_none()
        
        if subscription and subscription.plan_id:
            plan_result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                plan_name = plan.display_name
                plan_interval = plan.interval
                credits_per_month = plan.credits_per_month
        
        return {
            "token": access_token,
            "user": UserMe(
                **user_profile.model_dump(),
                credit_balance=wallet.balance_credits,
                plan_name=plan_name,
                plan_interval=plan_interval,
                credits_per_month=credits_per_month
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback POST error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
    )
