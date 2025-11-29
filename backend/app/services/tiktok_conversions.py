"""
TikTok Conversions API Service

This service handles server-side tracking of TikTok conversion events
using the TikTok Events API (Conversion API).
"""
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from app.core.config import settings
from logging.handlers import RotatingFileHandler
import os
import json

logger = logging.getLogger(__name__)

# Create dedicated TikTok Conversions API logger that writes to file
tiktok_conversions_logger = logging.getLogger("tiktok_conversions_api")
tiktok_conversions_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
# Determine project root relative to this file (backend/app/services/tiktok_conversions.py)
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent.parent
project_root = backend_dir.parent
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)

# Create rotating file handler (max 50MB per file, keep 5 files)
tiktok_log_file = os.path.join(log_dir, "tiktok_conversions_api.log")
file_handler = RotatingFileHandler(
    tiktok_log_file,
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

# Add handler to tiktok_conversions_logger
tiktok_conversions_logger.addHandler(file_handler)

# Prevent propagation to avoid duplicate logs
tiktok_conversions_logger.propagate = False

class TikTokConversionsService:
    """Service for sending events to TikTok Events API."""
    
    def __init__(self):
        self.pixel_id = settings.TIKTOK_PIXEL_ID
        self.access_token = settings.TIKTOK_ACCESS_TOKEN
        self.api_url = "https://business-api.tiktok.com/open_api/v1.3/event/track/"
        
        if not self.pixel_id or not self.access_token:
            logger.warning("TikTok Conversions API not configured. Pixel ID and Access Token required.")
    
    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA256 for TikTok Events API."""
        if not value:
            return ""
        return hashlib.sha256(value.lower().strip().encode('utf-8')).hexdigest()
    
    def _get_user_data(self, email: Optional[str] = None, phone: Optional[str] = None,
                      first_name: Optional[str] = None, last_name: Optional[str] = None,
                      external_id: Optional[str] = None, ttp: Optional[str] = None,
                      ttclid: Optional[str] = None) -> Dict[str, Any]:
        """Build user object for TikTok Events API.
        
        Args:
            email: User email (will be hashed)
            phone: User phone (will be hashed)
            first_name: User first name (will be hashed)
            last_name: User last name (will be hashed)
            external_id: External user ID (not hashed)
            ttp: TikTok Pixel cookie (_ttp) - for attribution matching
            ttclid: TikTok Click ID cookie (_ttclid) - for ad click attribution
        """
        user_data = {}
        
        if email:
            user_data["email"] = self._hash_value(email)
        if phone:
            user_data["phone_number"] = self._hash_value(phone)
        if first_name:
            user_data["first_name"] = self._hash_value(first_name)
        if last_name:
            user_data["last_name"] = self._hash_value(last_name)
        if external_id:
            user_data["external_id"] = external_id
        # TikTok cookies for better attribution
        if ttp:
            user_data["ttp"] = ttp
        if ttclid:
            # TikTok expects 'ttclid' in the 'context' object, but for S2S events 
            # it can also be passed in 'user' object or 'properties' depending on documentation versions.
            # Current docs suggest ttclid is a click_id and should be at event root or properties.
            # However, standard practice for S2S is often in context or properties. 
            # Let's add it to 'user' object as 'ttclid' (as per our implementation)
            # AND also add it as 'click_id' which is a common alias.
            user_data["ttclid"] = ttclid
            user_data["click_id"] = ttclid
        
        return user_data
    
    def _get_context(self, client_ip: Optional[str] = None,
                    client_user_agent: Optional[str] = None,
                    event_source_url: Optional[str] = None,
                    ttclid: Optional[str] = None) -> Dict[str, Any]:
        """Build context object for TikTok Events API."""
        context = {}
        
        if client_ip:
            context["ip"] = client_ip
        if client_user_agent:
            context["user_agent"] = client_user_agent
        if event_source_url:
            context["page"] = {"url": event_source_url}
        if ttclid:
            context["ttclid"] = ttclid
            # Some docs suggest click_id in context too
            context["click_id"] = ttclid
        
        return context
    
    def _get_properties(
        self, 
        currency: Optional[str] = None, 
        value: Optional[float] = None,
        content_ids: Optional[List[str]] = None,
        content_name: Optional[str] = None,
        content_type: Optional[str] = None,
        contents: Optional[List[Dict[str, Any]]] = None,
        num_items: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build properties object for TikTok Events API (used for Purchase, AddToCart events)."""
        properties = {}
        
        if currency:
            properties["currency"] = currency
        
        if value is not None:
            properties["value"] = value
        
        if content_ids:
            properties["content_ids"] = content_ids
        
        if content_name:
            properties["content_name"] = content_name
        
        if content_type:
            properties["content_type"] = content_type
        
        if contents:
            properties["contents"] = contents
        
        if num_items is not None:
            properties["num_items"] = num_items
        
        return properties
    
    async def send_event(
        self,
        event_name: str,
        user: Dict[str, Any],
        context: Dict[str, Any],
        properties: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Send a conversion event to TikTok Events API.
        
        Args:
            event_name: Name of the event (e.g., "CompleteRegistration", "CompletePayment")
            user: User data dictionary (email, phone, etc.)
            context: Context data dictionary (ip, user_agent, page)
            properties: Optional properties dictionary (currency, value, etc.)
            event_id: Optional event ID for deduplication
        
        Returns:
            True if event was sent successfully, False otherwise
        """
        if not self.pixel_id or not self.access_token:
            logger.debug("TikTok Conversions API not configured, skipping event")
            return False
        
        try:
            # TikTok Events API correct payload structure:
            # Reference: https://business-api.tiktok.com/portal/docs?id=1797165504155649
            #
            # Root level fields:
            # - event_source: "web", "app", or "offline"
            # - event_source_id: Your TikTok Pixel ID
            # - data: Array of event objects
            #
            # Event object fields:
            # - event: Event name (e.g., "CompletePayment", "AddToCart")
            # - event_time: Unix timestamp (integer, seconds since epoch)
            # - event_id: Unique ID for deduplication
            # - user: User data (email, phone, ip, user_agent, external_id - all in user object)
            # - properties: Event-specific data (value, currency, contents, etc.)
            
            # Merge context data (ip, user_agent) into user object
            # TikTok expects ip and user_agent inside user object, not in separate context
            merged_user = user.copy()
            if context:
                if context.get("ip"):
                    merged_user["ip"] = context["ip"]
                if context.get("user_agent"):
                    merged_user["user_agent"] = context["user_agent"]
            
            # TikTok cookies for better attribution
            if context.get("ttclid"):
                 merged_user["ttclid"] = context["ttclid"]
                 merged_user["click_id"] = context["ttclid"]  # Alias for better compatibility
            
            # Build the event object
            event = {
                "event": event_name,
                "event_time": int(time.time()),  # Unix timestamp as integer
                "user": merged_user,
            }
            
            # Add page URL to properties if available
            if context and context.get("page", {}).get("url"):
                if properties is None:
                    properties = {}
                properties["page_url"] = context["page"]["url"]

            # Add click_id to context if available (for some implementations)
            if context.get("ttclid"):
                if properties is None:
                    properties = {}
                # Add click_id to properties as well, just in case
                properties["click_id"] = context["ttclid"]
            
            # Add properties if provided
            if properties:
                event["properties"] = properties
            
            # Add event_id for deduplication if provided
            if event_id:
                event["event_id"] = event_id
                logger.info(f"🎯 Sending {event_name} event with event_id: {event_id} for deduplication")
            else:
                logger.warning(f"⚠️  {event_name} event sent WITHOUT event_id - deduplication not possible!")
            
            # TikTok API requires:
            # - event_source at root level
            # - event_source_id at root level
            # - events wrapped in a "data" array
            payload = {
                "event_source": "web",
                "event_source_id": self.pixel_id,
                "data": [event]
            }
            
            # Log CompletePayment event details for debugging
            if event_name == "CompletePayment":
                value = properties.get("value") if properties else None
                currency = properties.get("currency") if properties else None
                logger.info(f"💰 CompletePayment Event Details: value={value}, currency={currency}, user={user.get('email', 'N/A')[:10]}..., external_id={user.get('external_id', 'N/A')}")
                
                # Log all user fields for verification
                logger.info(f"📊 CompletePayment User Data Fields:")
                logger.info(f"  - email: {'✓' if user.get('email') else '✗'}")
                logger.info(f"  - first_name: {'✓' if user.get('first_name') else '✗'}")
                logger.info(f"  - last_name: {'✓' if user.get('last_name') else '✗'}")
                logger.info(f"  - external_id: {'✓' if user.get('external_id') else '✗'}")
                logger.info(f"  - ttp: {'✓' if user.get('ttp') else '✗'} ({user.get('ttp', 'N/A')})")
                logger.info(f"  - ttclid: {'✓' if user.get('ttclid') else '✗'} ({user.get('ttclid', 'N/A')})")
                logger.info(f"📊 CompletePayment Context Fields:")
                logger.info(f"  - ip: {'✓' if context.get('ip') else '✗'}")
                logger.info(f"  - user_agent: {'✓' if context.get('user_agent') else '✗'}")
                logger.info(f"  - page.url: {'✓' if context.get('page', {}).get('url') else '✗'}")
            
            # Log AddToCart event details for debugging
            if event_name == "AddToCart":
                value = properties.get("value") if properties else None
                currency = properties.get("currency") if properties else None
                content_ids = properties.get("content_ids") if properties else None
                content_name = properties.get("content_name") if properties else None
                content_type = properties.get("content_type") if properties else None
                contents = properties.get("contents") if properties else None
                num_items = properties.get("num_items") if properties else None
                event_url = context.get("page", {}).get("url") if context else None
                logger.debug(f"🛒 AddToCart Event Details: value={value}, currency={currency}, content_ids={content_ids}, content_name={content_name}, content_type={content_type}, num_items={num_items}, url={event_url}, user={user.get('email', 'N/A')[:10]}..., external_id={user.get('external_id', 'N/A')}")
                
                # Log all user fields for verification
                logger.debug(f"📊 AddToCart User Data Fields:")
                logger.debug(f"  - email: {'✓' if user.get('email') else '✗'}")
                logger.debug(f"  - first_name: {'✓' if user.get('first_name') else '✗'}")
                logger.debug(f"  - last_name: {'✓' if user.get('last_name') else '✗'}")
                logger.debug(f"  - external_id: {'✓' if user.get('external_id') else '✗'}")
                logger.debug(f"  - ttp: {'✓' if user.get('ttp') else '✗'}")
                logger.debug(f"  - ttclid: {'✓' if user.get('ttclid') else '✗'}")
                logger.debug(f"📊 AddToCart Context Fields:")
                logger.debug(f"  - ip: {'✓' if context.get('ip') else '✗'}")
                logger.debug(f"  - user_agent: {'✓' if context.get('user_agent') else '✗'}")
                logger.debug(f"  - page.url: {'✓' if context.get('page', {}).get('url') else '✗'}")
                logger.debug(f"📦 AddToCart Properties Fields:")
                logger.debug(f"  - currency: {'✓' if currency else '✗'}")
                logger.debug(f"  - value: {'✓' if value is not None else '✗'}")
                logger.debug(f"  - content_ids: {'✓' if content_ids else '✗'}")
                logger.debug(f"  - content_name: {'✓' if content_name else '✗'}")
                logger.debug(f"  - content_type: {'✓' if content_type else '✗'}")
                logger.debug(f"  - contents: {'✓' if contents else '✗'}")
                logger.debug(f"  - num_items: {'✓' if num_items is not None else '✗'}")
            
            # Log the complete payload being sent to TikTok (mask access token)
            payload_for_logging = payload.copy()
            
            # Log concise summary to main console (no JSON)
            logger.info(f"[OUT] Sending {event_name} event to TikTok Events API")
            
            # Log full details to dedicated file
            tiktok_conversions_logger.info("=" * 100)
            tiktok_conversions_logger.info(f"[OUT] OUTGOING REQUEST - {event_name} Event")
            tiktok_conversions_logger.info(f"URL: {self.api_url}")
            tiktok_conversions_logger.info(f"HTTP Method: POST")
            tiktok_conversions_logger.info(f"Request Payload:")
            tiktok_conversions_logger.info(json.dumps(payload_for_logging, indent=2))
            tiktok_conversions_logger.info("=" * 100)
            
            # Send the request with Access-Token header
            headers = {
                "Content-Type": "application/json",
                "Access-Token": self.access_token,
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                result = response.json()
                
                # Log concise response to main console (no JSON)
                code = result.get("code", -1)
                message = result.get("message", "Unknown")
                logger.info(f"[IN] TikTok response: {response.status_code} - Code: {code}, Message: {message}")
                
                # Log full response to dedicated file
                tiktok_conversions_logger.info("=" * 100)
                tiktok_conversions_logger.info(f"[IN] INCOMING RESPONSE - {event_name} Event")
                tiktok_conversions_logger.info(f"HTTP Status Code: {response.status_code}")
                tiktok_conversions_logger.info(f"Response Headers: {dict(response.headers)}")
                tiktok_conversions_logger.info(f"Response Body:")
                tiktok_conversions_logger.info(json.dumps(result, indent=2))
                tiktok_conversions_logger.info("=" * 100)
                tiktok_conversions_logger.info("")  # Empty line for readability
                
                # Check for errors in response
                if code != 0:
                    error_message = result.get("message", "Unknown error")
                    logger.error(f"TikTok Events API error: Code {code}, Message: {error_message}")
                    return False
                
                # Check HTTP status
                if response.status_code != 200:
                    logger.error(f"TikTok Events API returned status {response.status_code}: {result}")
                    return False
                
                # Success
                if code == 0:
                    logger.info(f"[SUCCESS] {event_name} event successfully sent")
                    return True
                else:
                    logger.warning(f"[WARNING] TikTok returned code {code} for {event_name}")
                    return False
                    
        except httpx.HTTPStatusError as e:
            # Get error response details
            try:
                error_response = e.response.json()
                logger.error(f"TikTok Events API HTTP error {e.response.status_code}: {error_response}")
            except:
                logger.error(f"TikTok Events API HTTP error {e.response.status_code}: {e.response.text}")
            return False
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending TikTok Events API event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending TikTok Events API event: {str(e)}", exc_info=True)
            return False
    
    async def track_complete_registration(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_id: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None,
    ) -> bool:
        """
        Track CompleteRegistration event.
        
        Sends all TikTok-recommended parameters including:
        - User data: email, first/last name, external_id, ttp, ttclid
        - Context: client_ip, user_agent, page URL
        - Event ID: for deduplication (if provided)
        
        All PII (email, names) are automatically SHA-256 hashed before sending.
        TikTok cookies (ttp, ttclid) are passed as-is for attribution.
        """
        user = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            ttp=ttp,
            ttclid=ttclid,
        )
        
        context = self._get_context(
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            ttclid=ttclid,
        )
        
        return await self.send_event(
            event_name="CompleteRegistration",
            user=user,
            context=context,
            event_id=event_id,
        )
    
    async def track_initiate_checkout(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        event_source_url: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None,
        # Optional value parameters for when user selects a specific plan
        value: Optional[float] = None,
        currency: Optional[str] = "USD",
        content_ids: Optional[List[str]] = None,
        content_name: Optional[str] = None,
        content_type: Optional[str] = None,
        num_items: Optional[int] = None,
    ) -> bool:
        """Track InitiateCheckout event.
        
        Optionally includes value/currency when user selects a specific plan.
        This helps TikTok optimize for high-value checkouts.
        """
        user = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            ttp=ttp,
            ttclid=ttclid,
        )
        
        context = self._get_context(
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            ttclid=ttclid,
        )
        
        # Build properties if value is provided
        properties = None
        if value is not None:
            properties = self._get_properties(
                currency=currency,
                value=value,
                content_ids=content_ids,
                content_name=content_name,
                content_type=content_type,
                num_items=num_items,
            )
        
        return await self.send_event(
            event_name="InitiateCheckout",
            user=user,
            context=context,
            properties=properties,
        )
    
    async def track_purchase(
        self,
        value: float,
        currency: str = "USD",
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_id: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None,
    ) -> bool:
        """
        Track CompletePayment event (TikTok's Purchase event).
        
        Sends all TikTok-recommended parameters including:
        - User data: email, first/last name, external_id, ttp, ttclid
        - Context: client_ip, user_agent, page URL
        - Properties: value, currency
        - Event ID: for deduplication
        
        All PII (email, names) are automatically SHA-256 hashed before sending.
        TikTok cookies (ttp, ttclid) are passed as-is for attribution.
        """
        user = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            ttp=ttp,
            ttclid=ttclid,
        )
        
        context = self._get_context(
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            ttclid=ttclid,
        )
        
        properties = self._get_properties(
            currency=currency,
            value=value,
        )
        
        return await self.send_event(
            event_name="CompletePayment",
            user=user,
            context=context,
            properties=properties if properties else None,
            event_id=event_id,
        )
    
    async def track_view_content(
        self,
        email: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        event_source_url: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None,
    ) -> bool:
        """Track ViewContent event."""
        user = self._get_user_data(
            email=email,
            external_id=external_id,
            ttp=ttp,
            ttclid=ttclid,
        )
        
        context = self._get_context(
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            ttclid=ttclid,
        )
        
        return await self.send_event(
            event_name="ViewContent",
            user=user,
            context=context,
        )
    
    async def track_add_to_cart(
        self,
        currency: Optional[str] = "USD",
        value: Optional[float] = None,
        content_ids: Optional[List[str]] = None,
        content_name: Optional[str] = None,
        content_type: Optional[str] = None,
        contents: Optional[List[Dict[str, Any]]] = None,
        num_items: Optional[int] = None,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_id: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None,
    ) -> bool:
        """
        Track AddToCart event for SaaS subscription page.
        
        Sends all TikTok-recommended parameters including:
        - User data: email, first_name, last_name, external_id, ttp, ttclid
        - Context: client_ip, user_agent, page URL
        - Properties: currency, value, content_ids, content_name, content_type, contents, num_items
        - Event ID: for deduplication (if provided)
        
        All PII (email, names) are automatically SHA-256 hashed before sending.
        TikTok cookies (ttp, ttclid) are passed as-is for attribution.
        """
        user = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            ttp=ttp,
            ttclid=ttclid,
        )
        
        context = self._get_context(
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            ttclid=ttclid,
        )
        
        properties = self._get_properties(
            currency=currency,
            value=value,
            content_ids=content_ids,
            content_name=content_name,
            content_type=content_type,
            contents=contents,
            num_items=num_items,
        )
        
        return await self.send_event(
            event_name="AddToCart",
            user=user,
            context=context,
            properties=properties if properties else None,
            event_id=event_id,
        )

    async def track_start_trial(
        self,
        value: float,
        currency: str = "USD",
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_id: Optional[str] = None,
        ttp: Optional[str] = None,
        ttclid: Optional[str] = None,
    ) -> bool:
        """
        Track StartTrial event (used for trial starts).
        
        Sends all TikTok-recommended parameters including:
        - User data: email, first/last name, external_id, ttp, ttclid
        - Context: client_ip, user_agent, page URL
        - Properties: value, currency
        - Event ID: for deduplication
        
        All PII (email, names) are automatically SHA-256 hashed before sending.
        TikTok cookies (ttp, ttclid) are passed as-is for attribution.
        """
        user = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            ttp=ttp,
            ttclid=ttclid,
        )
        
        context = self._get_context(
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            ttclid=ttclid,
        )
        
        properties = self._get_properties(
            currency=currency,
            value=value,
        )
        
        return await self.send_event(
            event_name="StartTrial",
            user=user,
            context=context,
            properties=properties if properties else None,
            event_id=event_id,
        )

