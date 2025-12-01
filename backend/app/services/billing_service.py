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
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        ga_client_id: Optional[str] = None,
        ga_session_id: Optional[str] = None,
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
            # Also add click_id alias
            metadata["click_id"] = ttclid
        # Google Ads parameters
        if gclid:
            metadata["gclid"] = gclid
        if gbraid:
            metadata["gbraid"] = gbraid
        if wbraid:
            metadata["wbraid"] = wbraid
        # GA4 parameters
        if ga_client_id:
            metadata["ga_client_id"] = ga_client_id
        if ga_session_id:
            metadata["ga_session_id"] = ga_session_id
        
        # Add any extra metadata (e.g., is_upgrade, existing_subscription_id)
        metadata.update(extra_metadata)
        
        return metadata

    async def create_checkout_session(
        self,
        user: UserProfile,
        plan_name: str,
        skip_trial: bool = False,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None,
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        ga_client_id: Optional[str] = None,
        ga_session_id: Optional[str] = None
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
        if existing_subscription and not skip_trial:
            # Check if this is an admin subscription (manually granted, starts with "admin_")
            is_admin_subscription = existing_subscription.stripe_subscription_id.startswith("admin_")
            
            # Check if user is trying to select the same plan they already have
            # FIX: Compare full plan names to allow switching intervals (e.g. monthly -> yearly)
            # current_plan_key = existing_subscription.plan_name.split('_')[0] 
            # new_plan_key = plan_name.split('_')[0]
            is_same_plan = existing_subscription.plan_name == plan_name
            
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
            
            # FORCE skip_trial=True since they already have a subscription (active or trial)
            # This ensures they pay full price immediately for the new plan
            skip_trial = True
            
            # PROCEED TO CHECKOUT CREATION
            # We do NOT cancel the old subscription immediately.
            # We create a new Checkout Session for the new plan.
            # When the user pays and the new subscription activates, the webhook logic (in _process_subscription)
            # will automatically detect and cancel the old subscription ("Single Active Subscription" rule).
            
        # No existing subscription (or upgrading) - create new checkout session
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
        
        # If skipping trial or upgrading, don't cancel existing subscriptions immediately (let webhook do it after payment)
        is_upgrade = existing_subscription is not None
        if skip_trial or is_upgrade:
            other_active_subscriptions = []
        
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
        
        # Get the product for this plan (needed for trial price and discounted price)
        product_id = None
        try:
            plan_price = stripe.Price.retrieve(plan.stripe_price_id)
            product_id = plan_price.product if isinstance(plan_price.product, str) else plan_price.product.id
        except Exception as e:
            logger.warning(f"Could not retrieve plan price to get product ID: {e}")
        
        # Create or get trial price ($1 one-time payment)
        # According to Stripe docs: "Trial periods can be combined with one time prices"
        # The one-time item will be invoiced immediately at the start of the trial
        trial_price_id = None
        if product_id:
            try:
                # Check if a trial price already exists for this product (reuse to avoid creating many prices)
                existing_prices = stripe.Price.list(
                    product=product_id,
                    active=True,
                    limit=100
                )
                # Look for existing $1 one-time price
                for price in existing_prices.data:
                    if (price.type == 'one_time' and 
                        price.unit_amount == plan.trial_amount_cents and 
                        price.currency == 'usd'):
                        trial_price_id = price.id
                        logger.info(f"Reusing existing trial price {trial_price_id} for plan {plan.name}")
                        break
                
                # If no existing price found, create a new one
                if not trial_price_id:
                    trial_price = stripe.Price.create(
                        unit_amount=plan.trial_amount_cents,  # $1.00
                        currency="usd",
                        product=product_id,
                    )
                    trial_price_id = trial_price.id
                    logger.info(f"Created new trial price {trial_price_id} for plan {plan.name}")
            except Exception as e:
                logger.warning(f"Could not create/get trial price, will use subscription trial only: {e}")
        
        # For yearly plans, create a discounted price (40% off) to avoid applying discount to trial fee
        # This way the discount only applies to the subscription, not the $1 trial fee
        # According to Stripe docs, discounts at checkout level apply to all items, so we pre-discount the subscription price
        subscription_price_id = plan.stripe_price_id
        if plan.interval == "year" and trial_price_id and product_id:
            # Calculate discounted price (40% off = 60% of original)
            discounted_amount = int(plan.amount_cents * 0.6)
            try:
                # Check if a discounted price already exists (reuse to avoid creating many prices)
                existing_prices = stripe.Price.list(
                    product=product_id,
                    active=True,
                    limit=100
                )
                # Look for existing discounted yearly price
                for price in existing_prices.data:
                    if (price.type == 'recurring' and 
                        price.recurring and 
                        price.recurring.interval == plan.interval and
                        price.unit_amount == discounted_amount and 
                        price.currency == 'usd'):
                        subscription_price_id = price.id
                        logger.info(f"Reusing existing discounted price {subscription_price_id} for yearly plan {plan.name}")
                        break
                
                # If no existing discounted price found, create a new one
                if subscription_price_id == plan.stripe_price_id:
                    discounted_price = stripe.Price.create(
                        product=product_id,
                        unit_amount=discounted_amount,
                        currency="usd",
                        recurring={
                            "interval": plan.interval,
                        },
                    )
                    subscription_price_id = discounted_price.id
                    logger.info(f"Created new discounted price {subscription_price_id} for yearly plan {plan.name} (${discounted_amount/100} instead of ${plan.amount_cents/100})")
            except Exception as e:
                logger.warning(f"Could not create/get discounted price, will use original price: {e}")
                # Fall back to using coupon (which will apply to both, but better than failing)
        
        # Build line items: trial fee ($1) + subscription (if not skipping trial)
        # If skipping trial, only add subscription price
        line_items = []
        if not skip_trial and trial_price_id:
            line_items.append({"price": trial_price_id, "quantity": 1})  # $1 trial fee (charged immediately, no discount)
        
        line_items.append({"price": subscription_price_id, "quantity": 1})  # Subscription (with discount already applied if yearly)
        
        # Build subscription_data - conditionally include trial_period_days
        subscription_data = {
            "metadata": {
                "user_id": str(user.id),
                "plan_id": str(plan.id),
                "plan_name": plan.name,
                "client_ip": client_ip or "",
                "client_user_agent": client_user_agent or "",
                "fbp": fbp or "",
                "fbc": fbc or "",
                "ttp": ttp or "",
                "ttclid": ttclid or "",
                "gclid": gclid or "",
                "gbraid": gbraid or "",
                "wbraid": wbraid or "",
                "ga_client_id": ga_client_id or "",
                "ga_session_id": ga_session_id or ""
            }
        }
        
        # Only add trial period if not skipping trial
        if not skip_trial:
            subscription_data["trial_period_days"] = plan.trial_days  # 3-day trial
        
        # Apply 40% discount coupon for yearly plans (only if we didn't create a discounted price)
        # This applies to all line items, so we avoid it when we have a trial fee
        checkout_params = {
            "payment_method_types": ["card"],
            "line_items": line_items,
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
                gclid=gclid,
                gbraid=gbraid,
                wbraid=wbraid,
                ga_client_id=ga_client_id,
                ga_session_id=ga_session_id,
            ),
            "subscription_data": subscription_data,
        }
        
        # Customize button text based on whether skipping trial
        if not skip_trial:
            checkout_params["custom_text"] = {
                "submit": {
                    "message": "Start trial"
                }
            }
        
        # Only apply coupon discount if we don't have a trial fee (to avoid discounting the $1 fee)
        # OR if we couldn't create a discounted price
        if plan.interval == "year" and not trial_price_id:
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
                
                # Check if customer is marked as deleted in Stripe
                if hasattr(customer, 'deleted') and customer.deleted:
                    logger.warning(f"Customer {existing_sub.stripe_customer_id} is marked as deleted in Stripe. Will create new customer.")
                    # Fall through to email search/creation
                else:
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
            # ONLY track if active (paid) and NOT a trial (trials are handled in _grant_trial_credits with StartTrial event)
            
            # Check if it's effectively a trial (status='trialing' OR has future trial_end)
            # This matches logic in _process_subscription to prevent double tracking
            is_trial = stripe_subscription.status == "trialing"
            if not is_trial and stripe_subscription.get("trial_end"):
                try:
                    if float(stripe_subscription.get("trial_end")) > time.time():
                        is_trial = True
                except (ValueError, TypeError):
                    pass

            # Only track purchase if subscription is ACTIVE (paid) and NOT a trial
            # This prevents tracking on 'incomplete' or 'past_due' subscriptions
            if stripe_subscription.status == "active" and not is_trial:
                try:
                    from app.services.facebook_conversions import FacebookConversionsService
                    from app.services.tiktok_conversions import TikTokConversionsService
                    from app.services.ga4_service import GA4Service
                    from app.models.user import UserProfile
                    from sqlalchemy.future import select
                    
                    logger.info("=" * 80)
                    logger.info("💰 [PURCHASE TRACKING] Starting Purchase event tracking")
                    
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
                        # Google Ads parameters
                        gclid = metadata.get("gclid")
                        gbraid = metadata.get("gbraid")
                        wbraid = metadata.get("wbraid")
                        # GA4 parameters
                        ga_client_id = metadata.get("ga_client_id")
                        ga_session_id = metadata.get("ga_session_id")
                        
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
                                gclid = sub_metadata.get("gclid")
                                gbraid = sub_metadata.get("gbraid")
                                wbraid = sub_metadata.get("wbraid")
                                ga_client_id = sub_metadata.get("ga_client_id")
                                ga_session_id = sub_metadata.get("ga_session_id")
                        
                        # FALLBACK 2: If still missing, use last_checkout_* from user profile
                        # This handles cases where subscription was modified directly via Stripe API without checkout
                        if not client_ip and user.last_checkout_ip:
                            logger.info(f"💰 [PURCHASE TRACKING] Using fallback tracking context from user profile")
                            client_ip = user.last_checkout_ip
                            client_user_agent = user.last_checkout_user_agent
                            fbp = user.last_checkout_fbp
                            fbc = user.last_checkout_fbc
                            ga_client_id = user.last_checkout_ga_client_id
                            ga_session_id = user.last_checkout_ga_session_id
                            # Note: we don't currently store last_checkout_gclid on user model, but we could
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
                        logger.info(f"💰 [PURCHASE TRACKING] GA4: client_id={ga_client_id}, session_id={ga_session_id}")
                        
                        conversions_service = FacebookConversionsService()
                        tiktok_service = TikTokConversionsService()
                        ga4_service = GA4Service()
                        
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
                        # GA4 tracking
                        if ga_client_id:
                            asyncio.create_task(ga4_service.track_purchase(
                                client_id=ga_client_id,
                                transaction_id=event_id,
                                value=value,
                                currency=currency,
                                user_id=str(user.id),
                                session_id=ga_session_id,
                                client_ip=client_ip,
                                user_agent=client_user_agent,
                                page_location=f"{settings.FRONTEND_URL}/",
                                items=[{"item_id": plan_name, "item_name": plan_name, "price": value, "quantity": 1}]
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
        # Use scalars().first() instead of scalar_one_or_none() to handle potential duplicates gracefully
        existing = result.scalars().first()
        
        if existing:
            user_id = existing.user_id
            logger.info(f"Found existing subscription record for user {user_id}")
        else:
            # Try to find by customer_id
            result = await self.session.execute(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            )
            existing = result.scalars().first()
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
            old_status = subscription.status
            new_status = subscription_data.get("status")
            subscription.status = new_status
            
            # Safely extract timestamp fields
            period_start_ts = subscription_data.get("current_period_start")
            period_end_ts = subscription_data.get("current_period_end")
            
            if period_start_ts is not None:
                subscription.current_period_start = datetime.fromtimestamp(period_start_ts)
            if period_end_ts is not None:
                subscription.current_period_end = datetime.fromtimestamp(period_end_ts)
            
            subscription.updated_at = datetime.utcnow()
            
            # Handle trial to active transition - switch to actual plan and grant full credits
            if old_status == "trialing" and new_status == "active":
                logger.info(f"Subscription {subscription.stripe_subscription_id} transitioned from trial to active - switching to actual plan")
                
                # Get the actual plan from Stripe subscription (not free_trial)
                # For trial conversions, Stripe usually updates the subscription to the real price ID
                price_id = subscription_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
                
                # If price_id is still missing or looks like trial, try to use plan_id from metadata
                actual_plan = None
                
                # 1. Try fetching plan by price_id
                if price_id:
                    plan_result = await self.session.execute(
                        select(Plan).where(Plan.stripe_price_id == price_id, Plan.name != "free_trial")
                    )
                    actual_plan = plan_result.scalar_one_or_none()
                
                # 2. If not found (e.g. Stripe hasn't updated items yet or using same price ID), use metadata
                if not actual_plan:
                    # Try to get plan from metadata which we store at creation time
                    plan_id_str = subscription.plan_id
                    if plan_id_str:
                        plan_result = await self.session.execute(
                            select(Plan).where(Plan.id == plan_id_str)
                        )
                        current_db_plan = plan_result.scalar_one_or_none()
                        
                        # If current plan in DB is NOT free_trial, use it (it's the real plan)
                        if current_db_plan and current_db_plan.name != "free_trial":
                            actual_plan = current_db_plan
                            logger.info(f"Using existing plan from DB: {actual_plan.name}")
                        
                        # If it IS free_trial (or null), try to find the real plan from metadata
                        # (This handles cases where we saved the real plan ID in metadata during checkout)
                        # BUT we don't have easy access to metadata here unless we fetch from Stripe
                        # Let's rely on the fact that _process_subscription sets the real plan ID initially
                
                if actual_plan:
                    # Switch from free_trial to actual plan (if needed)
                    if subscription.plan_id != actual_plan.id:
                        subscription.plan_id = actual_plan.id
                        subscription.plan_name = actual_plan.name
                        self.session.add(subscription)
                        await self.session.commit()
                    
                    # Grant full plan credits (replacing trial credits)
                    await self._reset_monthly_credits(subscription, skip_webhook_check=True)
                    logger.info(f"Switched to {actual_plan.name} and granted full plan credits ({actual_plan.credits_per_month}) to user {subscription.user_id} after trial ended")
                    
                    # TRACKING REMOVED: Trial conversion tracking is now handled by _handle_invoice_payment_succeeded
                    # This prevents duplicate events when both invoice.payment_succeeded and customer.subscription.updated fire.
            
            # Handle trial expiration without conversion - remove credits and cancel
            if old_status == "trialing" and new_status in ["canceled", "unpaid", "past_due"]:
                logger.info(f"Subscription {subscription.stripe_subscription_id} trial ended without conversion - removing trial credits")
                
                # Remove all trial credits (they expire after 3 days)
                wallet = await self.credits_service.get_wallet(subscription.user_id)
                if wallet.balance_credits > 0:
                    old_balance = wallet.balance_credits
                    await self.credits_service.spend_credits(
                        user_id=subscription.user_id,
                        amount=wallet.balance_credits,
                        reason="trial_expired",
                        metadata={
                            "subscription_id": str(subscription.id),
                            "old_balance": old_balance,
                            "trial_ended": True
                        }
                    )
                    logger.info(f"Removed {old_balance} trial credits from user {subscription.user_id} - trial expired without conversion")
            
            # Check if we need to reset credits (new billing period) - only if plan didn't change and not transitioning from trial
            if not (new_plan and new_plan.id != old_plan_id) and not (old_status == "trialing" and new_status == "active"):
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
        """Handle subscription cancellation - removes all user credits.
        
        If subscription was in trial, this means trial expired without conversion.
        Trial credits (70) expire after 3 days.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        subscription_id = subscription_data.get("id")
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            was_trial = subscription.status == "trialing"
            subscription.status = "canceled"
            self.session.add(subscription)
            await self.session.commit()
            
            # Invalidate user cache
            try:
                from app.utils.cache import invalidate_user_cache
                await invalidate_user_cache(str(subscription.user_id))
            except Exception as e:
                logger.error(f"Failed to invalidate user cache: {e}")
            
            # Check if the user has another active subscription
            # If they do, we should NOT wipe their credits
            result = await self.session.execute(
                select(Subscription).where(
                    Subscription.user_id == subscription.user_id,
                    Subscription.status.in_(["active", "trialing"]),
                    Subscription.id != subscription.id
                )
            )
            other_active_subscription = result.scalar_one_or_none()
            
            if other_active_subscription:
                logger.info(f"Subscription {subscription.id} canceled, but user {subscription.user_id} has another active subscription {other_active_subscription.id}. Preserving credits.")
                return

            # Remove all credits when subscription is canceled
            # If it was a trial, credits expire after 3 days
            wallet = await self.credits_service.get_wallet(subscription.user_id)
            if wallet.balance_credits > 0:
                reason = "trial_expired" if was_trial else "subscription_canceled"
                # Spend all remaining credits to bring balance to 0
                await self.credits_service.spend_credits(
                    user_id=subscription.user_id,
                    amount=wallet.balance_credits,
                    reason=reason,
                    metadata={
                        "subscription_id": str(subscription.id), 
                        "old_balance": wallet.balance_credits,
                        "was_trial": was_trial,
                        "trial_expired": was_trial
                    }
                )
                logger.info(f"Removed all credits ({wallet.balance_credits}) for user {subscription.user_id} - {'trial expired' if was_trial else 'subscription canceled'}")

    async def _handle_invoice_payment_succeeded(self, invoice_data):
        """Handle successful invoice payment.
        
        For monthly plans: Invoice is sent monthly, reset credits
        For yearly plans: Invoice is sent yearly, but we still check if monthly reset is needed
        """
        import logging
        logger = logging.getLogger(__name__)
        
        subscription_id = invoice_data.get("subscription")
        customer_id = invoice_data.get("customer")
        billing_reason = invoice_data.get("billing_reason")
        amount_paid = invoice_data.get("amount_paid", 0)
        invoice_id = invoice_data.get("id")
        
        logger.info(f"🧾 [INVOICE HANDLER] Processing invoice {invoice_id} for subscription {subscription_id}")
        logger.info(f"   Reason: {billing_reason}, Amount: {amount_paid}")

        # Try to find subscription
        subscription = None
        
        # 1. Try by subscription ID if present
        if subscription_id:
            result = await self.session.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            
        # 2. Fallback: Try by customer ID if subscription not found
        if not subscription and customer_id:
            logger.info(f"   Subscription ID {subscription_id} missing or not found. Attempting fallback via customer_id: {customer_id}")
            # Find most recent active/trialing subscription for this customer
            result = await self.session.execute(
                select(Subscription).where(
                    Subscription.stripe_customer_id == customer_id,
                    Subscription.status.in_(["active", "trialing", "past_due", "incomplete"])
                ).order_by(Subscription.created_at.desc())
            )
            subscription = result.scalars().first()
        
        if not subscription:
            logger.warning(f"   Skipping: Subscription not found for invoice {invoice_id} (sub: {subscription_id}, cust: {customer_id})")
            return

        logger.info(f"   Found subscription {subscription.id}, status: {subscription.status}")
        
        if subscription and subscription.status in ["active", "trialing", "past_due", "incomplete"]:
            # Force credit reset on successful payment (user paid -> user gets credits)
            # This ensures credits are filled up immediately upon payment receipt,
            # bypassing any potential timing issues with _check_and_reset_credits.
            
            # MODIFIED: Don't reset credits if it's a trial subscription (trial credits are handled separately)
            if subscription.status == "trialing":
                 logger.info(f"Invoice paid for subscription {subscription.id} but status is 'trialing' - skipping full credit reset (handled by trial logic)")
            else:
                logger.info(f"Invoice paid for subscription {subscription.id} (status: {subscription.status}) - forcing credit reset to full plan amount")
                await self._reset_monthly_credits(subscription, skip_webhook_check=True)
            
            # --- TRACK PURCHASE EVENT FOR RENEWALS (Monthly/Yearly) ---
            # Note: This event fires for every successful invoice payment (renewals)
            # We want to track this as a Purchase event in ad platforms to optimize for LTV/retention
            try:
                # Track ALL successful invoice payments as purchases (renewals, trial conversions, etc.)
                # Invoice billing_reason: subscription_create, subscription_cycle, subscription_update
                
                # DEDUPLICATION FIX: Skip 'subscription_create' because it is already handled by checkout.session.completed
                # (for non-trials) or _grant_trial_credits (for trials - triggering StartTrial).
                # We only want to track RECURRING payments (renewals) or manual updates here.
                if billing_reason == "subscription_create":
                    logger.info(f"💰 [INVOICE PAYMENT] Skipping Purchase tracking for subscription_create (handled by checkout/trial logic)")
                else:
                    # Only track 'subscription_cycle' (renewals) and 'subscription_update' here. 
                    # 'subscription_create' is handled by checkout.session.completed
                    # 'subscription_update' might be handled by customer.subscription.updated
                    # We expand this to track ANY payment that results in money charged
                    
                    if amount_paid > 0:
                        from app.services.facebook_conversions import FacebookConversionsService
                        from app.services.tiktok_conversions import TikTokConversionsService
                        from app.services.ga4_service import GA4Service
                        from app.models.user import UserProfile
                        
                        # Get user
                        user_result = await self.session.execute(
                            select(UserProfile).where(UserProfile.id == subscription.user_id)
                        )
                        user = user_result.scalar_one_or_none()
                        
                        # Get plan for value
                        plan_result = await self.session.execute(
                            select(Plan).where(Plan.id == subscription.plan_id)
                        )
                        plan = plan_result.scalar_one_or_none()
                        
                        if user and plan:
                            # Calculate value from invoice amount (handles discounts etc.)
                            value = amount_paid / 100.0
                            currency = invoice_data.get("currency", "usd").upper()
                            event_id = f"invoice_{invoice_data.get('id')}"
                            
                            # Get tracking context from user profile (best effort)
                            client_ip = user.last_checkout_ip
                            client_user_agent = user.last_checkout_user_agent
                            fbp = user.last_checkout_fbp
                            fbc = user.last_checkout_fbc
                            ga_client_id = user.last_checkout_ga_client_id
                            ga_session_id = user.last_checkout_ga_session_id
                            
                            # Try to get cookies from subscription metadata (better attribution)
                            # We need to fetch the subscription from Stripe to get metadata
                            ttp = None
                            ttclid = None
                            try:
                                stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                                metadata = stripe_sub.metadata
                                ttp = metadata.get("ttp")
                                ttclid = metadata.get("ttclid")
                                # Also refresh cookies if available in metadata (might be newer than user profile)
                                if metadata.get("fbp"): fbp = metadata.get("fbp")
                                if metadata.get("fbc"): fbc = metadata.get("fbc")
                                if metadata.get("client_ip"): client_ip = metadata.get("client_ip")
                                if metadata.get("client_user_agent"): client_user_agent = metadata.get("client_user_agent")
                                if metadata.get("ga_client_id"): ga_client_id = metadata.get("ga_client_id")
                                if metadata.get("ga_session_id"): ga_session_id = metadata.get("ga_session_id")
                            except Exception as e:
                                logger.warning(f"Could not retrieve subscription metadata for attribution: {e}")
                            
                            # Extract names
                            first_name = None
                            last_name = None
                            if user.display_name:
                                name_parts = user.display_name.split(maxsplit=1)
                                first_name = name_parts[0] if name_parts else None
                                last_name = name_parts[1] if len(name_parts) > 1 else None
                                
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"💰 [INVOICE PAYMENT] Tracking Purchase event for user {user.email}")
                            logger.info(f"   Plan: {plan.name}, Value: ${value}")
                            
                            fb_service = FacebookConversionsService()
                            tiktok_service = TikTokConversionsService()
                            ga4_service = GA4Service()
                            
                            import asyncio
                            # Facebook Purchase
                            asyncio.create_task(fb_service.track_purchase(
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
                            
                            # TikTok Purchase
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

                            # GA4 Purchase
                            if ga_client_id:
                                asyncio.create_task(ga4_service.track_purchase(
                                    client_id=ga_client_id,
                                    transaction_id=event_id,
                                    value=value,
                                    currency=currency,
                                    user_id=str(user.id),
                                    session_id=ga_session_id,
                                    client_ip=client_ip,
                                    user_agent=client_user_agent,
                                    page_location=f"{settings.FRONTEND_URL}/",
                                    items=[{"item_id": plan.name, "item_name": plan.name, "price": value, "quantity": 1}]
                                ))
                        else:
                            logger.warning(f"⚠️  [INVOICE PAYMENT] Missing user or plan for tracking (user found: {bool(user)}, plan found: {bool(plan)})")
                    else:
                         logger.info(f"💰 [INVOICE PAYMENT] Skipping tracking: amount_paid is {amount_paid}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"❌ [INVOICE PAYMENT] Failed to track Purchase event: {e}", exc_info=True)
        else:
             logger.warning(f"⚠️  [INVOICE HANDLER] Subscription {subscription.id if subscription else 'None'} status '{subscription.status if subscription else 'None'}' not in allowed list")

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
        trial_end = stripe_subscription.get("trial_end")
        metadata = stripe_subscription.get("metadata", {})
        
        logger.info(f"Processing subscription {subscription_id} for user {user_id}")
        logger.info(f"  - Status: {subscription_status}")
        logger.info(f"  - Trial End: {trial_end}")
        
        # Determine if it's a trial
        # Trust trial_end timestamp if present and in future, as status might be 'active' or 'incomplete'
        is_trial = subscription_status == "trialing"
        if not is_trial and trial_end:
            try:
                import time
                if float(trial_end) > time.time():
                    is_trial = True
                    logger.info(f"Subscription has future trial_end ({trial_end}), treating as trial despite status '{subscription_status}'")
            except (ValueError, TypeError):
                pass
        
        # Try to get plan from metadata first (reliable even if price ID changes due to discounts)
        plan = None
        plan_id_from_meta = metadata.get("plan_id")
        
        if plan_id_from_meta:
            try:
                # Import UUID to validate
                import uuid
                plan_uuid = uuid.UUID(plan_id_from_meta)
                result = await self.session.execute(
                    select(Plan).where(Plan.id == plan_uuid)
                )
                plan = result.scalar_one_or_none()
                if plan:
                    logger.info(f"Found plan from metadata: {plan.name}")
            except Exception as e:
                logger.warning(f"Failed to load plan from metadata ID {plan_id_from_meta}: {e}")
        
        # Fallback: Get plan from Stripe price ID
        if not plan:
            price_id = stripe_subscription.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
            if price_id:
                # Find plan in database (exclude free_trial - get the actual selected plan)
                result = await self.session.execute(
                    select(Plan).where(
                        Plan.stripe_price_id == price_id,
                        Plan.name != "free_trial"
                    )
                )
                plan = result.scalar_one_or_none()
        
        if not plan:
            logger.warning(f"Plan not found for subscription {subscription_id}")
            return
        
        logger.info(f"Found plan: {plan.name} with {plan.credits_per_month} credits/month")
        
        # Check if subscription already exists
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        # If this is a new active subscription, cancel any other active subscriptions for this user IMMEDIATELY
        # This ensures users can only have one active subscription at a time
        if subscription_status in ["active", "trialing"]:
            # 1. STRIPE-SIDE CLEANUP: Query Stripe directly to find and cancel duplicate subscriptions
            # This handles cases where the local DB is out of sync (e.g. missed webhooks)
            if customer_id:
                try:
                    # List all active/trialing subscriptions for this customer from Stripe
                    # We iterate through all non-canceled ones to be safe
                    stripe_subs = stripe.Subscription.list(
                        customer=customer_id,
                        status="all", 
                        limit=100
                    )
                    
                    for sub in stripe_subs.data:
                        # Skip the current subscription we are processing
                        if sub.id == subscription_id:
                            continue
                            
                        # If it's active or trialing, cancel it immediately
                        if sub.status in ["active", "trialing"]:
                            logger.warning(f"Found duplicate active subscription {sub.id} in Stripe, canceling immediately to enforce limit.")
                            try:
                                stripe.Subscription.delete(sub.id)
                                logger.info(f"Successfully canceled duplicate subscription {sub.id}")
                                
                                # Update DB if we have a record of it
                                dup_result = await self.session.execute(
                                    select(Subscription).where(Subscription.stripe_subscription_id == sub.id)
                                )
                                dup_sub = dup_result.scalar_one_or_none()
                                if dup_sub:
                                    dup_sub.status = "canceled"
                                    dup_sub.updated_at = datetime.utcnow()
                                    self.session.add(dup_sub)
                            except Exception as e:
                                logger.error(f"Failed to cancel duplicate subscription {sub.id}: {e}")
                except Exception as e:
                    logger.error(f"Error during Stripe-side subscription cleanup: {e}")

            # 2. LOCAL DB CLEANUP: Ensure local DB consistency
            # (This might be redundant now but good for safety if different customer IDs are linked to same user)
            if not subscription or subscription.stripe_subscription_id != subscription_id:
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
                        try:
                            stripe.Subscription.delete(old_sub.stripe_subscription_id)
                        except stripe.error.InvalidRequestError:
                            pass # Already deleted
                            
                        # Update status in our database
                        old_sub.status = "canceled"
                        old_sub.updated_at = datetime.utcnow()
                        self.session.add(old_sub)
                        logger.info(f"Immediately canceled subscription {old_sub.stripe_subscription_id} in Stripe and database")
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
        
        # Store the actual selected plan - always use the actual plan, even during trial
        # The trial is just a status, not a different plan
        actual_plan_id = plan.id
        actual_plan_name = plan.name
        # Cache trial credits before commit to avoid lazy loading error (MissingGreenlet)
        trial_credits_to_grant = plan.trial_credits
        
        if subscription:
            # Update existing subscription
            # Always use the actual plan (not free_trial) - trial is just a status
            subscription.plan_id = actual_plan_id
            subscription.plan_name = actual_plan_name
            subscription.status = stripe_subscription.get("status")
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
            subscription.updated_at = now
        else:
            # Create new subscription
            # Always use the actual plan (not free_trial) - trial is just a status
            subscription = Subscription(
                user_id=user_id,
                plan_id=actual_plan_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan_name=actual_plan_name,
                status=stripe_subscription.get("status"),
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                last_credit_reset=now,
                created_at=now,
                updated_at=now,  # Explicitly set updated_at
            )
        
        self.session.add(subscription)
        
        try:
            await self.session.commit()
        except Exception as e:
            # Handle race condition: Subscription might have been created by another webhook (e.g. customer.subscription.created)
            # while we were processing this one.
            if "IntegrityError" in str(type(e).__name__) or "UniqueViolationError" in str(e):
                logger.warning(f"Race condition detected for subscription {subscription_id}. Retrying update...")
                await self.session.rollback()
                
                # Re-fetch the existing subscription
                result = await self.session.execute(
                    select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
                )
                existing_sub = result.scalar_one_or_none()
                
                if existing_sub:
                    # Update the existing record instead
                    existing_sub.plan_id = actual_plan_id
                    existing_sub.plan_name = actual_plan_name
                    existing_sub.status = stripe_subscription.get("status")
                    existing_sub.current_period_start = current_period_start
                    existing_sub.current_period_end = current_period_end
                    existing_sub.updated_at = now
                    # Only update last_credit_reset if it's a new record logic (optional, but keep consistent)
                    # existing_sub.last_credit_reset = now 
                    
                    self.session.add(existing_sub)
                    await self.session.commit()
                    subscription = existing_sub # Update reference
                    logger.info(f"Successfully recovered from race condition and updated subscription {subscription_id}")
                else:
                    # Should not happen if error was UniqueViolation on this ID
                    logger.error(f"IntegrityError occurred but could not find existing subscription {subscription_id}: {e}")
                    raise e
            else:
                raise e

        await self.session.refresh(subscription)
        
        # Invalidate user cache so frontend updates immediately (e.g. hide timer)
        try:
            from app.utils.cache import invalidate_user_cache
            await invalidate_user_cache(str(user_id))
            logger.info(f"Invalidated user cache for {user_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate user cache: {e}")
        
        # Grant credits based on subscription status
        # If in trial, grant 40 trial credits (plan is already set to free_trial above)
        if is_trial:
            logger.info(f"Subscription {subscription_id} is in trial - granting {trial_credits_to_grant} trial credits")
            
            # Refresh plan to ensure attributes are loaded (prevents MissingGreenlet error)
            # The plan object might be expired after the commit above
            try:
                await self.session.refresh(plan)
            except Exception as e:
                logger.warning(f"Could not refresh plan object, might cause lazy loading error: {e}")
            
            # Extract tracking context from subscription metadata
            tracking_context = {
                "client_ip": metadata.get("client_ip"),
                "client_user_agent": metadata.get("client_user_agent"),
                "fbp": metadata.get("fbp"),
                "fbc": metadata.get("fbc"),
                "ttp": metadata.get("ttp"),
                "ttclid": metadata.get("ttclid"),
                "ga_client_id": metadata.get("ga_client_id"),
                "ga_session_id": metadata.get("ga_session_id"),
            }
            
            # Grant trial credits (70) - use the actual plan's trial_credits setting
            await self._grant_trial_credits(subscription, plan, tracking_context)
        else:
            # Reset credits to plan amount (monthly reset)
            await self._reset_monthly_credits(subscription)

    async def _check_and_reset_credits(self, subscription: Subscription):
        """Check if credits need to be reset based on billing period.
        
        For monthly plans: Reset when billing period changes (monthly)
        For yearly plans: Reset every month (not just when billing period changes)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Don't reset credits for trial subscriptions - they have fixed trial credits
        if subscription.status == "trialing":
            return
        
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
            
            # Also check if billing period rolled over (new year started)
            period_start = subscription.current_period_start
            if period_start.tzinfo is None and last_reset.tzinfo is not None:
                from datetime import timezone
                period_start = period_start.replace(tzinfo=timezone.utc)
            elif period_start.tzinfo is not None and last_reset.tzinfo is None:
                from datetime import timezone
                last_reset = last_reset.replace(tzinfo=timezone.utc)
            
            new_billing_period = period_start > last_reset
            
            logger.info(f"[YEARLY PLAN CHECK] User {subscription.user_id}: Months: {months_since_reset}, Days: {days_since_reset}, New Period: {new_billing_period}, Last reset: {last_reset}, Now: {now}")
            
            if months_since_reset >= 1 or days_since_reset >= 30 or new_billing_period:
                logger.info(f"[YEARLY PLAN RESET] User {subscription.user_id}: Reset triggered (months: {months_since_reset}, days: {days_since_reset}, new_period: {new_billing_period})")
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

    async def _grant_trial_credits(self, subscription: Subscription, plan: Plan, tracking_context: Optional[dict] = None):
        """Grant trial credits (40) to user during trial period.
        
        SECURITY: This method should ONLY be called from verified webhook handlers.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Idempotency check: Check if we already granted trial credits for this subscription
        # This prevents duplicate events when both checkout.session.completed and customer.subscription.created fire
        from app.models.credits import CreditTransaction
        
        # Check for existing trial_start transaction for this user created in the last minute
        # or check metadata if possible (harder with JSON)
        # We'll check for any 'trial_start' transaction for this user associated with this plan recently
        # Since trial start happens once per subscription, checking user_id + reason='trial_start' + recent time is safe enough
        # Or better: check if the wallet balance is already equal to trial credits and we just did a transaction
        
        # Best approach: Query for recent transaction
        result = await self.session.execute(
            select(CreditTransaction).where(
                CreditTransaction.user_id == subscription.user_id,
                CreditTransaction.reason == "trial_start",
                CreditTransaction.created_at > datetime.utcnow() - timedelta(minutes=5)
            )
        )
        existing_tx = result.scalars().first()
        
        # Get current wallet to check balance
        wallet = await self.credits_service.get_wallet(subscription.user_id)
        
        # Idempotency: Only skip if we granted credits AND user still has them (or close to it)
        # This handles cases where credits were accidentally wiped by auth.py race conditions
        if existing_tx and wallet.balance_credits > 0:
            logger.info(f"Trial credits already granted for user {subscription.user_id} (tx {existing_tx.id}). Skipping duplicate grant/tracking.")
            return

        logger.info(f"[TRIAL CREDITS] Granting {plan.trial_credits} trial credits for subscription {subscription.id}, user {subscription.user_id}")
        
        # Get current wallet (already fetched above)
        old_balance = wallet.balance_credits
        
        # Set balance to trial credits (replace any existing credits)
        # FORCE 70 CREDITS for all trials as requested
        wallet.balance_credits = 70 # plan.trial_credits
        
        # Record transaction
        from app.models.credits import CreditTransaction
        credit_amount = 70 - old_balance # plan.trial_credits - old_balance
        transaction = CreditTransaction(
            user_id=subscription.user_id,
            amount=abs(credit_amount),
            direction="credit" if credit_amount > 0 else "debit",
            reason="trial_start",
            metadata_json=f'{{"plan_name": "{plan.name}", "old_balance": {old_balance}, "new_balance": 70, "trial_credits": 70}}'
        )
        
        logger.info(f"[TRIAL CREDITS] Set credits for user {subscription.user_id}: {old_balance} -> 70 (trial credits for plan: {plan.name})")
        
        self.session.add(transaction)
        self.session.add(wallet)
        
        await self.session.commit()
        logger.info(f"[TRIAL CREDITS] Trial credits granted successfully for user {subscription.user_id}")

        # --- TRIGGER TRACKING EVENTS ---
        # ONLY track if subscription status is valid (trialing or active)
        # Skip tracking for 'incomplete' status (payment failed/requires action)
        if subscription.status not in ["trialing", "active"]:
             logger.warning(f"⚠️ [TRIAL TRACKING] Skipping tracking for subscription {subscription.id} with status '{subscription.status}' (expected 'trialing' or 'active')")
             return

        try:
            from app.models.user import UserProfile
            from app.services.facebook_conversions import FacebookConversionsService
            from app.services.tiktok_conversions import TikTokConversionsService
            from app.services.ga4_service import GA4Service
            
            # Get user profile for tracking data
            result = await self.session.execute(
                select(UserProfile).where(UserProfile.id == subscription.user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Initialize tracking variables
                client_ip = None
                client_user_agent = None
                fbp = None
                fbc = None
                ttp = None
                ttclid = None
                ga_client_id = None
                ga_session_id = None
                
                # 1. Try to use passed tracking_context first (from subscription metadata)
                if tracking_context:
                    client_ip = tracking_context.get("client_ip")
                    client_user_agent = tracking_context.get("client_user_agent")
                    fbp = tracking_context.get("fbp")
                    fbc = tracking_context.get("fbc")
                    ttp = tracking_context.get("ttp")
                    ttclid = tracking_context.get("ttclid")
                    ga_client_id = tracking_context.get("ga_client_id")
                    ga_session_id = tracking_context.get("ga_session_id")
                
                # 2. Fallback to user profile if missing
                if not client_ip:
                    client_ip = user.last_checkout_ip
                if not client_user_agent:
                    client_user_agent = user.last_checkout_user_agent
                if not fbp:
                    fbp = user.last_checkout_fbp
                if not fbc:
                    fbc = user.last_checkout_fbc
                
                # GA4 fallbacks
                if not ga_client_id:
                    ga_client_id = user.last_checkout_ga_client_id or user.signup_ga_client_id
                if not ga_session_id:
                    ga_session_id = user.last_checkout_ga_session_id or user.signup_ga_session_id
                    
                # Note: UserProfile doesn't have ttp/ttclid yet, so they might remain None if not in tracking_context
                
                # Extract names
                first_name = None
                last_name = None
                if user.display_name:
                    name_parts = user.display_name.split(maxsplit=1)
                    first_name = name_parts[0] if name_parts else None
                    last_name = name_parts[1] if len(name_parts) > 1 else None
                
                # Calculate value (use $0 for trial start, or $1 if we charge $1)
                # We charge $1 for trial.
                value = plan.trial_amount_cents / 100.0
                
                # Apply discount if yearly plan (60% of original price for trial amount too if applicable)
                if plan.interval == "year":
                    # If trial amount is same as subscription amount (no trial), apply discount
                    # But usually trial is $1 fixed.
                    # If plan.trial_amount_cents is > 100 (e.g. full price first month), apply discount
                    if plan.trial_amount_cents > 100:
                        value = value * 0.6
                
                currency = "USD"
                event_id = f"purchase_{subscription.id}_{int(time.time())}"
                
                fb_service = FacebookConversionsService()
                tt_service = TikTokConversionsService()
                ga4_service = GA4Service()
                
                import asyncio
                # Facebook Purchase (Track trial charge as purchase)
                asyncio.create_task(fb_service.track_purchase(
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
                    content_name=f"{plan.name} (Trial)",
                    content_ids=[str(plan.id)]
                ))
                
                # TikTok Purchase (Track trial charge as purchase)
                # Get tracking from user profile as fallback if not in context
                if not ttp and user.signup_ttp:
                    ttp = user.signup_ttp
                if not ttclid and user.signup_ttclid:
                    ttclid = user.signup_ttclid
                if not ttp and user.last_checkout_ttp:
                    ttp = user.last_checkout_ttp
                if not ttclid and user.last_checkout_ttclid:
                    ttclid = user.last_checkout_ttclid
                    
                asyncio.create_task(tt_service.track_purchase(
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
                    ttclid=ttclid
                ))
                
                # GA4 Purchase (Track trial charge as purchase)
                if ga_client_id:
                    asyncio.create_task(ga4_service.track_purchase(
                        client_id=ga_client_id,
                        transaction_id=event_id,
                        value=value,
                        currency=currency,
                        user_id=str(user.id),
                        session_id=ga_session_id,
                        client_ip=client_ip,
                        user_agent=client_user_agent,
                        page_location=f"{settings.FRONTEND_URL}/upgrade",
                        items=[{
                            "item_id": str(plan.id),
                            "item_name": f"{plan.name} (Trial)",
                            "price": value,
                            "quantity": 1
                        }]
                    ))
                    logger.info(f"✅ [TRIAL TRACKING] GA4 Purchase event queued for user {user.email} (client_id={ga_client_id})")
                else:
                    logger.warning(f"⚠️ [TRIAL TRACKING] Skipped GA4 tracking - missing client_id for user {user.email}")
                
                logger.info(f"✅ [TRIAL TRACKING] StartTrial/Subscribe events triggered for user {user.email}")
                logger.info(f"   Context: IP={client_ip}, ttp={ttp}, ttclid={ttclid}, fbp={fbp}, fbc={fbc}, ga_client_id={ga_client_id}")
        except Exception as e:
            logger.error(f"❌ [TRIAL TRACKING] Failed to track trial start events: {e}", exc_info=True)

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
        
        # Invalidate credit cache (CRITICAL: otherwise user sees old balance)
        try:
            from app.utils.cache import invalidate_cache, cache_key
            # Invalidate credit cache
            cache_key_str = cache_key("cache", "user", str(subscription.user_id), "credits")
            await invalidate_cache(cache_key_str)
            # Invalidate profile cache (includes credit balance)
            profile_cache_key = cache_key("cache", "user", str(subscription.user_id), "profile")
            await invalidate_cache(profile_cache_key)
            # Invalidate legacy user cache
            from app.utils.cache import invalidate_user_cache
            await invalidate_user_cache(str(subscription.user_id))
            logger.info(f"Invalidated all caches for user {subscription.user_id} after credit reset")
        except Exception as e:
            logger.error(f"Failed to invalidate caches after credit reset: {e}")
            
        logger.info(f"Credits reset successfully for user {subscription.user_id}")
