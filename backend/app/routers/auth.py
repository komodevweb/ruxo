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
from app.utils.request_helpers import get_client_ip
from supabase import create_client, Client
from app.core.config import settings
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

async def _ensure_no_credits_without_plan(wallet, user_id: uuid.UUID, session: AsyncSession):
    """Ensure users without an active plan have no credits."""
    if wallet.balance_credits > 0:
        logger.info(f"User {user_id} has {wallet.balance_credits} credits but no active subscription - removing credits")
        # Reset credits to 0
        wallet.balance_credits = 0
        session.add(wallet)
        await session.commit()
        
        # Invalidate credit cache
        from app.utils.cache import invalidate_cache, cache_key
        cache_key_str_credits = cache_key("cache", "user", str(user_id), "credits")
        await invalidate_cache(cache_key_str_credits)

# Initialize Supabase client for auth operations
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    # Tracking cookies (sent from frontend since cross-domain cookies don't work)
    fbp: Optional[str] = None
    fbc: Optional[str] = None
    ttp: Optional[str] = None
    ttclid: Optional[str] = None
    gclid: Optional[str] = None
    gbraid: Optional[str] = None
    wbraid: Optional[str] = None
    # GA4
    ga_client_id: Optional[str] = None
    ga_session_id: Optional[str] = None

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
    new_user: Optional[bool] = None  # True if this is a new user registration (for OAuth CompleteRegistration tracking)

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
            client_ip = get_client_ip(http_request)
            client_user_agent = http_request.headers.get("user-agent") if http_request else None
            # Get tracking cookies from request body (cross-domain cookies don't work)
            fbp = signup_request.fbp
            fbc = signup_request.fbc
            ttp = signup_request.ttp
            ttclid = signup_request.ttclid
            # Google Ads
            gclid = signup_request.gclid
            gbraid = signup_request.gbraid
            wbraid = signup_request.wbraid
            
            # Fallback to cookies if not in body
            if http_request:
                if not fbp:
                    fbp = http_request.cookies.get("_fbp")
                if not fbc:
                    fbc = http_request.cookies.get("_fbc")
                if not ttp:
                    ttp = http_request.cookies.get("_ttp")
                if not ttclid:
                    ttclid = http_request.cookies.get("_ttclid") or http_request.cookies.get("ttclid")
                if not gclid:
                    gclid = http_request.cookies.get("gclid") or http_request.cookies.get("_gcl_aw") or http_request.query_params.get("gclid")
                if not gbraid:
                    gbraid = http_request.cookies.get("gbraid") or http_request.query_params.get("gbraid")
                if not wbraid:
                    wbraid = http_request.cookies.get("wbraid") or http_request.query_params.get("wbraid")
            
            # GA4
            ga_client_id = signup_request.ga_client_id
            ga_session_id = signup_request.ga_session_id
            
            # Fallback to cookies if not in body
            if not ga_client_id:
                ga_cookie = http_request.cookies.get("_ga")
                if ga_cookie:
                    parts = ga_cookie.split('.')
                    if len(parts) >= 2:
                        ga_client_id = '.'.join(parts[-2:])
                    else:
                        ga_client_id = ga_cookie
            
            if not ga_session_id:
                for cookie_name, cookie_value in http_request.cookies.items():
                    if cookie_name.startswith("_ga_"):
                        parts = cookie_value.split(".")
                        if len(parts) > 2:
                            ga_session_id = parts[2]
                            break
            
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
                    signup_ttp=ttp,
                    signup_ttclid=ttclid,
                    signup_gclid=gclid,
                    signup_gbraid=gbraid,
                    signup_wbraid=wbraid,
                    signup_ga_client_id=ga_client_id,
                    signup_ga_session_id=ga_session_id,
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
                user_profile.signup_ttp = ttp
                user_profile.signup_ttclid = ttclid
                user_profile.signup_gclid = gclid
                user_profile.signup_gbraid = gbraid
                user_profile.signup_wbraid = wbraid
                user_profile.signup_ga_client_id = ga_client_id
                user_profile.signup_ga_session_id = ga_session_id
                session.add(user_profile)
                await session.commit()
            
            # Track CompleteRegistration event for users requiring email verification
            try:
                from app.services.facebook_conversions import FacebookConversionsService
                from app.services.tiktok_conversions import TikTokConversionsService
                from app.services.ga4_service import GA4Service
                
                conversions_service = FacebookConversionsService()
                tiktok_service = TikTokConversionsService()
                ga4_service = GA4Service()
                
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
                
                # Facebook tracking
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
                
                # TikTok tracking (ttp, ttclid already extracted from request body above)
                asyncio.create_task(tiktok_service.track_complete_registration(
                    email=user_profile.email,
                    first_name=first_name,
                    last_name=last_name,
                    external_id=str(user_profile.id),
                    client_ip=client_ip,
                    client_user_agent=client_user_agent,
                    event_source_url=f"{settings.FRONTEND_URL}/signup-password",
                    event_id=event_id,
                    ttp=ttp,
                    ttclid=ttclid,
                ))
                
                # GA4 tracking
                if ga_client_id:
                    asyncio.create_task(ga4_service.track_sign_up(
                        client_id=ga_client_id,
                        user_id=str(user_profile.id),
                        session_id=ga_session_id,
                        client_ip=client_ip,
                        user_agent=client_user_agent,
                        page_location=f"{settings.FRONTEND_URL}/signup-password",
                        method="email"
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
                Subscription.status.in_(["active", "trialing"])
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
            from app.services.tiktok_conversions import TikTokConversionsService
            
            conversions_service = FacebookConversionsService()
            tiktok_service = TikTokConversionsService()
            
            # Extract first and last name from display_name if available
            first_name = None
            last_name = None
            if user_profile.display_name:
                name_parts = user_profile.display_name.split(maxsplit=1)
                first_name = name_parts[0] if name_parts else None
                last_name = name_parts[1] if len(name_parts) > 1 else None
            
            # Get client IP and user agent from HTTP request
            client_ip = get_client_ip(http_request)
            client_user_agent = http_request.headers.get("user-agent") if http_request else None
            
            # Get Facebook cookies (prefer request body for cross-domain support)
            fbp = signup_request.fbp
            if not fbp and http_request:
                fbp = http_request.cookies.get("_fbp")
                
            fbc = signup_request.fbc
            if not fbc and http_request:
                fbc = http_request.cookies.get("_fbc")
            
            # Track registration (fire and forget - don't block response)
            import asyncio
            import uuid
            import time
            # Generate unique event_id for deduplication (if user also has Meta Pixel)
            event_id = f"registration_{user_profile.id}_{int(time.time())}"
            logger.info(f"🎯 Triggering CompleteRegistration for verified user: {user_profile.email} (event_id: {event_id})")
            
            # Facebook tracking
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
            
            # TikTok tracking
            # Prefer request body for cross-domain support
            ttp = signup_request.ttp
            if not ttp and http_request:
                ttp = http_request.cookies.get("_ttp")
            
            ttclid = signup_request.ttclid
            if not ttclid and http_request:
                ttclid = http_request.cookies.get("_ttclid") or http_request.cookies.get("ttclid")
                
            asyncio.create_task(tiktok_service.track_complete_registration(
                email=user_profile.email,
                first_name=first_name,
                last_name=last_name,
                external_id=str(user_profile.id),
                client_ip=client_ip,
                client_user_agent=client_user_agent,
                event_source_url=f"{settings.FRONTEND_URL}/signup-password",
                event_id=event_id,
                ttp=ttp,
                ttclid=ttclid,
            ))
        except Exception as e:
            logger.warning(f"Failed to track CompleteRegistration event: {str(e)}")
        
        # Track ViewContent event for signup page
        try:
            from app.services.facebook_conversions import FacebookConversionsService
            
            conversions_service = FacebookConversionsService()
            
            # Get client IP and user agent from HTTP request if available
            try:
                client_ip = get_client_ip(http_request)
                client_user_agent = http_request.headers.get("user-agent") if http_request else None
                fbp = http_request.cookies.get("_fbp") if http_request else None
                fbc = http_request.cookies.get("_fbc") if http_request else None
            except:
                client_ip = None
                client_user_agent = None
                fbp = None
                fbc = None
            
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
                Subscription.status.in_(["active", "trialing"])
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
            try:
                client_ip = get_client_ip(http_request)
                client_user_agent = http_request.headers.get("user-agent") if http_request else None
                fbp = http_request.cookies.get("_fbp") if http_request else None
                fbc = http_request.cookies.get("_fbc") if http_request else None
            except:
                client_ip = None
                client_user_agent = None
                fbp = None
                fbc = None
            
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
    subscription_status = None
    
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["active", "trialing"])
        )
    )
    subscription = result.scalar_one_or_none()
    
    if subscription:
        subscription_status = subscription.status
        if subscription.plan_id:
            plan_result = await session.execute(
                select(Plan).where(Plan.id == subscription.plan_id)
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                plan_name = plan.display_name  # Use display_name for user-friendly display
                plan_interval = plan.interval
                credits_per_month = plan.credits_per_month
    else:
        # User has no active subscription - ensure they have no credits
        await _ensure_no_credits_without_plan(wallet, current_user.id, session)
    
    user_data = UserMe(
        **current_user.model_dump(),
        credit_balance=wallet.balance_credits,
        plan_name=plan_name,
        plan_interval=plan_interval,
        subscription_status=subscription_status,
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
    subscription_status = None
    
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["active", "trialing"])
        )
    )
    subscription = result.scalar_one_or_none()
    
    if subscription:
        subscription_status = subscription.status
        if subscription.plan_id:
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
        subscription_status=subscription_status,
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

class TrackingData(BaseModel):
    """Optional tracking data sent from frontend to preserve cookies across OAuth redirects."""
    fbp: Optional[str] = None
    fbc: Optional[str] = None
    ttp: Optional[str] = None
    ttclid: Optional[str] = None
    gclid: Optional[str] = None
    gbraid: Optional[str] = None
    wbraid: Optional[str] = None
    user_agent: Optional[str] = None

class OAuthExchangeRequest(BaseModel):
    code: str
    redirect_to: str  # The exact redirect_to URL that was used in the authorize request
    tracking_data: Optional[TrackingData] = None  # Optional tracking data from frontend

@router.post("/oauth/exchange", response_model=AuthResponse)
async def oauth_exchange(
    request: OAuthExchangeRequest,
    http_request: FastAPIRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Exchange OAuth authorization code for access token.
    Called by frontend after Supabase redirects with code.
    Creates user profile if new, or logs in existing user.
    Returns token that frontend can use to set cookie.
    """
    # Use the dedicated Facebook logger for visibility in facebook_conversions_api.log
    fb_logger = logging.getLogger("facebook_conversions_api")
    
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
                # User doesn't exist by ID - check if they exist by email (migration case)
                if email:
                    result_by_email = await session.execute(
                        select(UserProfile).where(UserProfile.email == email)
                    )
                    existing_by_email = result_by_email.scalar_one_or_none()
                    
                    if existing_by_email:
                        # MIGRATION CASE: User exists by email but with different ID
                        # This happens when user deleted Supabase account and re-registered with same email
                        is_new_user = True  # Treat as new for CompleteRegistration purposes
                        logger.info(f"🔄 [OAUTH EXCHANGE] MIGRATION detected: email={email}, old_id={existing_by_email.id}, new_id={user_id}")
                        logger.info(f"ℹ️  [OAUTH EXCHANGE] Migration will be handled by get_current_user in complete-registration endpoint")
                        
                        # DON'T create new profile here - migration will be handled by security.py's get_current_user
                        # when frontend calls complete-registration endpoint
                        # Return existing profile for now, it will be migrated on next request
                        user_profile = existing_by_email
                        
                        # Get wallet (it will be migrated to new ID later)
                        wallet = await credits_service.get_or_create_wallet(existing_by_email.id)
                    else:
                        # NEW USER: Create new user profile
                        is_new_user = True
                        logger.info(f"🆕 [OAUTH EXCHANGE] NEW USER detected: {email} (ID: {user_id})")
                        fb_logger.info(f"🆕 [OAUTH EXCHANGE] NEW USER detected: {email} (ID: {user_id}) - will return new_user=True")
                        
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
                        
                        # DO NOT fire CompleteRegistration here - the request comes from Google's server, not the real browser
                        # Instead, return new_user flag and let frontend call a separate endpoint from the real browser
                        logger.info(f"🆕 [OAUTH EXCHANGE] New user created - CompleteRegistration will be fired when real browser hits backend")
                else:
                    # No email in token - shouldn't happen but handle gracefully
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid token: missing email"
                    )
            else:
                # Existing user by ID - regular login, no CompleteRegistration needed
                logger.info(f"👤 [OAUTH EXCHANGE] EXISTING USER login: {email} (ID: {user_id})")
                logger.info(f"ℹ️  [OAUTH EXCHANGE] CompleteRegistration NOT fired - user already exists")
                fb_logger.info(f"👤 [OAUTH EXCHANGE] EXISTING USER login: {email} (ID: {user_id}) - return new_user=False")
                
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
                        Subscription.status.in_(["active", "trialing"])
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
            
            # Return response with new_user flag
            # Frontend will call complete-registration endpoint if new_user is True
            return AuthResponse(
                token=access_token,
                user=UserMe(
                    **user_profile.model_dump(),
                    credit_balance=wallet.balance_credits,
                    plan_name=plan_name,
                    plan_interval=plan_interval,
                    credits_per_month=credits_per_month
                ),
                new_user=is_new_user  # Frontend will use this to trigger CompleteRegistration from real browser
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

class CompleteRegistrationRequest(BaseModel):
    """
    Tracking data sent from frontend for CompleteRegistration event.
    
    IMPORTANT: _fbp, _fbc, _ttp, and _ttclid are first-party cookies set on the FRONTEND domain.
    They won't be sent automatically via credentials:include because the backend
    is on a different domain. Frontend must read them from document.cookie and
    send them in the request body.
    """
    # Facebook cookies
    fbp: Optional[str] = None
    fbc: Optional[str] = None
    # TikTok cookies
    ttp: Optional[str] = None
    ttclid: Optional[str] = None
    
    # Google Ads
    gclid: Optional[str] = None
    gbraid: Optional[str] = None
    wbraid: Optional[str] = None

    # GA4
    ga_client_id: Optional[str] = None
    ga_session_id: Optional[str] = None
    # Browser info
    user_agent: Optional[str] = None

@router.post("/oauth/complete-registration")
async def oauth_complete_registration(
    http_request: FastAPIRequest,
    tracking_data: Optional[CompleteRegistrationRequest] = None,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Fire CompleteRegistration event for OAuth signup.
    Called by frontend AFTER OAuth (both code exchange and hash flows).
    This request comes from the REAL browser, so we get real IP, user agent, cookies.
    
    Only fires the event if user is NEW (created within last 5 minutes) and hasn't
    had tracking data set yet.
    
    IMPORTANT: Frontend must send fbp and fbc in the request body because they are
    first-party cookies on the frontend domain and won't be sent automatically
    to the backend API domain via credentials:include.
    """
    try:
        from app.services.facebook_conversions import FacebookConversionsService
        from app.services.tiktok_conversions import TikTokConversionsService
        from app.services.ga4_service import GA4Service
        import asyncio
        import time
        
        # Use the dedicated Facebook logger for visibility in facebook_conversions_api.log
        fb_logger = logging.getLogger("facebook_conversions_api")
        
        # Check if user is new and needs CompleteRegistration tracking
        # Criteria: created within last 5 minutes AND signup_ip not set (hasn't been tracked yet)
        is_new_user = False
        time_info = "N/A"
        
        if current_user.created_at:
            # Use timezone-aware datetime for comparison
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            
            # Make created_at timezone-aware if it's naive
            created_at = current_user.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            time_since_creation = now_utc - created_at
            seconds_since_creation = time_since_creation.total_seconds()
            
            # Allow up to 1 hour (3600s) to account for slow user flow or clock skew
            # Originally was 5 mins (300s) which might be too tight
            is_recently_created = seconds_since_creation < 3600
            
            has_no_tracking = not (hasattr(current_user, 'signup_ip') and current_user.signup_ip)
            is_new_user = is_recently_created and has_no_tracking
            
            time_info = f"created_at={created_at}, now={now_utc}, diff={seconds_since_creation:.0f}s"
            
            fb_logger.info(f"📊 [OAUTH COMPLETE-REGISTRATION] User check: {current_user.email}, is_new={is_new_user}, recently_created={is_recently_created}, no_tracking={has_no_tracking}, {time_info}")
        
        if not is_new_user:
            # Fallback: If signup_ip is NULL, we should probably track it anyway if it's reasonably recent (e.g. < 24 hours)
            # This catches cases where the user registered hours ago but never completed the flow or tracking failed
            if current_user.created_at and hasattr(current_user, 'signup_ip') and not current_user.signup_ip:
                 # Re-calculate time since creation
                 if 'seconds_since_creation' in locals() and seconds_since_creation < 86400: # 24 hours
                     is_new_user = True
                     fb_logger.info(f"⚠️ [OAUTH COMPLETE-REGISTRATION] User {current_user.email} is older than 1h but has NO tracking data (signup_ip=None). Forcing tracking. Age: {seconds_since_creation:.0f}s")

        if not is_new_user:
            logger.info(f"ℹ️  [OAUTH COMPLETE-REGISTRATION] Skipping - user is not new: {current_user.email}")
            fb_logger.info(f"ℹ️  [OAUTH COMPLETE-REGISTRATION] Skipping - user is not new: {current_user.email} ({time_info})")
            return {"status": "skipped", "message": "User is not new", "event_fired": False}
        
        conversions_service = FacebookConversionsService()
        tiktok_service = TikTokConversionsService()
        ga4_service = GA4Service()
        
        # Extract first and last name from display_name
        first_name = None
        last_name = None
        if current_user.display_name:
            name_parts = current_user.display_name.split(maxsplit=1)
            first_name = name_parts[0] if name_parts else None
            last_name = name_parts[1] if len(name_parts) > 1 else None
        
        # Get REAL client info from the actual browser request (not Google's server)
        client_ip = get_client_ip(http_request)
        
        # Try to get user agent from request headers first, then from body
        client_user_agent = http_request.headers.get("user-agent") if http_request else None
        if tracking_data and tracking_data.user_agent:
            # Prefer the user_agent from body if provided (more reliable)
            client_user_agent = tracking_data.user_agent
        
        # IMPORTANT: _fbp and _fbc cookies are set on the FRONTEND domain
        # They won't be sent via cookies to backend (different domain)
        # Frontend must read them from document.cookie and send in request body
        fbp = None
        fbc = None
        
        # Try cookies first (in case same domain)
        if http_request:
            fbp = http_request.cookies.get("_fbp")
            fbc = http_request.cookies.get("_fbc")
        
        # Use tracking_data from request body (preferred - works cross-domain)
        if tracking_data:
            logger.info(f"📊 [OAUTH COMPLETE-REGISTRATION] Received tracking_data: ttp={'✓' if tracking_data.ttp else '✗'}, ttclid={'✓' if tracking_data.ttclid else '✗'}, fbp={'✓' if tracking_data.fbp else '✗'}, gclid={'✓' if tracking_data.gclid else '✗'}")
            if tracking_data.fbp:
                fbp = tracking_data.fbp
            if tracking_data.fbc:
                fbc = tracking_data.fbc
        
        # Fallback for GA4 cookies if not provided in tracking_data
        ga_client_id = None
        ga_session_id = None
        
        if tracking_data and tracking_data.ga_client_id:
            ga_client_id = tracking_data.ga_client_id
        
        if tracking_data and tracking_data.ga_session_id:
            ga_session_id = tracking_data.ga_session_id
            
        # Try extracting from cookies if missing
        if not ga_client_id and http_request:
            ga_cookie = http_request.cookies.get("_ga")
            if ga_cookie:
                parts = ga_cookie.split('.')
                if len(parts) >= 2:
                    ga_client_id = '.'.join(parts[-2:])
                else:
                    ga_client_id = ga_cookie
        
        if not ga_session_id and http_request:
            for cookie_name, cookie_value in http_request.cookies.items():
                if cookie_name.startswith("_ga_"):
                    parts = cookie_value.split(".")
                    if len(parts) > 2:
                        ga_session_id = parts[2]
                        break
                        
        # If still missing, try to fallback to what we saved in user profile
        if not ga_client_id and hasattr(current_user, 'signup_ga_client_id') and current_user.signup_ga_client_id:
            ga_client_id = current_user.signup_ga_client_id
            
        if not ga_session_id and hasattr(current_user, 'signup_ga_session_id') and current_user.signup_ga_session_id:
            ga_session_id = current_user.signup_ga_session_id
        
        logger.info(f"🎯 [OAUTH COMPLETE-REGISTRATION] Firing CompleteRegistration for NEW OAuth user: {current_user.email}")
        logger.info(f"📊 [OAUTH COMPLETE-REGISTRATION] Real browser data: IP={client_ip}, UA={bool(client_user_agent)}, fbp={bool(fbp)}, fbc={bool(fbc)}, ga_client_id={bool(ga_client_id)}")
        if fbp:
            logger.info(f"📊 [OAUTH COMPLETE-REGISTRATION] fbp value: {fbp[:30]}..." if len(fbp) > 30 else f"📊 [OAUTH COMPLETE-REGISTRATION] fbp value: {fbp}")
        if fbc:
            logger.info(f"📊 [OAUTH COMPLETE-REGISTRATION] fbc value: {fbc[:30]}..." if len(fbc) > 30 else f"📊 [OAUTH COMPLETE-REGISTRATION] fbc value: {fbc}")
        
        # Save tracking data to user profile to prevent duplicate tracking
        if hasattr(current_user, 'signup_ip'):
            current_user.signup_ip = client_ip
            current_user.signup_user_agent = client_user_agent
            current_user.signup_fbp = fbp
            current_user.signup_fbc = fbc
            
            # Define TikTok and Google variables before usage
            ttp = None
            ttclid = None
            gclid = None
            gbraid = None
            wbraid = None
            
            if http_request:
                ttp = http_request.cookies.get("_ttp")
                ttclid = http_request.cookies.get("_ttclid") or http_request.cookies.get("ttclid")
                gclid = http_request.cookies.get("gclid") or http_request.cookies.get("_gcl_aw") or http_request.query_params.get("gclid")
                gbraid = http_request.cookies.get("gbraid") or http_request.query_params.get("gbraid")
                wbraid = http_request.cookies.get("wbraid") or http_request.query_params.get("wbraid")
                
            if tracking_data:
                if hasattr(tracking_data, 'ttp') and tracking_data.ttp:
                    ttp = tracking_data.ttp
                if hasattr(tracking_data, 'ttclid') and tracking_data.ttclid:
                    ttclid = tracking_data.ttclid
                if hasattr(tracking_data, 'gclid') and tracking_data.gclid:
                    gclid = tracking_data.gclid
                if hasattr(tracking_data, 'gbraid') and tracking_data.gbraid:
                    gbraid = tracking_data.gbraid
                if hasattr(tracking_data, 'wbraid') and tracking_data.wbraid:
                    wbraid = tracking_data.wbraid
            
            current_user.signup_ttp = ttp
            current_user.signup_ttclid = ttclid
            current_user.signup_gclid = gclid
            current_user.signup_gbraid = gbraid
            current_user.signup_wbraid = wbraid
            
            if tracking_data and tracking_data.ga_client_id:
                current_user.signup_ga_client_id = tracking_data.ga_client_id
            if tracking_data and tracking_data.ga_session_id:
                current_user.signup_ga_session_id = tracking_data.ga_session_id
                
            session.add(current_user)
            await session.commit()
        
        # Generate unique event_id for deduplication
        event_id = f"registration_{current_user.id}_{int(time.time())}"
        
        # Fire CompleteRegistration event (fire and forget)
        # Facebook tracking
        asyncio.create_task(conversions_service.track_complete_registration(
            email=current_user.email,
            first_name=first_name,
            last_name=last_name,
            external_id=str(current_user.id),
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
            event_source_url=f"{settings.FRONTEND_URL}/",
            event_id=event_id,
        ))
        
        # TikTok tracking (using the variables defined above)
        asyncio.create_task(tiktok_service.track_complete_registration(
            email=current_user.email,
            first_name=first_name,
            last_name=last_name,
            external_id=str(current_user.id),
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=f"{settings.FRONTEND_URL}/",
            event_id=event_id,
            ttp=ttp,
            ttclid=ttclid,
        ))
        
                # GA4 tracking
        if ga_client_id:
            asyncio.create_task(ga4_service.track_sign_up(
                client_id=ga_client_id,
                user_id=str(current_user.id),
                session_id=ga_session_id,
                client_ip=client_ip,
                user_agent=client_user_agent,
                page_location=f"{settings.FRONTEND_URL}/",
                method="google"  # Since this is OAuth callback
            ))
        
        logger.info(f"✅ [OAUTH COMPLETE-REGISTRATION] CompleteRegistration event queued for new user")
        
        return {"status": "success", "message": "CompleteRegistration event fired", "event_fired": True}
        
    except Exception as e:
        logger.error(f"❌ [OAUTH COMPLETE-REGISTRATION] Failed to fire CompleteRegistration: {str(e)}", exc_info=True)
        # Don't fail the request - tracking is best effort
        return {"status": "error", "message": "Failed to fire CompleteRegistration event", "event_fired": False}

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
                Subscription.status.in_(["active", "trialing"])
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
