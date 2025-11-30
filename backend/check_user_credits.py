import asyncio
import sys
import os
from pathlib import Path
import uuid
from dotenv import load_dotenv

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
load_dotenv(backend_dir / ".env")

from app.db.session import engine
from app.models.credits import CreditWallet, CreditTransaction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

async def check_credits(user_id_str):
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        print(f"Invalid UUID: {user_id_str}")
        return

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Get Wallet
        result = await session.execute(select(CreditWallet).where(CreditWallet.user_id == user_id))
        wallet = result.scalar_one_or_none()
        
        print(f"\n--- Credit Report for {user_id} ---")
        if wallet:
            print(f"Balance: {wallet.balance_credits} credits")
            print(f"Lifetime Added: {wallet.lifetime_credits_added}")
            print(f"Lifetime Spent: {wallet.lifetime_credits_spent}")
        else:
            print("No wallet found for this user.")

        # Get Recent Transactions
        print("\n--- Recent Transactions ---")
        result = await session.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(10)
        )
        transactions = result.scalars().all()
        
        if transactions:
            for tx in transactions:
                print(f"{tx.created_at} | {tx.direction.upper()} {tx.amount} | Reason: {tx.reason} | Meta: {tx.metadata_json}")
        else:
            print("No transactions found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_user_credits.py <user_id>")
    else:
        asyncio.run(check_credits(sys.argv[1]))

