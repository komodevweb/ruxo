from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.db.session import get_session
from app.models.logging import CountryIP
from sqlalchemy.future import select

class GeoIPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Simple logic to capture IP on requests
        # In production, this might be better handled async or via background tasks to not slow down requests
        # For now, we just pass through.
        
        response = await call_next(request)
        return response

# Helper to log IP (to be used in specific endpoints like signup/login if needed)
async def log_ip_country(ip_address: str, session):
    # Mock lookup
    country_code = "US" 
    country_name = "United States"
    
    # Check if exists
    result = await session.execute(select(CountryIP).where(CountryIP.ip_address == ip_address))
    if not result.scalar_one_or_none():
        record = CountryIP(
            ip_address=ip_address,
            country_code=country_code,
            country_name=country_name
        )
        session.add(record)
        try:
            await session.commit()
        except:
            await session.rollback()

