import stripe
import uuid
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

    async def create_checkout_session(self, user: UserProfile, plan_name: str) -> str:
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
        
        # If user has an active subscription, create a checkout session for upgrade
        # This allows the user to see the new plan and complete payment through Stripe checkout
        if existing_subscription:
            logger.info(f"User {user.id} has active subscription {existing_subscription.stripe_subscription_id}, creating checkout for upgrade to {plan_name}")
            
            try:
                # Get or create Stripe customer
                customer_id = existing_subscription.stripe_customer_id or await self._get_or_create_customer(user)
            
                # Cancel the existing subscription at period end (so it doesn't conflict)
                # We'll create a new subscription through checkout
                try:
                    stripe.Subscription.modify(
                existing_subscription.stripe_subscription_id,
                        cancel_at_period_end=True,
                metadata={
                            "user_id": str(user.id),
                            "will_be_replaced_by": plan_name
                        }
                    )
                    logger.info(f"Marked existing subscription {existing_subscription.stripe_subscription_id} to cancel at period end")
                except Exception as e:
                    logger.warning(f"Could not mark subscription for cancellation: {e}")
                
                # Apply 40% discount coupon for yearly plans
                checkout_params = {
                    "payment_method_types": ["card"],
                    "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
                    "mode": "subscription",
                    "customer": customer_id,
                    "success_url": f"{settings.FRONTEND_URL}/settings?session_id={{CHECKOUT_SESSION_ID}}&upgraded=true",
                    "cancel_url": f"{settings.FRONTEND_URL}/pricing",
                    "metadata": {
                    "user_id": str(user.id),
                    "plan_id": str(plan.id),
                        "plan_name": plan.name,
                        "is_upgrade": "true",
                        "existing_subscription_id": existing_subscription.stripe_subscription_id
                    },
                    "subscription_data": {
                        "metadata": {
                            "user_id": str(user.id),
                            "plan_id": str(plan.id),
                            "plan_name": plan.name,
                            "is_upgrade": "true",
                            "existing_subscription_id": existing_subscription.stripe_subscription_id
                        }
                    }
                }
                
                # Apply 40% discount coupon for yearly plans
                if plan.interval == "year":
                    checkout_params["discounts"] = [{"coupon": "ruxo40"}]
                
                # Create checkout session for the new plan
                # Stripe will handle the upgrade and proration
                checkout_session = stripe.checkout.Session.create(**checkout_params)
                
                logger.info(f"Checkout session created for upgrade: {checkout_session.id}")
                return checkout_session.url
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
        
        # Cancel any other active subscriptions to ensure only one active subscription
        for old_sub in other_active_subscriptions:
            logger.warning(f"Found unexpected active subscription {old_sub.stripe_subscription_id} for user {user.id}, canceling it")
            try:
                stripe.Subscription.modify(
                    old_sub.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                old_sub.status = "canceled"
                old_sub.updated_at = datetime.utcnow()
                self.session.add(old_sub)
            except Exception as e:
                logger.error(f"Error canceling subscription {old_sub.stripe_subscription_id}: {e}")
        
        if other_active_subscriptions:
            await self.session.commit()
            logger.info(f"Canceled {len(other_active_subscriptions)} existing subscription(s) for user {user.id}")
        
        # Get or create Stripe customer
        customer_id = await self._get_or_create_customer(user)
        
        # Apply 40% discount coupon for yearly plans
        checkout_params = {
            "payment_method_types": ["card"],
            "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
            "mode": "subscription",
            "customer": customer_id,
            "success_url": f"{settings.FRONTEND_URL}/settings?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{settings.FRONTEND_URL}/pricing",
            "metadata": {
                "user_id": str(user.id),
                "plan_id": str(plan.id),
                "plan_name": plan.name
            }
        }
        
        # Apply 40% discount coupon for yearly plans
        if plan.interval == "year":
            checkout_params["discounts"] = [{"coupon": "ruxo40"}]
        
        checkout_session = stripe.checkout.Session.create(**checkout_params)
        return checkout_session.url

    async def _get_or_create_customer(self, user: UserProfile) -> str:
        """Get existing Stripe customer or create new one."""
        # Check if user has existing subscription(s) - handle multiple subscriptions
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
            return existing_sub.stripe_customer_id
        
        # Create new Stripe customer with user_id in metadata
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)}
        )
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
            return_url=f"{settings.FRONTEND_URL}/pricing",
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
