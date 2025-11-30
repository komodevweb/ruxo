import asyncio
import sys
import uuid
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.db.session import engine
from app.models.user import UserProfile
from app.services.credits_service import CreditsService

async def check_user_credits(user_id_str: str):
    """Check a user's credits."""
    async_session = sessionmaker(engine, class_=AsyncSessionType, expire_on_commit=False)
    async with async_session() as session:
        try:
            # Parse user ID
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                print(f"❌ Invalid user ID format: {user_id_str}")
                return
            
            # Find user
            result = await session.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User not found: {user_id}")
                return
            
            print(f"✓ Found user: {user.email} ({user.id})")
            
            # Get current credits
            credits_service = CreditsService(session)
            wallet = await credits_service.get_wallet(user.id)
            
            print(f"\n💰 Credit Balance: {wallet.balance_credits}")
            print(f"   Lifetime Added: {wallet.lifetime_credits_added}")
            print(f"   Lifetime Spent: {wallet.lifetime_credits_spent}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_user_credits.py <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    asyncio.run(check_user_credits(user_id))

