import stripe
import uuid
import time
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.core.config import settings
from app.models.billing import Subscription, Payment, Plan
from app.models.user import UserProfile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.services.credits_service import CreditsService

stripe.api_key = settings.STRIPE_API_KEY

class BillingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.credits_service = CreditsService(session)
    
    def _build_checkout_metadata(
        self,
        user_id: str,
        plan_id: str,
        plan_name: str,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None,
        **extra_metadata
    ) -> dict:
        """Build checkout session metadata with tracking context for Purchase events."""
        metadata = {
            "user_id": user_id,
            "plan_id": plan_id,
            "plan_name": plan_name,
        }
        
        # Add tracking context if available (for later Purchase event)
        if client_ip:
            metadata["client_ip"] = client_ip
        if client_user_agent:
            metadata["client_user_agent"] = client_user_agent
        # Facebook cookies
        if fbp:
            metadata["fbp"] = fbp
        if fbc:
            metadata["fbc"] = fbc
        # TikTok cookies
        if ttp:
            metadata["ttp"] = ttp
        if ttclid:
            metadata["ttclid"] = ttclid
        
        # Add any extra metadata (e.g., is_upgrade, existing_subscription_id)
        metadata.update(extra_metadata)
        
        return metadata

    async def create_checkout_session(
        self,
        user: UserProfile,
        plan_name: str,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None
    ) -> str:
        """Create Stripe checkout session for a subscription plan or upgrade existing subscription."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Fetch the plan from the DB
        query = select(Plan).where(Plan.name == plan_name, Plan.is_active == True)
        result = await self.session.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            raise HTTPException(status_code=400, detail=f"Plan '{plan_name}' not found.")
        
        # Check if user has an active subscription
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status.in_(["active", "trialing"])
            )
        )
        existing_subscription = result.scalar_one_or_none()
        
        # If user has an active subscription, handle upgrade/downgrade
        # SECURITY: Do NOT cancel admin subscriptions (manually granted) - they should use portal
        # Only cancel real Stripe subscriptions, and only if they're upgrading/downgrading to a different plan
        if existing_subscription:
            # Check if this is an admin subscription (manually granted, starts with "admin_")
            is_admin_subscription = existing_subscription.stripe_subscription_id.startswith("admin_")
            
            # Check if user is trying to select the same plan they already have
            current_plan_key = existing_subscription.plan_name.split('_')[0]  # e.g., "pro" from "pro_monthly"
            new_plan_key = plan_name.split('_')[0]  # e.g., "pro" from "pro_monthly"
            is_same_plan = current_plan_key == new_plan_key
            
            if is_admin_subscription:
                # Admin subscriptions should use customer portal, not checkout
                logger.warning(f"User {user.id} has admin subscription {existing_subscription.stripe_subscription_id}. Admin subscriptions should be managed via portal, not checkout.")
                raise HTTPException(
                    status_code=400,
                    detail="You have a manually granted subscription. Please use the 'Manage Subscription' button to modify your plan, or contact support."
                )
            
            if is_same_plan:
                # User is trying to subscribe to the same plan they already have
                logger.info(f"User {user.id} already has plan {plan_name}. Redirecting to customer portal.")
                raise HTTPException(
                    status_code=400,
                    detail=f"You already have the {plan.display_name} plan. Use 'Manage Subscription' to view or modify your subscription."
                )
            
            # User is upgrading/downgrading to a different plan
            logger.info(f"User {user.id} has active subscription {existing_subscription.stripe_subscription_id}, upgrading to {plan_name}")
            
            try:
                # Get or create Stripe customer (validates customer exists in Stripe)
                if existing_subscription.stripe_customer_id:
                    # Verify customer exists, create new one if it doesn't
                    try:
                        stripe.Customer.retrieve(existing_subscription.stripe_customer_id)
                        customer_id = existing_subscription.stripe_customer_id
                    except stripe.error.StripeError:
                        # Customer doesn't exist, get or create a new one
                        logger.warning(f"Customer {existing_subscription.stripe_customer_id} not found in Stripe. Creating new customer.")
                        customer_id = await self._get_or_create_customer(user)
                        # Update subscription with new customer ID
                        existing_subscription.stripe_customer_id = customer_id
                        self.session.add(existing_subscription)
                        await self.session.commit()
                else:
                    customer_id = await self._get_or_create_customer(user)
            
                # For upgrades/downgrades, use Stripe's subscription modification instead of canceling
                # This preserves the subscription and just changes the plan
                try:
                    # Retrieve the current subscription from Stripe
                    stripe_subscription = stripe.Subscription.retrieve(existing_subscription.stripe_subscription_id)
                    
                    # Update the subscription to the new plan (Stripe handles proration)
                    updated_subscription = stripe.Subscription.modify(
                        existing_subscription.stripe_subscription_id,
                        items=[{
                            'id': stripe_subscription['items']['data'][0].id,
                            'price': plan.stripe_price_id,
                        }],
                        proration_behavior='always_invoice',  # Charge immediately for prorated amount
                    )
                    
                    logger.info(f"Updated subscription {existing_subscription.stripe_subscription_id} to plan {plan_name} via Stripe API")
                    
                    # Update our database to reflect the new plan
                    existing_subscription.plan_id = plan.id
                    existing_subscription.plan_name = plan.name
                    existing_subscription.updated_at = datetime.utcnow()
                    self.session.add(existing_subscription)
                    await self.session.commit()
                    
                    # Track Purchase event for subscription upgrade/downgrade
                    # This is critical because Subscription.modify() doesn't trigger checkout.session.completed webhook
                    try:
                        from app.services.facebook_conversions import FacebookConversionsService
                        from app.services.tiktok_conversions import TikTokConversionsService
                        
                        # Calculate purchase value
                        value = plan.amount_cents / 100.0
                        currency = "USD"
                        event_id = f"sub_modify_{existing_subscription.stripe_subscription_id}_{int(time.time())}"
                        
                        # Extract name parts from display_name
                        first_name = None
                        last_name = None
                        if user.display_name:
                            name_parts = user.display_name.split(maxsplit=1)
                            first_name = name_parts[0] if name_parts else None
                            last_name = name_parts[1] if len(name_parts) > 1 else None
                        
                        logger.info("=" * 80)
                        logger.info(f"💰 [PURCHASE TRACKING] Tracking Purchase for Subscription.modify() upgrade")
                        logger.info(f"💰 [PURCHASE TRACKING] User: {user.email}, Plan: {plan_name}, Value: ${value}")
                        logger.info(f"💰 [PURCHASE TRACKING] Using tracking context: IP={client_ip}, UA={client_user_agent[:50] if client_user_agent else 'None'}...")
                        logger.info(f"💰 [PURCHASE TRACKING] Facebook Cookies: fbp={fbp}, fbc={fbc}")
                        logger.info(f"💰 [PURCHASE TRACKING] TikTok Cookies: ttp={ttp}, ttclid={ttclid}")
                        
                        conversions_service = FacebookConversionsService()
                        tiktok_service = TikTokConversionsService()
                        import asyncio
                        # Facebook tracking
                        asyncio.create_task(conversions_service.track_purchase(
                            value=value,
                            currency=currency,
                            email=user.email,
                            first_name=first_name,
                            last_name=last_name,
                            external_id=str(user.id),
                            client_ip=client_ip,
                            client_user_agent=client_user_agent,
                            fbp=fbp,
                            fbc=fbc,
                            event_source_url=f"{settings.FRONTEND_URL}/upgrade",
                            event_id=event_id,
                        ))
                        # TikTok tracking
                        asyncio.create_task(tiktok_service.track_purchase(
                            value=value,
                            currency=currency,
                            email=user.email,
                            first_name=first_name,
                            last_name=last_name,
                            external_id=str(user.id),
                            client_ip=client_ip,
                            client_user_agent=client_user_agent,
                            event_source_url=f"{settings.FRONTEND_URL}/upgrade",
                            event_id=event_id,
                            ttp=ttp,
                            ttclid=ttclid,
                        ))
                        logger.info(f"✅ [PURCHASE TRACKING] Purchase event triggered for subscription upgrade")
                        logger.info("=" * 80)
                    except Exception as e:
                        logger.error(f"❌ [PURCHASE TRACKING] Failed to track Purchase event for upgrade: {str(e)}", exc_info=True)
                    
                    # Return the customer portal URL instead of checkout URL
                    # User should use portal to manage their updated subscription
                    portal_session = stripe.billing_portal.Session.create(
                        customer=customer_id,
                        return_url=f"{settings.FRONTEND_URL}/upgrade",
                    )
                    return portal_session.url
                    
                except stripe.error.InvalidRequestError as e:
                    error_msg = str(e)
                    if "No such subscription" in error_msg:
                        # Subscription doesn't exist in Stripe, but exists in our DB
                        # This can happen with admin subscriptions or deleted subscriptions
                        # Allow creating a new checkout session instead of blocking
                        logger.warning(f"Subscription {existing_subscription.stripe_subscription_id} not found in Stripe. Marking as cancelled and creating new checkout session.")
                        
                        # Mark the old subscription as cancelled since it doesn't exist in Stripe
                        existing_subscription.status = "cancelled"
                        existing_subscription.cancelled_at = datetime.utcnow()
                        self.session.add(existing_subscription)
                        await self.session.commit()
                        
                        # Create a new checkout session for the new plan
                        # Verify the price ID exists in Stripe
                        try:
                            stripe.Price.retrieve(plan.stripe_price_id)
                        except stripe.error.InvalidRequestError as price_err:
                            if "No such price" in str(price_err):
                                logger.error(f"Price ID {plan.stripe_price_id} for plan '{plan.name}' does not exist in Stripe.")
                                raise HTTPException(
                                    status_code=500,
                                    detail=f"Invalid price configuration for plan '{plan.display_name}'. Please contact support."
                                )
                            raise
                        
                        # Create checkout session for new subscription
                        checkout_params = {
                            "payment_method_types": ["card"],
                            "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
                            "mode": "subscription",
                            "customer": customer_id,
                            "success_url": f"{settings.FRONTEND_URL}/",
                            "cancel_url": f"{settings.FRONTEND_URL}/upgrade",
                            "metadata": self._build_checkout_metadata(
                                user_id=str(user.id),
                                plan_id=str(plan.id),
                                plan_name=plan.name,
                                client_ip=client_ip,
                                client_user_agent=client_user_agent,
                                fbp=fbp,
                                fbc=fbc,
                                ttp=ttp,
                                ttclid=ttclid,
                            ),
                            "subscription_data": {
                                "metadata": {
                                    "user_id": str(user.id),
                                    "plan_id": str(plan.id),
                                    "plan_name": plan.name,
                                    "client_ip": client_ip or "",
                                    "client_user_agent": client_user_agent or "",
                                    "fbp": fbp or "",
                                    "fbc": fbc or ""
                                }
                            }
                        }
                        
                        # Apply 40% discount coupon for yearly plans
                        if plan.interval == "year":
                            checkout_params["discounts"] = [{"coupon": "ruxo40"}]
                        
                        try:
                            checkout_session = stripe.checkout.Session.create(**checkout_params)
                            logger.info(f"Checkout session created for new subscription (old one didn't exist in Stripe): {checkout_session.id}")
                            return checkout_session.url
                        except stripe.error.StripeError as checkout_err:
                            logger.error(f"Error creating checkout session: {checkout_err}")
                            raise HTTPException(
                                status_code=400,
                                detail=f"Failed to create checkout session: {str(checkout_err)}"
                            )
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to update subscription: {str(e)}"
                        )
                except stripe.error.StripeError as e:
                    logger.error(f"Stripe error updating subscription {existing_subscription.stripe_subscription_id}: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to update subscription: {str(e)}"
                    )
                
                # Subscription was successfully updated via Stripe API
                if existing_subscription:
                    # Verify the price ID exists in Stripe before creating checkout
                    try:
                        stripe.Price.retrieve(plan.stripe_price_id)
                    except stripe.error.InvalidRequestError as e:
                        if "No such price" in str(e):
                            logger.error(f"Price ID {plan.stripe_price_id} for plan '{plan.name}' does not exist in Stripe. Please update the price ID in the database.")
                            raise HTTPException(
                                status_code=500,
                                detail=f"Invalid price configuration for plan '{plan.display_name}'. Please contact support or update the plan's Stripe price ID in the database."
                            )
                        raise
                    
                    # Apply 40% discount coupon for yearly plans
                    checkout_params = {
                        "payment_method_types": ["card"],
                        "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
                        "mode": "subscription",
                        "customer": customer_id,
                        "success_url": f"{settings.FRONTEND_URL}/",
                        "cancel_url": f"{settings.FRONTEND_URL}/upgrade",
                        "metadata": self._build_checkout_metadata(
                            user_id=str(user.id),
                            plan_id=str(plan.id),
                            plan_name=plan.name,
                            client_ip=client_ip,
                            client_user_agent=client_user_agent,
                            fbp=fbp,
                            fbc=fbc,
                            ttp=ttp,
                            ttclid=ttclid,
                            is_upgrade="true",
                            existing_subscription_id=existing_subscription.stripe_subscription_id
                        ),
                        "subscription_data": {
                            "metadata": {
                                "user_id": str(user.id),
                                "plan_id": str(plan.id),
                                "plan_name": plan.name,
                                "is_upgrade": "true",
                                "existing_subscription_id": existing_subscription.stripe_subscription_id,
                                "client_ip": client_ip or "",
                                "client_user_agent": client_user_agent or "",
                                "fbp": fbp or "",
                                "fbc": fbc or ""
                            }
                        }
                    }
                    
                    # Apply 40% discount coupon for yearly plans
                    if plan.interval == "year":
                        checkout_params["discounts"] = [{"coupon": "ruxo40"}]
                    
                    # Create checkout session for the new plan
                    # Stripe will handle the upgrade and proration
                    try:
                        checkout_session = stripe.checkout.Session.create(**checkout_params)
                        logger.info(f"Checkout session created for upgrade: {checkout_session.id}")
                        return checkout_session.url
                    except stripe.error.InvalidRequestError as e:
                        if "No such price" in str(e):
                            logger.error(f"Price ID {plan.stripe_price_id} for plan '{plan.name}' does not exist in Stripe.")
                            raise HTTPException(
                                status_code=500,
                                detail=f"Invalid price configuration for plan '{plan.display_name}'. The Stripe price ID '{plan.stripe_price_id}' does not exist. Please update the plan's price ID in the database."
                            )
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to create upgrade checkout: {str(e)}"
                        )
            except HTTPException:
                raise
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error during upgrade checkout creation: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to create upgrade checkout: {str(e)}"
                )
        
        # No existing subscription - create new checkout session
        # Note: Webhook secret check is done at webhook endpoint level for security
        # We allow checkout creation here, but webhook will verify signature before processing
        
        # First, ensure no other active subscriptions exist (safety check)
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status.in_(["active", "trialing"])
            )
        )
        other_active_subscriptions = result.scalars().all()
        
        # Cancel any other active subscriptions IMMEDIATELY to ensure only one active subscription
        for old_sub in other_active_subscriptions:
            logger.warning(f"Found unexpected active subscription {old_sub.stripe_subscription_id} for user {user.id}, canceling it immediately")
            try:
                # Cancel the subscription in Stripe IMMEDIATELY (not at period end)
                stripe.Subscription.delete(old_sub.stripe_subscription_id)
                old_sub.status = "canceled"
                old_sub.updated_at = datetime.utcnow()
                self.session.add(old_sub)
                logger.info(f"Immediately canceled subscription {old_sub.stripe_subscription_id} for user {user.id}")
            except stripe.error.StripeError as e:
                error_msg = str(e)
                # If subscription is already canceled or doesn't exist, just update our database
                if "No such subscription" in error_msg or "already been deleted" in error_msg:
                    logger.info(f"Subscription {old_sub.stripe_subscription_id} already canceled in Stripe. Updating database only.")
                    old_sub.status = "canceled"
                    old_sub.updated_at = datetime.utcnow()
                    self.session.add(old_sub)
                else:
                    logger.error(f"Error canceling subscription {old_sub.stripe_subscription_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error canceling subscription {old_sub.stripe_subscription_id}: {e}")
        
        if other_active_subscriptions:
            await self.session.commit()
            logger.info(f"Canceled {len(other_active_subscriptions)} existing subscription(s) for user {user.id}")
        
        # Get or create Stripe customer
        customer_id = await self._get_or_create_customer(user)
        
        # Validate price ID exists in Stripe before creating checkout
        try:
            stripe.Price.retrieve(plan.stripe_price_id)
        except stripe.error.InvalidRequestError as e:
            if "No such price" in str(e):
                logger.error(f"Price ID {plan.stripe_price_id} for plan '{plan.name}' does not exist in Stripe. Please update the price ID in the database.")
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid price configuration for plan '{plan.display_name}'. The Stripe price ID '{plan.stripe_price_id}' does not exist. Please update the plan's price ID in the database."
                )
            raise
        
        # Apply 40% discount coupon for yearly plans
        checkout_params = {
            "payment_method_types": ["card"],
            "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
            "mode": "subscription",
            "customer": customer_id,
            "success_url": f"{settings.FRONTEND_URL}/",
            "cancel_url": f"{settings.FRONTEND_URL}/upgrade",
            "metadata": self._build_checkout_metadata(
                user_id=str(user.id),
                plan_id=str(plan.id),
                plan_name=plan.name,
                client_ip=client_ip,
                client_user_agent=client_user_agent,
                fbp=fbp,
                fbc=fbc,
                ttp=ttp,
                ttclid=ttclid,
            ),
            "subscription_data": {
                "metadata": {
                    "user_id": str(user.id),
                    "plan_id": str(plan.id),
                    "plan_name": plan.name,
                    "client_ip": client_ip or "",
                    "client_user_agent": client_user_agent or "",
                    "fbp": fbp or "",
                    "fbc": fbc or ""
                }
            }
        }
        
        # Apply 40% discount coupon for yearly plans
        if plan.interval == "year":
            checkout_params["discounts"] = [{"coupon": "ruxo40"}]
        
        try:
            checkout_session = stripe.checkout.Session.create(**checkout_params)
            return checkout_session.url
        except stripe.error.InvalidRequestError as e:
            if "No such price" in str(e):
                logger.error(f"Price ID {plan.stripe_price_id} for plan '{plan.name}' does not exist in Stripe.")
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid price configuration for plan '{plan.display_name}'. The Stripe price ID '{plan.stripe_price_id}' does not exist. Please update the plan's price ID in the database."
                )
            raise HTTPException(
                status_code=400,
                detail=f"Failed to create checkout session: {str(e)}"
            )

    async def _get_or_create_customer(self, user: UserProfile) -> str:
        """Get existing Stripe customer or create new one."""
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. Check if user has existing subscription(s) in our database
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        existing_subs = result.scalars().all()
        
        # Find the most recent active subscription with a customer_id, or any subscription with customer_id
        existing_sub = None
        for sub in existing_subs:
            if sub.stripe_customer_id:
                # Prefer active subscriptions
                if sub.status in ["active", "trialing"]:
                    existing_sub = sub
                    break
                # Otherwise use the first one we find
                if not existing_sub:
                    existing_sub = sub
        
        if existing_sub and existing_sub.stripe_customer_id:
            # Verify the customer actually exists in Stripe
            try:
                customer = stripe.Customer.retrieve(existing_sub.stripe_customer_id)
                logger.info(f"Found existing Stripe customer {existing_sub.stripe_customer_id} for user {user.id} (from subscription)")
                return existing_sub.stripe_customer_id
            except stripe.error.StripeError as e:
                # Customer doesn't exist in Stripe, will search by email below
                logger.warning(f"Customer {existing_sub.stripe_customer_id} not found in Stripe: {e}. Will search by email.")
        
        # 2. Search Stripe for existing customer by email (handles abandoned checkouts)
        try:
            existing_customers = stripe.Customer.list(email=user.email, limit=1)
            if existing_customers.data:
                existing_customer = existing_customers.data[0]
                logger.info(f"Found existing Stripe customer {existing_customer.id} for user {user.id} (by email search)")
                
                # Update the customer metadata to include our user_id if not present
                if not existing_customer.metadata.get("user_id"):
                    stripe.Customer.modify(
                        existing_customer.id,
                        metadata={"user_id": str(user.id)}
                    )
                    logger.info(f"Updated customer {existing_customer.id} with user_id metadata")
                
                # If we had a stale subscription record, update it
                if existing_sub:
                    existing_sub.stripe_customer_id = existing_customer.id
                    self.session.add(existing_sub)
                    await self.session.commit()
                
                return existing_customer.id
        except stripe.error.StripeError as e:
            logger.warning(f"Error searching for customer by email: {e}")
        
        # 3. No existing customer found - create new one
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)}
        )
        logger.info(f"Created new Stripe customer {customer.id} for user {user.id}")
        return customer.id

    async def create_portal_session(self, user: UserProfile) -> str:
        # Find stripe customer id - handle multiple subscriptions
        result = await self.session.execute(select(Subscription).where(Subscription.user_id == user.id))
        subscriptions = result.scalars().all()
        
        # Find the most recent active subscription, or any subscription with customer_id
        subscription = None
        for sub in subscriptions:
            if sub.stripe_customer_id:
                # Prefer active subscriptions
                if sub.status in ["active", "trialing"]:
                    subscription = sub
                    break
                # Otherwise use the first one we find
                if not subscription:
                    subscription = sub
        
        if not subscription or not subscription.stripe_customer_id:
             # In real app, create customer if missing or handle error
             raise Exception("No subscription found for user")

        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/upgrade",
        )
        return portal_session.url

    async def handle_webhook(self, event: dict):
        """
        Handle Stripe webhook events.
        
        SECURITY NOTE: This method should ONLY be called after signature verification
        has passed in the webhook router. If signature verification fails, this method
        will never be called, ensuring no plans or credits are granted.
        
        CRITICAL: If STRIPE_WEBHOOK_SECRET is not configured, this method will
        refuse to grant any credits or subscriptions.
        """
        import logging
        from app.core.config import settings
        logger = logging.getLogger(__name__)
        
        # CRITICAL SECURITY CHECK: Never grant credits/subscriptions if webhook secret is not configured
        if not settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET.strip() == "":
            logger.error("SECURITY: STRIPE_WEBHOOK_SECRET is not configured - REFUSING to grant credits or subscriptions")
            logger.error("SECURITY: This webhook will NOT process any events - no credits or subscriptions will be granted")
            raise HTTPException(
                status_code=500,
                detail="Webhook secret not configured - credits and subscriptions cannot be granted"
            )
        
        event_type = event["type"]
        data = event["data"]["object"]
        
        logger.info(f"Processing verified Stripe webhook: {event_type}")
        
        try:
            if event_type == "checkout.session.completed":
                await self._handle_checkout_completed(data)
            elif event_type == "customer.subscription.created":
                await self._handle_subscription_created(data)
            elif event_type == "customer.subscription.updated":
                await self._handle_subscription_updated(data)
            elif event_type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(data)
            elif event_type == "invoice.payment_succeeded":
                await self._handle_invoice_payment_succeeded(data)
            elif event_type == "invoice.payment_failed":
                await self._handle_invoice_payment_failed(data)
            elif event_type == "charge.refunded":
                await self._handle_charge_refunded(data)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
        except Exception as e:
            # Rollback any partial database changes
            await self.session.rollback()
            logger.error(f"Error processing webhook {event_type}: {e}", exc_info=True)
            raise  # Re-raise to be handled by the router

    async def _handle_checkout_completed(self, session):
        """Handle when checkout session is completed."""
        import logging
        logger = logging.getLogger(__name__)
        
        user_id = session.get("metadata", {}).get("user_id")
        if not user_id:
            logger.warning("checkout.session.completed: No user_id in metadata")
            return
        
        logger.info(f"Checkout completed for user {user_id}")
        
        # Get subscription from Stripe
        subscription_id = session.get("subscription")
        if subscription_id:
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            await self._process_subscription(stripe_subscription, uuid.UUID(user_id))
            
            # Track Purchase event for Facebook Conversions API
            try:
                from app.services.facebook_conversions import FacebookConversionsService
                from app.services.tiktok_conversions import TikTokConversionsService
                from app.models.user import UserProfile
                from sqlalchemy.future import select
                
                logger.info("=" * 80)
                logger.info("💰 [PURCHASE TRACKING] Starting Facebook Purchase event tracking")
                
                # Get user profile for email
                result = await self.session.execute(
                    select(UserProfile).where(UserProfile.id == uuid.UUID(user_id))
                )
                user = result.scalar_one_or_none()
                
                if user:
                    # Get plan details for value
                    plan_name = session.get("metadata", {}).get("plan_name")
                    plan_result = await self.session.execute(
                        select(Plan).where(Plan.name == plan_name)
                    )
                    plan = plan_result.scalar_one_or_none()
                    
                    # Calculate value in dollars
                    value = 0.0
                    if plan:
                        value = plan.amount_cents / 100.0
                    
                    # Get amount paid from session (this is the actual amount charged)
                    amount_total = session.get("amount_total", 0)
                    if amount_total:
                        value = amount_total / 100.0
                    
                    currency = session.get("currency", "USD").upper()
                    event_id = session.get("id")  # Use checkout session ID as event_id for deduplication
                    
                    # Get tracking context from session metadata (captured at checkout initiation)
                    metadata = session.get("metadata", {})
                    client_ip = metadata.get("client_ip")
                    client_user_agent = metadata.get("client_user_agent")
                    # Facebook cookies
                    fbp = metadata.get("fbp")
                    fbc = metadata.get("fbc")
                    # TikTok cookies
                    ttp = metadata.get("ttp")
                    ttclid = metadata.get("ttclid")
                    
                    # FALLBACK 1: Check subscription metadata if session metadata is missing
                    if not client_ip and stripe_subscription:
                        sub_metadata = stripe_subscription.get("metadata", {})
                        if sub_metadata.get("client_ip"):
                            logger.info(f"💰 [PURCHASE TRACKING] Using tracking context from subscription metadata")
                            client_ip = sub_metadata.get("client_ip")
                            client_user_agent = sub_metadata.get("client_user_agent")
                            fbp = sub_metadata.get("fbp")
                            fbc = sub_metadata.get("fbc")
                            ttp = sub_metadata.get("ttp")
                            ttclid = sub_metadata.get("ttclid")
                    
                    # FALLBACK 2: If still missing, use last_checkout_* from user profile
                    # This handles cases where subscription was modified directly via Stripe API without checkout
                    if not client_ip and user.last_checkout_ip:
                        logger.info(f"💰 [PURCHASE TRACKING] Using fallback tracking context from user profile")
                        client_ip = user.last_checkout_ip
                        client_user_agent = user.last_checkout_user_agent
                        fbp = user.last_checkout_fbp
                        fbc = user.last_checkout_fbc
                        logger.info(f"💰 [PURCHASE TRACKING] Fallback context age: {datetime.utcnow() - user.last_checkout_timestamp if user.last_checkout_timestamp else 'unknown'}")
                    
                    # Extract first and last name from display_name for better event matching
                    first_name = None
                    last_name = None
                    if user.display_name:
                        name_parts = user.display_name.split(maxsplit=1)
                        first_name = name_parts[0] if name_parts else None
                        last_name = name_parts[1] if len(name_parts) > 1 else None
                    
                    logger.info(f"💰 [PURCHASE TRACKING] User: {user.email} (ID: {user.id})")
                    logger.info(f"💰 [PURCHASE TRACKING] Name: {first_name} {last_name}" if first_name else "💰 [PURCHASE TRACKING] Name: Not available")
                    logger.info(f"💰 [PURCHASE TRACKING] Plan: {plan_name}")
                    logger.info(f"💰 [PURCHASE TRACKING] Value: ${value} {currency}")
                    logger.info(f"💰 [PURCHASE TRACKING] Event ID: {event_id}")
                    logger.info(f"💰 [PURCHASE TRACKING] Event Source URL: {settings.FRONTEND_URL}/")
                    logger.info(f"💰 [PURCHASE TRACKING] Tracking Context: IP={client_ip}, UA={client_user_agent[:50] if client_user_agent else 'None'}...")
                    logger.info(f"💰 [PURCHASE TRACKING] Facebook Cookies: fbp={fbp}, fbc={fbc}")
                    logger.info(f"💰 [PURCHASE TRACKING] TikTok Cookies: ttp={ttp}, ttclid={ttclid}")
                    
                    conversions_service = FacebookConversionsService()
                    tiktok_service = TikTokConversionsService()
                    
                    # Track purchase (fire and forget - don't block response)
                    import asyncio
                    # Facebook tracking
                    asyncio.create_task(conversions_service.track_purchase(
                        value=value,
                        currency=currency,
                        email=user.email,
                        first_name=first_name,
                        last_name=last_name,
                        external_id=str(user.id),
                        client_ip=client_ip,
                        client_user_agent=client_user_agent,
                        fbp=fbp,
                        fbc=fbc,
                        event_source_url=f"{settings.FRONTEND_URL}/",
                        event_id=event_id,
                    ))
                    # TikTok tracking
                    asyncio.create_task(tiktok_service.track_purchase(
                        value=value,
                        currency=currency,
                        email=user.email,
                        first_name=first_name,
                        last_name=last_name,
                        external_id=str(user.id),
                        client_ip=client_ip,
                        client_user_agent=client_user_agent,
                        event_source_url=f"{settings.FRONTEND_URL}/",
                        event_id=event_id,
                        ttp=ttp,
                        ttclid=ttclid,
                    ))
                    logger.info(f"✅ [PURCHASE TRACKING] Purchase event triggered successfully")
                    logger.info("=" * 80)
                else:
                    logger.warning(f"⚠️  [PURCHASE TRACKING] User not found: {user_id}")
            except Exception as e:
                logger.error(f"❌ [PURCHASE TRACKING] Failed to track Purchase event: {str(e)}", exc_info=True)
        else:
            logger.warning(f"Checkout completed but no subscription_id for user {user_id}")

    async def _handle_subscription_created(self, subscription_data):
        """Handle new subscription creation."""
        import logging
        logger = logging.getLogger(__name__)
        
        customer_id = subscription_data.get("customer")
        subscription_id = subscription_data.get("id")
        
        logger.info(f"Subscription created: {subscription_id}, customer: {customer_id}")
        
        # First, try to find existing subscription by subscription_id
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            user_id = existing.user_id
            logger.info(f"Found existing subscription record for user {user_id}")
        else:
            # Try to find by customer_id
            result = await self.session.execute(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                user_id = existing.user_id
                logger.info(f"Found subscription by customer_id for user {user_id}")
            else:
                # Get user_id from Stripe customer metadata
                try:
                    customer = stripe.Customer.retrieve(customer_id)
                    user_id = customer.metadata.get("user_id")
                    if not user_id:
                        logger.warning(f"No user_id in customer {customer_id} metadata")
                        return
                    logger.info(f"Found user_id from customer metadata: {user_id}")
                except Exception as e:
                    logger.error(f"Error retrieving customer {customer_id}: {e}")
                    return
        
        # Handle user_id - it might already be a UUID object from asyncpg
        if isinstance(user_id, uuid.UUID):
            user_uuid = user_id
        else:
            user_uuid = uuid.UUID(str(user_id))
        
        await self._process_subscription(subscription_data, user_uuid)

    async def _handle_subscription_updated(self, subscription_data):
        """Handle subscription updates (plan changes, status changes)."""
        import logging
        logger = logging.getLogger(__name__)
        
        subscription_id = subscription_data.get("id")
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # Get the new plan from Stripe
            price_id = subscription_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
            new_plan = None
            if price_id:
                plan_result = await self.session.execute(
                    select(Plan).where(Plan.stripe_price_id == price_id)
                )
                new_plan = plan_result.scalar_one_or_none()
            
            # Check if plan changed (upgrade/downgrade)
            old_plan_id = subscription.plan_id
            if new_plan and new_plan.id != old_plan_id:
                logger.info(f"Plan changed for subscription {subscription_id}: {old_plan_id} -> {new_plan.id}")
                
                # Remove all existing credits and reset to new plan amount
                wallet = await self.credits_service.get_wallet(subscription.user_id)
                old_balance = wallet.balance_credits
                
                if old_balance > 0:
                    # Remove all existing credits
                    await self.credits_service.spend_credits(
                        user_id=subscription.user_id,
                        amount=old_balance,
                        reason="subscription_upgrade_reset",
                        metadata={"old_plan_id": str(old_plan_id), "new_plan": new_plan.name, "old_balance": old_balance}
                    )
                    logger.info(f"Removed all credits ({old_balance}) for plan change to {new_plan.name}")
                
                # Set credits to new plan amount
                wallet = await self.credits_service.get_wallet(subscription.user_id)  # Refresh wallet
                credits_to_add = new_plan.credits_per_month - wallet.balance_credits
                if credits_to_add > 0:
                    await self.credits_service.add_credits(
                        user_id=subscription.user_id,
                        amount=credits_to_add,
                        reason="subscription_upgrade",
                        metadata={"old_plan_id": str(old_plan_id), "new_plan": new_plan.name, "old_balance": old_balance, "new_balance": new_plan.credits_per_month}
                    )
                    logger.info(f"Set credits to {new_plan.credits_per_month} for plan change to {new_plan.name}")
                
                # Update subscription plan
                subscription.plan_id = new_plan.id
                subscription.plan_name = new_plan.name
            
            # Update subscription status and period
            subscription.status = subscription_data.get("status")
            
            # Safely extract timestamp fields
            period_start_ts = subscription_data.get("current_period_start")
            period_end_ts = subscription_data.get("current_period_end")
            
            if period_start_ts is not None:
                subscription.current_period_start = datetime.fromtimestamp(period_start_ts)
            if period_end_ts is not None:
                subscription.current_period_end = datetime.fromtimestamp(period_end_ts)
            
            subscription.updated_at = datetime.utcnow()
            
            # Check if we need to reset credits (new billing period) - only if plan didn't change
            if not (new_plan and new_plan.id != old_plan_id):
                await self._check_and_reset_credits(subscription)
            
            self.session.add(subscription)
            await self.session.commit()
            
            # Invalidate user cache
            try:
                from app.utils.cache import invalidate_user_cache
                await invalidate_user_cache(str(subscription.user_id))
            except Exception as e:
                logger.error(f"Failed to invalidate user cache: {e}")

    async def _handle_subscription_deleted(self, subscription_data):
        """Handle subscription cancellation - removes all user credits."""
        import logging
        logger = logging.getLogger(__name__)
        
        subscription_id = subscription_data.get("id")
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = "canceled"
            self.session.add(subscription)
            await self.session.commit()
            
            # Invalidate user cache
            try:
                from app.utils.cache import invalidate_user_cache
                await invalidate_user_cache(str(subscription.user_id))
            except Exception as e:
                logger.error(f"Failed to invalidate user cache: {e}")
            
            # Remove all credits when subscription is canceled
            wallet = await self.credits_service.get_wallet(subscription.user_id)
            if wallet.balance_credits > 0:
                # Spend all remaining credits to bring balance to 0
                await self.credits_service.spend_credits(
                    user_id=subscription.user_id,
                    amount=wallet.balance_credits,
                    reason="subscription_canceled",
                    metadata={"subscription_id": str(subscription.id), "old_balance": wallet.balance_credits}
                )
                logger.info(f"Removed all credits ({wallet.balance_credits}) for user {subscription.user_id} due to subscription cancellation")

    async def _handle_invoice_payment_succeeded(self, invoice_data):
        """Handle successful invoice payment.
        
        For monthly plans: Invoice is sent monthly, reset credits
        For yearly plans: Invoice is sent yearly, but we still check if monthly reset is needed
        """
        subscription_id = invoice_data.get("subscription")
        if not subscription_id:
            return
        
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if subscription and subscription.status == "active":
            # Use _check_and_reset_credits which handles both monthly and yearly plans correctly
            await self._check_and_reset_credits(subscription)

    async def _handle_invoice_payment_failed(self, invoice_data):
        """Handle failed invoice payment."""
        subscription_id = invoice_data.get("subscription")
        if subscription_id:
            result = await self.session.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            if subscription:
                subscription.status = "past_due"
                self.session.add(subscription)
                await self.session.commit()

    async def _handle_charge_refunded(self, charge_data):
        """Handle charge refund - wipe user credits and cancel subscription."""
        import logging
        logger = logging.getLogger(__name__)
        
        charge_id = charge_data.get("id")
        customer_id = charge_data.get("customer")
        
        logger.info(f"Processing charge.refunded webhook: charge_id={charge_id}, customer_id={customer_id}")
        
        if not customer_id:
            logger.warning(f"charge.refunded: No customer_id in charge data for charge {charge_id}")
            return
        
        # Find subscription by customer_id
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == customer_id,
                Subscription.status == "active"
            )
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            logger.warning(f"charge.refunded: No active subscription found for customer {customer_id}")
            return
        
        user_id = subscription.user_id
        logger.info(f"charge.refunded: Found active subscription {subscription.stripe_subscription_id} for user {user_id}")
        
        # Wipe all user credits
        wallet = await self.credits_service.get_wallet(user_id)
        if wallet.balance_credits > 0:
            old_balance = wallet.balance_credits
            # Spend all remaining credits to bring balance to 0
            await self.credits_service.spend_credits(
                user_id=user_id,
                amount=wallet.balance_credits,
                reason="charge_refunded",
                metadata={
                    "charge_id": charge_id,
                    "subscription_id": str(subscription.id),
                    "old_balance": old_balance,
                    "refund_reason": "charge_refunded_webhook"
                }
            )
            logger.info(f"charge.refunded: Wiped all credits ({old_balance}) for user {user_id}")
        else:
            logger.info(f"charge.refunded: User {user_id} already has 0 credits")
        
        # Cancel subscription in Stripe and database
        try:
            # Cancel the subscription in Stripe immediately
            stripe.Subscription.delete(subscription.stripe_subscription_id)
            logger.info(f"charge.refunded: Canceled subscription {subscription.stripe_subscription_id} in Stripe")
        except stripe.error.StripeError as stripe_error:
            # If subscription is already canceled or doesn't exist, just update our database
            if stripe_error.code == "resource_missing":
                logger.info(f"charge.refunded: Subscription {subscription.stripe_subscription_id} already canceled in Stripe. Updating database only.")
            else:
                logger.warning(f"charge.refunded: Stripe error canceling subscription {subscription.stripe_subscription_id}: {stripe_error}. Updating database only.")
        except Exception as e:
            logger.error(f"charge.refunded: Unexpected error canceling subscription {subscription.stripe_subscription_id}: {e}")
        
        # Update subscription status in database
        subscription.status = "canceled"
        self.session.add(subscription)
        await self.session.commit()
        
        # Invalidate user cache
        try:
            from app.utils.cache import invalidate_user_cache
            await invalidate_user_cache(str(user_id))
        except Exception as e:
            logger.error(f"Failed to invalidate user cache: {e}")
        
        logger.info(f"charge.refunded: Successfully processed refund for user {user_id} - credits wiped and subscription canceled")

    async def _process_subscription(self, stripe_subscription: dict, user_id: uuid.UUID):
        """Process subscription: create/update subscription record and add credits.
        
        Ensures user only has one active subscription at a time by canceling any existing
        active subscriptions before creating/updating the new one.
        
        SECURITY: This method should ONLY be called from verified webhook handlers.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # CRITICAL SECURITY CHECK: Never grant subscriptions if webhook secret is not configured
        if not settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET.strip() == "":
            logger.error(f"SECURITY: STRIPE_WEBHOOK_SECRET is not configured - REFUSING to grant subscription for user {user_id}")
            raise HTTPException(
                status_code=500,
                detail="Webhook secret not configured - subscriptions cannot be granted"
            )
        
        subscription_id = stripe_subscription.get("id")
        customer_id = stripe_subscription.get("customer")
        subscription_status = stripe_subscription.get("status")
        
        logger.info(f"Processing subscription {subscription_id} for user {user_id}")
        
        # Get plan from Stripe price
        price_id = stripe_subscription.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
        if not price_id:
            logger.warning(f"No price_id found in subscription {subscription_id}")
            return
        
        # Find plan in database
        result = await self.session.execute(
            select(Plan).where(Plan.stripe_price_id == price_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            logger.warning(f"Plan not found for price_id {price_id}")
            return
        
        logger.info(f"Found plan: {plan.name} with {plan.credits_per_month} credits/month")
        
        # Check if subscription already exists
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        # If this is a new active subscription, cancel any other active subscriptions for this user IMMEDIATELY
        # This ensures users can only have one active subscription at a time
        if subscription_status in ["active", "trialing"] and (not subscription or subscription.stripe_subscription_id != subscription_id):
            result = await self.session.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.status.in_(["active", "trialing"]),
                    Subscription.stripe_subscription_id != subscription_id  # Exclude the current subscription
                )
            )
            existing_active_subscriptions = result.scalars().all()
            
            for old_sub in existing_active_subscriptions:
                logger.info(f"Canceling existing subscription {old_sub.stripe_subscription_id} for user {user_id} immediately to ensure only one active subscription")
                try:
                    # Cancel the subscription in Stripe IMMEDIATELY (not at period end)
                    stripe.Subscription.delete(old_sub.stripe_subscription_id)
                    # Update status in our database
                    old_sub.status = "canceled"
                    old_sub.updated_at = datetime.utcnow()
                    self.session.add(old_sub)
                    logger.info(f"Immediately canceled subscription {old_sub.stripe_subscription_id} in Stripe and database")
                except Exception as stripe_error:
                    # If subscription is already canceled or doesn't exist, just update our database
                    error_msg = str(stripe_error)
                    if "No such subscription" in error_msg or "already been deleted" in error_msg:
                        logger.info(f"Subscription {old_sub.stripe_subscription_id} already canceled in Stripe. Updating database only.")
                    else:
                        logger.warning(f"Stripe error canceling subscription {old_sub.stripe_subscription_id}: {stripe_error}. Updating database only.")
                    old_sub.status = "canceled"
                    old_sub.updated_at = datetime.utcnow()
                    self.session.add(old_sub)
                except Exception as e:
                    logger.error(f"Error canceling subscription {old_sub.stripe_subscription_id}: {e}")
            
            if existing_active_subscriptions:
                await self.session.commit()
        
        # Safely extract timestamp fields (handle None values)
        period_start_ts = stripe_subscription.get("current_period_start")
        period_end_ts = stripe_subscription.get("current_period_end")
        
        # If timestamps are missing, fetch the full subscription from Stripe
        if period_start_ts is None or period_end_ts is None:
            logger.warning(f"Subscription {subscription_id} missing period timestamps, fetching from Stripe...")
            try:
                full_subscription = stripe.Subscription.retrieve(subscription_id)
                period_start_ts = full_subscription.get("current_period_start")
                period_end_ts = full_subscription.get("current_period_end")
                # Update the subscription_data with the full data
                stripe_subscription = full_subscription
                logger.info(f"Retrieved full subscription data from Stripe: start={period_start_ts}, end={period_end_ts}")
            except Exception as e:
                logger.error(f"Error fetching subscription {subscription_id} from Stripe: {e}")
                raise ValueError(f"Subscription {subscription_id} is missing required period timestamps and could not be fetched from Stripe")
        
        if period_start_ts is None or period_end_ts is None:
            logger.error(f"Subscription {subscription_id} still missing period timestamps after fetch: start={period_start_ts}, end={period_end_ts}")
            raise ValueError(f"Subscription {subscription_id} is missing required period timestamps")
        
        current_period_start = datetime.fromtimestamp(period_start_ts)
        current_period_end = datetime.fromtimestamp(period_end_ts)
        now = datetime.utcnow()
        
        if subscription:
            # Update existing subscription
            subscription.plan_id = plan.id
            subscription.plan_name = plan.name
            subscription.status = stripe_subscription.get("status")
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
            subscription.updated_at = now
        else:
            # Create new subscription
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan_name=plan.name,
                status=stripe_subscription.get("status"),
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                last_credit_reset=now,
                created_at=now,
                updated_at=now,  # Explicitly set updated_at
            )
        
        self.session.add(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        
        # Invalidate user cache so frontend updates immediately (e.g. hide timer)
        try:
            from app.utils.cache import invalidate_user_cache
            await invalidate_user_cache(str(user_id))
            logger.info(f"Invalidated user cache for {user_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate user cache: {e}")
        
        # Reset credits to plan amount (monthly reset)
        await self._reset_monthly_credits(subscription)

    async def _check_and_reset_credits(self, subscription: Subscription):
        """Check if credits need to be reset based on billing period.
        
        For monthly plans: Reset when billing period changes (monthly)
        For yearly plans: Reset every month (not just when billing period changes)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not subscription.last_credit_reset:
            subscription.last_credit_reset = subscription.current_period_start
            self.session.add(subscription)
            await self.session.commit()
            return
        
        # Get plan to check interval
        if not subscription.plan_id:
            return
        
        result = await self.session.execute(
            select(Plan).where(Plan.id == subscription.plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            return
        
        # Normalize datetimes to avoid offset-naive vs offset-aware comparison
        last_reset = subscription.last_credit_reset
        now = datetime.utcnow()
        
        # Make both timezone-aware or both naive for comparison
        if now.tzinfo is None and last_reset.tzinfo is not None:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        elif now.tzinfo is not None and last_reset.tzinfo is None:
            from datetime import timezone
            last_reset = last_reset.replace(tzinfo=timezone.utc)
        
        # For yearly plans: reset credits every month (not just when billing period changes)
        if plan.interval == "year":
            # Check if a month has passed since last reset
            # Calculate months difference
            months_since_reset = (now.year - last_reset.year) * 12 + (now.month - last_reset.month)
            
            # Also check if at least 30 days have passed (more reliable than just month difference)
            days_since_reset = (now - last_reset).days
            
            logger.info(f"[YEARLY PLAN CHECK] User {subscription.user_id}: Months: {months_since_reset}, Days: {days_since_reset}, Last reset: {last_reset}, Now: {now}")
            
            if months_since_reset >= 1 or days_since_reset >= 30:
                logger.info(f"[YEARLY PLAN RESET] User {subscription.user_id}: {months_since_reset} month(s) / {days_since_reset} day(s) since last reset, resetting credits")
                # Skip webhook check for scheduler calls (internal, trusted)
                await self._reset_monthly_credits(subscription, skip_webhook_check=True)
            else:
                logger.info(f"[YEARLY PLAN SKIP] User {subscription.user_id}: Not yet time to reset (months: {months_since_reset}, days: {days_since_reset})")
        else:
            # For monthly plans: reset when billing period changes
            # Note: Monthly plans are handled by Stripe webhooks, not the scheduler
            # The scheduler only handles yearly plans that need monthly resets
            period_start = subscription.current_period_start
            
            # Make both timezone-aware or both naive for comparison
            if period_start.tzinfo is None and last_reset.tzinfo is not None:
                from datetime import timezone
                period_start = period_start.replace(tzinfo=timezone.utc)
            elif period_start.tzinfo is not None and last_reset.tzinfo is None:
                from datetime import timezone
                last_reset = last_reset.replace(tzinfo=timezone.utc)
            
            if period_start > last_reset:
                logger.info(f"Monthly plan user {subscription.user_id}: new billing period started, resetting credits")
                # Monthly plans should be handled by webhooks, but allow scheduler as fallback
                await self._reset_monthly_credits(subscription, skip_webhook_check=True)

    async def _reset_monthly_credits(self, subscription: Subscription, skip_webhook_check: bool = False):
        """Reset user's credits to the plan's monthly amount.
        
        SECURITY: This method should ONLY be called from verified webhook handlers or the scheduler.
        
        Args:
            subscription: The subscription to reset credits for
            skip_webhook_check: If True, skip the webhook secret check (for internal scheduler use)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[RESET CREDITS] Starting credit reset for subscription {subscription.id}, user {subscription.user_id}")
        
        # CRITICAL SECURITY CHECK: Never grant credits if webhook secret is not configured
        # Skip this check only when called from the scheduler (internal, trusted)
        if not skip_webhook_check:
            if not settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET.strip() == "":
                logger.error(f"SECURITY: STRIPE_WEBHOOK_SECRET is not configured - REFUSING to grant credits for user {subscription.user_id}")
                raise HTTPException(
                    status_code=500,
                    detail="Webhook secret not configured - credits cannot be granted"
                )
        
        if not subscription.plan_id:
            logger.warning(f"Subscription {subscription.id} has no plan_id")
            return
        
        # Get plan
        result = await self.session.execute(
            select(Plan).where(Plan.id == subscription.plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            logger.warning(f"Plan not found for subscription {subscription.id}")
            return
        
        # Get current wallet
        wallet = await self.credits_service.get_wallet(subscription.user_id)
        
        # Reset credits: set to plan amount (not add, but replace)
        old_balance = wallet.balance_credits
        
        logger.info(f"[RESET CREDITS] User {subscription.user_id}: Resetting credits from {old_balance} to {plan.credits_per_month} (plan: {plan.name})")
        
        # Set balance to plan's monthly credits
        wallet.balance_credits = plan.credits_per_month
        
        # Record transaction
        from app.models.credits import CreditTransaction
        credit_amount = plan.credits_per_month - old_balance
        transaction = CreditTransaction(
            user_id=subscription.user_id,
            amount=abs(credit_amount),
            direction="credit" if credit_amount > 0 else "debit",
            reason="subscription_renewal",
            metadata_json=f'{{"plan_name": "{plan.name}", "old_balance": {old_balance}, "new_balance": {plan.credits_per_month}}}'
        )
        
        logger.info(f"Resetting credits for user {subscription.user_id}: {old_balance} -> {plan.credits_per_month} (plan: {plan.name})")
        
        self.session.add(transaction)
        self.session.add(wallet)
        
        # Update subscription's last reset time
        subscription.last_credit_reset = datetime.utcnow()
        self.session.add(subscription)
        
        await self.session.commit()
        logger.info(f"Credits reset successfully for user {subscription.user_id}")
