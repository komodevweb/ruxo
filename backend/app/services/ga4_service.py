import logging
import httpx
import json
from typing import Dict, Any, Optional, List
from app.core.config import settings
import os
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

# Create dedicated GA4 Conversions API logger that writes to file
ga4_conversions_logger = logging.getLogger("ga4_conversions_api")
ga4_conversions_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent.parent
project_root = backend_dir.parent
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)

# Create rotating file handler (max 50MB per file, keep 5 files)
ga4_log_file = os.path.join(log_dir, "ga4_conversions_api.log")
file_handler = RotatingFileHandler(
    ga4_log_file,
    maxBytes=50*1024*1024,  # 50MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)

# Create formatter with detailed information
file_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)

# Add handler to ga4_conversions_logger
ga4_conversions_logger.addHandler(file_handler)

# Prevent propagation to avoid duplicate logs
ga4_conversions_logger.propagate = False

class GA4Service:
    """
    Service for tracking server-side events using Google Analytics 4 Measurement Protocol.
    """
    
    def __init__(self):
        self.measurement_id = settings.GA4_MEASUREMENT_ID
        self.api_secret = settings.GA4_API_SECRET
        self.base_url = "https://www.google-analytics.com/mp/collect"
        self.validation_url = "https://www.google-analytics.com/debug/mp/collect"
        
        if not self.measurement_id or not self.api_secret:
            ga4_conversions_logger.warning("GA4 credentials (GA4_MEASUREMENT_ID, GA4_API_SECRET) not configured. Tracking disabled.")

    async def send_event(
        self, 
        event_name: str, 
        client_id: str, 
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_location: Optional[str] = None,
        page_referrer: Optional[str] = None,
        page_title: Optional[str] = None,
        language: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        debug_mode: bool = False
    ) -> bool:
        """
        Send an event to GA4 Measurement Protocol.
        
        Args:
            event_name: The name of the event (e.g., 'purchase', 'sign_up')
            client_id: The client ID from the _ga cookie (required)
            user_id: The user ID (optional, for cross-device tracking)
            session_id: The session ID from the _ga_<container> cookie (recommended)
            client_ip: The client's IP address (optional, sent as custom param 'ip_address')
            user_agent: The client's user agent (optional, sent as custom param 'user_agent')
            page_location: The full URL of the page (optional, sent as 'page_location')
            page_referrer: The referrer URL (optional, sent as 'page_referrer')
            page_title: The page title (optional, sent as 'page_title')
            language: The user's language (optional, sent as 'language')
            params: Additional event parameters
            debug_mode: If True, sends to validation endpoint
        """
        if not self.measurement_id or not self.api_secret:
            return False
            
        if not client_id:
            ga4_conversions_logger.warning(f"Cannot track GA4 event {event_name}: client_id is missing")
            return False

        # Base parameters required for every event
        event_params = params or {}
        
        # Add session_id if provided
        if session_id:
            event_params["session_id"] = session_id
            
        # Add IP and User Agent as custom parameters if provided
        # Note: GA4 MP doesn't support IP override for geo-lookup, but we can log it as a param
        if client_ip:
            event_params["ip_address"] = client_ip
        if user_agent:
            event_params["user_agent"] = user_agent
            
        # Add standard page/user parameters if provided
        if page_location:
            event_params["page_location"] = page_location
        if page_referrer:
            event_params["page_referrer"] = page_referrer
        if page_title:
            event_params["page_title"] = page_title
        if language:
            event_params["language"] = language
            
        # Add debug_mode param if enabled (makes event appear in DebugView)
        # Also can be set via query param, but adding to event params ensures it works
        if debug_mode or settings.ENVIRONMENT == "development":
            event_params["debug_mode"] = 1

        payload = {
            "client_id": client_id,
            "events": [{
                "name": event_name,
                "params": event_params
            }]
        }

        if user_id:
            payload["user_id"] = user_id

        url = f"{self.validation_url if debug_mode else self.base_url}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"

        # Log full details to dedicated file
        ga4_conversions_logger.info("=" * 100)
        ga4_conversions_logger.info(f"[OUT] OUTGOING REQUEST - {event_name} Event")
        ga4_conversions_logger.info(f"URL: {url}")
        ga4_conversions_logger.info(f"HTTP Method: POST")
        if user_agent:
            ga4_conversions_logger.info(f"User-Agent Header: {user_agent}")
        ga4_conversions_logger.info(f"Request Payload:")
        ga4_conversions_logger.info(json.dumps(payload, indent=2))
        ga4_conversions_logger.info("=" * 100)

        try:
            headers = {}
            if user_agent:
                headers["User-Agent"] = user_agent

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # Log full response to dedicated file
                ga4_conversions_logger.info("=" * 100)
                ga4_conversions_logger.info(f"[IN] INCOMING RESPONSE - {event_name} Event")
                ga4_conversions_logger.info(f"HTTP Status Code: {response.status_code}")
                ga4_conversions_logger.info(f"Response Headers: {dict(response.headers)}")
                ga4_conversions_logger.info(f"Response Body:")
                
                # GA4 usually returns empty body (204 No Content) for successful requests unless debug/validation
                response_text = response.text
                if not response_text and response.status_code == 204:
                    response_text = "(Empty Body - 204 No Content)"
                
                try:
                    # Try to parse as JSON if possible
                    response_json = response.json()
                    ga4_conversions_logger.info(json.dumps(response_json, indent=2))
                except:
                    # Otherwise log text
                    ga4_conversions_logger.info(response_text)
                
                ga4_conversions_logger.info("=" * 100)
                ga4_conversions_logger.info("")  # Empty line for readability
                
                # Log full details for easier debugging (similar to TikTok/FB logs)
                ga4_conversions_logger.info(f"GA4 {event_name} Event Details:")
                ga4_conversions_logger.info(f"   - client_id: {client_id}")
                ga4_conversions_logger.info(f"   - user_id: {user_id}")
                ga4_conversions_logger.info(f"   - session_id: {session_id}")
                ga4_conversions_logger.info(f"   - debug_mode: {event_params.get('debug_mode', 0)}")
                if 'value' in event_params:
                    ga4_conversions_logger.info(f"   - value: {event_params.get('value')} {event_params.get('currency', 'USD')}")
                if 'transaction_id' in event_params:
                    ga4_conversions_logger.info(f"   - transaction_id: {event_params.get('transaction_id')}")
                if 'items' in event_params:
                    items = event_params.get('items')
                    ga4_conversions_logger.info(f"   - items: {len(items)} item(s)")
                    for i, item in enumerate(items):
                        ga4_conversions_logger.info(f"     {i+1}. {item.get('item_name', 'Unknown')} ({item.get('item_id', 'No ID')}) - {item.get('price', 0)} {event_params.get('currency', 'USD')}")
                
                ga4_conversions_logger.info(f"Context Fields:")
                ga4_conversions_logger.info(f"   - ip_address: {event_params.get('ip_address', 'N/A')}")
                ga4_conversions_logger.info(f"   - user_agent: {event_params.get('user_agent', 'N/A')}")
                ga4_conversions_logger.info(f"   - page_location: {event_params.get('page_location', 'N/A')}")
                
                ga4_conversions_logger.info("=" * 100)

                if debug_mode:
                    # Validation endpoint returns details
                    ga4_conversions_logger.info(f"GA4 Validation Response: {response.text}")
                
                # Standard endpoint returns 204 No Content on success, or 2xx
                if response.status_code >= 200 and response.status_code < 300:
                    ga4_conversions_logger.info(f"[SUCCESS] GA4 event '{event_name}' tracked successfully for client_id={client_id}")
                    return True
                else:
                    ga4_conversions_logger.error(f"[ERROR] Failed to track GA4 event '{event_name}': {response.status_code} {response.text}")
                    return False
        except Exception as e:
            ga4_conversions_logger.error(f"Error sending GA4 event '{event_name}': {e}")
            return False

    async def track_sign_up(
        self, 
        client_id: str, 
        user_id: str, 
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_location: Optional[str] = None,
        page_referrer: Optional[str] = None,
        method: str = "email"
    ):
        """Track 'sign_up' event"""
        return await self.send_event(
            event_name="sign_up",
            client_id=client_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            page_location=page_location,
            page_referrer=page_referrer,
            params={
                "method": method
            }
        )

    async def track_login(
        self, 
        client_id: str, 
        user_id: str, 
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_location: Optional[str] = None,
        page_referrer: Optional[str] = None,
        method: str = "email"
    ):
        """Track 'login' event"""
        return await self.send_event(
            event_name="login",
            client_id=client_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            page_location=page_location,
            page_referrer=page_referrer,
            params={
                "method": method
            }
        )

    async def track_purchase(
        self,
        client_id: str,
        transaction_id: str,
        value: float,
        currency: str = "USD",
        items: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_location: Optional[str] = None,
        page_referrer: Optional[str] = None,
        coupon: Optional[str] = None
    ):
        """
        Track 'purchase' event.
        
        items format: [{"item_id": "sku1", "item_name": "Plan Name", "price": 10.00, "quantity": 1}]
        """
        params = {
            "transaction_id": transaction_id,
            "value": value,
            "currency": currency,
        }
        
        if items:
            params["items"] = items
            
        if coupon:
            params["coupon"] = coupon
            
        return await self.send_event(
            event_name="purchase",
            client_id=client_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            page_location=page_location,
            page_referrer=page_referrer,
            params=params
        )

    async def track_begin_checkout(
        self,
        client_id: str,
        value: float,
        currency: str = "USD",
        items: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_location: Optional[str] = None,
        page_referrer: Optional[str] = None,
        coupon: Optional[str] = None
    ):
        """Track 'begin_checkout' event"""
        params = {
            "value": value,
            "currency": currency,
        }
        
        if items:
            params["items"] = items
            
        if coupon:
            params["coupon"] = coupon
            
        return await self.send_event(
            event_name="begin_checkout",
            client_id=client_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            page_location=page_location,
            page_referrer=page_referrer,
            params=params
        )

    async def track_add_to_cart(
        self,
        client_id: str,
        value: float,
        currency: str = "USD",
        items: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_location: Optional[str] = None,
        page_referrer: Optional[str] = None
    ):
        """Track 'add_to_cart' event"""
        params = {
            "value": value,
            "currency": currency,
        }
        
        if items:
            params["items"] = items
            
        return await self.send_event(
            event_name="add_to_cart",
            client_id=client_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            page_location=page_location,
            page_referrer=page_referrer,
            params=params
        )

    async def track_view_item(
        self,
        client_id: str,
        value: float,
        currency: str = "USD",
        items: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_location: Optional[str] = None,
        page_referrer: Optional[str] = None
    ):
        """Track 'view_item' event"""
        params = {
            "value": value,
            "currency": currency,
        }
        
        if items:
            params["items"] = items
            
        return await self.send_event(
            event_name="view_item",
            client_id=client_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            page_location=page_location,
            page_referrer=page_referrer,
            params=params
        )

    async def track_start_trial(
        self,
        client_id: str,
        value: float,
        currency: str = "USD",
        items: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        page_location: Optional[str] = None,
        page_referrer: Optional[str] = None
    ):
        """Track 'start_trial' event (custom event for trials)"""
        params = {
            "value": value,
            "currency": currency,
        }
        
        if items:
            params["items"] = items
            
        return await self.send_event(
            event_name="start_trial",
            client_id=client_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            page_location=page_location,
            page_referrer=page_referrer,
            params=params
        )
