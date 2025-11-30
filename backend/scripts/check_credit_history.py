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
from app.models.credits import CreditTransaction
from app.models.user import UserProfile

async def check_credit_history(user_id_str: str):
    """Check a user's credit transaction history."""
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
            
            # Get credit transactions
            result = await session.execute(
                select(CreditTransaction)
                .where(CreditTransaction.user_id == user.id)
                .order_by(CreditTransaction.created_at.desc())
            )
            transactions = result.scalars().all()
            
            print(f"\n📊 Transaction History ({len(transactions)} total):")
            print(f"{'Date':<20} | {'Type':<8} | {'Amount':<6} | {'Reason':<25} | {'Metadata'}")
            print("-" * 100)
            
            for tx in transactions:
                date_str = tx.created_at.strftime("%Y-%m-%d %H:%M:%S")
                direction = "➕" if tx.direction == "credit" else "➖"
                
                # Parse metadata if it's JSON string or dict
                metadata = tx.metadata_json
                if hasattr(metadata, 'get'): # It's likely already a dict if using SQLModel with JSON column
                    pass 
                
                print(f"{date_str:<20} | {direction} {tx.direction:<5} | {tx.amount:<6} | {tx.reason:<25} | {metadata}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_credit_history.py <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    asyncio.run(check_credit_history(user_id))

