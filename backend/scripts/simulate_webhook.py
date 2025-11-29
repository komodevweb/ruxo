import asyncio
import sys
import os
import time
import stripe
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.session import engine
from app.services.billing_service import BillingService
from app.models.user import UserProfile
from app.models.billing import Plan
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

stripe.api_key = settings.STRIPE_API_KEY

async def simulate_webhook(user_email: str, plan_name: str):
    """
    Simulates a checkout.session.completed event to grant a plan and credits.
    Useful when local webhooks are not working.
    """
    print(f"🔧 Simulating webhook for user: {user_email}, plan: {plan_name}")
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Find User
        result = await session.execute(select(UserProfile).where(UserProfile.email == user_email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User not found: {user_email}")
            return

        print(f"✅ Found User: {user.id}")
        
        # Find Stripe Customer ID by email since it's not in UserProfile
        stripe_customer_id = None
        try:
            customers = stripe.Customer.list(email=user_email, limit=1)
            if customers.data:
                stripe_customer_id = customers.data[0].id
                print(f"✅ Found Stripe Customer ID: {stripe_customer_id}")
            else:
                print(f"❌ No Stripe customer found for email: {user_email}")
                return
        except Exception as e:
            print(f"❌ Error finding Stripe customer: {e}")
            return
        
        # 2. Find Plan
        result = await session.execute(select(Plan).where(Plan.name == plan_name))
        plan = result.scalar_one_or_none()
        
        if not plan:
            print(f"❌ Plan not found: {plan_name}")
            return
            
        print(f"✅ Found Plan: {plan.display_name} ({plan.name}) - {plan.credits_per_month} credits")

        # 3. Create Dummy Subscription Object (Mocking Stripe Data)
        # We need to create a real subscription in DB or mock the stripe object for _process_subscription
        
        # Let's try to find the latest subscription in Stripe for this customer to make it real
        try:
            subscriptions = stripe.Subscription.list(
                customer=stripe_customer_id,
                limit=1,
                status='all' # Get even incomplete ones if any
            )
            
            if subscriptions.data:
                stripe_sub = subscriptions.data[0]
                print(f"✅ Found latest Stripe subscription: {stripe_sub.id} ({stripe_sub.status})")
                
                # Force status to active/trialing for the simulation if it's not
                if stripe_sub.status not in ['active', 'trialing']:
                    print(f"⚠️ Subscription status is '{stripe_sub.status}'. Treating as 'active' for simulation.")
                    stripe_sub.status = 'active' 
                
                # MANUALLY CALL BillingService._process_subscription
                billing_service = BillingService(session)
                
                # Inject the plan_id into metadata to ensure correct plan matching
                # Using a regular dictionary update since stripe objects might be custom objects
                try:
                    stripe_sub['metadata']['plan_id'] = str(plan.id)
                except TypeError:
                     # If it's a stripe object wrapper, it might behave differently, but typically subscriptable
                     stripe_sub.metadata = {'plan_id': str(plan.id)}
                
                print("🔄 Processing subscription locally...")
                await billing_service._process_subscription(stripe_sub, user.id)
                
                print("✅ Webhook simulation complete!")
                print("👉 Check your credits and plan in the app now.")
                
            else:
                print("❌ No subscriptions found in Stripe for this customer.")
                print("   Please try clicking 'Subscribe' in the UI first to generate a subscription object in Stripe.")
                
        except Exception as e:
            print(f"❌ Error during simulation: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/simulate_webhook.py <email> <plan_name>")
        print("Example: python scripts/simulate_webhook.py user@example.com starter_monthly")
        sys.exit(1)
        
    email = sys.argv[1]
    plan = sys.argv[2]
    
    # Windows asyncio loop policy fix
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(simulate_webhook(email, plan))
