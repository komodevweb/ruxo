"""
Fix trial subscription - manually sync from Stripe if webhook failed
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_session_local
from app.services.billing_service import BillingService
from sqlalchemy.future import select
from app.models.user import UserProfile
import stripe
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

async def fix_trial_subscription(user_email: str):
    """Fix trial subscription by syncing from Stripe"""
    async with get_session_local() as session:
        # Find user
        result = await session.execute(
            select(UserProfile).where(UserProfile.email == user_email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User not found: {user_email}")
            return
        
        print(f"Found user: {user.email} (ID: {user.id})")
        
        # Find customer in Stripe
        customers = stripe.Customer.list(email=user.email, limit=1)
        if not customers.data:
            print(f"No Stripe customer found for {user.email}")
            return
        
        customer = customers.data[0]
        print(f"Found Stripe customer: {customer.id}")
        
        # Get subscriptions
        subscriptions = stripe.Subscription.list(customer=customer.id, limit=10)
        
        if not subscriptions.data:
            print(f"No subscriptions found for customer {customer.id}")
            return
        
        print(f"\nFound {len(subscriptions.data)} subscription(s):")
        for sub in subscriptions.data:
            print(f"  - {sub.id}: status={sub.status}, trial_end={sub.trial_end}")
            
            # Process active or trialing subscriptions
            if sub.status in ['active', 'trialing']:
                print(f"\nProcessing subscription {sub.id}...")
                billing_service = BillingService(session)
                
                try:
                    await billing_service._process_subscription(
                        subscription_data=sub,
                        user_id=user.id
                    )
                    print(f"✅ Successfully processed subscription {sub.id}")
                except Exception as e:
                    print(f"❌ Error processing subscription {sub.id}: {e}")
                    import traceback
                    traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_trial_subscription.py <user_email>")
        sys.exit(1)
    
    user_email = sys.argv[1]
    asyncio.run(fix_trial_subscription(user_email))

