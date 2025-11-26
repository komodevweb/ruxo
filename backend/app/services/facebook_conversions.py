"""
Facebook Conversions API Service

This service handles server-side tracking of Facebook conversion events
using the Facebook Conversions API (formerly Server-Side API).
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

logger = logging.getLogger(__name__)

# Create dedicated Facebook Conversions API logger that writes to file
fb_conversions_logger = logging.getLogger("facebook_conversions_api")
fb_conversions_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
log_dir = "/root/ruxo/logs"
os.makedirs(log_dir, exist_ok=True)

# Create rotating file handler (max 50MB per file, keep 5 files)
fb_log_file = os.path.join(log_dir, "facebook_conversions_api.log")
file_handler = RotatingFileHandler(
    fb_log_file,
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

# Add handler to fb_conversions_logger
fb_conversions_logger.addHandler(file_handler)

# Prevent propagation to avoid duplicate logs
fb_conversions_logger.propagate = False

class FacebookConversionsService:
    """Service for sending events to Facebook Conversions API."""
    
    def __init__(self):
        self.pixel_id = settings.FACEBOOK_PIXEL_ID
        self.access_token = settings.FACEBOOK_ACCESS_TOKEN
        self.api_url = "https://graph.facebook.com/v21.0"
        
        if not self.pixel_id or not self.access_token:
            logger.warning("Facebook Conversions API not configured. Pixel ID and Access Token required.")
    
    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA256 for Facebook Conversions API."""
        if not value:
            return ""
        return hashlib.sha256(value.lower().strip().encode('utf-8')).hexdigest()
    
    def _get_user_data(self, email: Optional[str] = None, phone: Optional[str] = None,
                      first_name: Optional[str] = None, last_name: Optional[str] = None,
                      external_id: Optional[str] = None, client_ip: Optional[str] = None,
                      client_user_agent: Optional[str] = None, fbp: Optional[str] = None,
                      fbc: Optional[str] = None) -> Dict[str, Any]:
        """Build user_data object for Facebook Conversions API."""
        user_data = {}
        
        if email:
            user_data["em"] = self._hash_value(email)
        if phone:
            user_data["ph"] = self._hash_value(phone)
        if first_name:
            user_data["fn"] = self._hash_value(first_name)
        if last_name:
            user_data["ln"] = self._hash_value(last_name)
        if external_id:
            user_data["external_id"] = external_id
        
        # Do not hash these fields
        if client_ip:
            user_data["client_ip_address"] = client_ip
        if client_user_agent:
            user_data["client_user_agent"] = client_user_agent
        if fbp:
            user_data["fbp"] = fbp
        if fbc:
            user_data["fbc"] = fbc
        
        return user_data
    
    def _get_event_data(self, event_source_url: Optional[str] = None) -> Dict[str, Any]:
        """Build event_data object for Facebook Conversions API."""
        event_data = {}
        
        if event_source_url:
            event_data["event_source_url"] = event_source_url
        
        return event_data
    
    def _get_custom_data(
        self, 
        currency: Optional[str] = None, 
        value: Optional[float] = None,
        content_ids: Optional[List[str]] = None,
        content_name: Optional[str] = None,
        content_type: Optional[str] = None,
        contents: Optional[List[Dict[str, Any]]] = None,
        num_items: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build custom_data object for Facebook Conversions API (used for Purchase, AddToCart events)."""
        custom_data = {}
        
        if currency:
            custom_data["currency"] = currency
        
        if value is not None:
            custom_data["value"] = value
        
        if content_ids:
            custom_data["content_ids"] = content_ids
        
        if content_name:
            custom_data["content_name"] = content_name
        
        if content_type:
            custom_data["content_type"] = content_type
        
        if contents:
            custom_data["contents"] = contents
        
        if num_items is not None:
            custom_data["num_items"] = num_items
        
        return custom_data
    
    async def send_event(
        self,
        event_name: str,
        user_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Send a conversion event to Facebook Conversions API.
        
        Args:
            event_name: Name of the event (e.g., "CompleteRegistration", "Purchase")
            user_data: User data dictionary (email, phone, etc.)
            event_data: Optional event data dictionary
            custom_data: Optional custom data dictionary
            event_id: Optional event ID for deduplication
        
        Returns:
            True if event was sent successfully, False otherwise
        """
        if not self.pixel_id or not self.access_token:
            logger.debug("Facebook Conversions API not configured, skipping event")
            return False
        
        try:
            # Build the event
            event = {
                "event_name": event_name,
                "event_time": int(time.time()),
                "action_source": "website",
                "user_data": user_data,
            }
            
            # Add event_source_url if provided
            if event_data and "event_source_url" in event_data:
                event["event_source_url"] = event_data["event_source_url"]
            
            # Add custom_data if provided
            if custom_data:
                event["custom_data"] = custom_data
            
            # Add event_id for deduplication if provided
            if event_id:
                event["event_id"] = event_id
                logger.info(f"🎯 Sending {event_name} event with event_id: {event_id} for deduplication")
            else:
                logger.warning(f"⚠️  {event_name} event sent WITHOUT event_id - deduplication not possible!")
            
            # Log Purchase event details for debugging
            if event_name == "Purchase":
                value = custom_data.get("value") if custom_data else None
                currency = custom_data.get("currency") if custom_data else None
                logger.info(f"💰 Purchase Event Details: value={value}, currency={currency}, user={user_data.get('em', 'N/A')[:10]}..., external_id={user_data.get('external_id', 'N/A')}")
                
                # Log all user_data fields for verification
                logger.info(f"📊 Purchase User Data Fields:")
                logger.info(f"  - em (email): {'✓' if user_data.get('em') else '✗'}")
                logger.info(f"  - fn (first name): {'✓' if user_data.get('fn') else '✗'}")
                logger.info(f"  - ln (last name): {'✓' if user_data.get('ln') else '✗'}")
                logger.info(f"  - external_id: {'✓' if user_data.get('external_id') else '✗'}")
                logger.info(f"  - client_ip_address: {'✓' if user_data.get('client_ip_address') else '✗'}")
                logger.info(f"  - client_user_agent: {'✓' if user_data.get('client_user_agent') else '✗'}")
                logger.info(f"  - fbp: {'✓' if user_data.get('fbp') else '✗'}")
                logger.info(f"  - fbc: {'✓' if user_data.get('fbc') else '✗'}")
            
            # Log AddToCart event details for debugging
            if event_name == "AddToCart":
                value = custom_data.get("value") if custom_data else None
                currency = custom_data.get("currency") if custom_data else None
                content_ids = custom_data.get("content_ids") if custom_data else None
                content_name = custom_data.get("content_name") if custom_data else None
                content_type = custom_data.get("content_type") if custom_data else None
                contents = custom_data.get("contents") if custom_data else None
                num_items = custom_data.get("num_items") if custom_data else None
                event_url = event_data.get("event_source_url") if event_data else None
                logger.info(f"🛒 AddToCart Event Details: value={value}, currency={currency}, content_ids={content_ids}, content_name={content_name}, content_type={content_type}, num_items={num_items}, url={event_url}, user={user_data.get('em', 'N/A')[:10]}..., external_id={user_data.get('external_id', 'N/A')}")
                
                # Log all user_data fields for verification
                logger.info(f"📊 AddToCart User Data Fields:")
                logger.info(f"  - em (email): {'✓' if user_data.get('em') else '✗'}")
                logger.info(f"  - fn (first name): {'✓' if user_data.get('fn') else '✗'}")
                logger.info(f"  - ln (last name): {'✓' if user_data.get('ln') else '✗'}")
                logger.info(f"  - external_id: {'✓' if user_data.get('external_id') else '✗'}")
                logger.info(f"  - client_ip_address: {'✓' if user_data.get('client_ip_address') else '✗'}")
                logger.info(f"  - client_user_agent: {'✓' if user_data.get('client_user_agent') else '✗'}")
                logger.info(f"  - fbp: {'✓' if user_data.get('fbp') else '✗'}")
                logger.info(f"  - fbc: {'✓' if user_data.get('fbc') else '✗'}")
                
                # Log all custom_data fields for verification
                logger.info(f"📦 AddToCart Custom Data Fields:")
                logger.info(f"  - currency: {'✓' if currency else '✗'}")
                logger.info(f"  - value: {'✓' if value is not None else '✗'}")
                logger.info(f"  - content_ids: {'✓' if content_ids else '✗'}")
                logger.info(f"  - content_name: {'✓' if content_name else '✗'}")
                logger.info(f"  - content_type: {'✓' if content_type else '✗'}")
                logger.info(f"  - contents: {'✓' if contents else '✗'}")
                logger.info(f"  - num_items: {'✓' if num_items is not None else '✗'}")
            
            # Build the request payload
            payload = {
                "data": [event],
                "access_token": self.access_token,
            }
            
            # Log the complete payload being sent to Facebook (mask access token)
            import json
            payload_for_logging = {
                "data": [event],
                "access_token": f"{self.access_token[:10]}...{self.access_token[-4:]}" if self.access_token else "None"
            }
            
            # Log concise summary to main console (no JSON)
            logger.info(f"📤 Sending {event_name} event to Facebook Conversions API")
            
            # Log full details to dedicated file
            fb_conversions_logger.info("=" * 100)
            fb_conversions_logger.info(f"📤 OUTGOING REQUEST - {event_name} Event")
            fb_conversions_logger.info(f"URL: {self.api_url}/{self.pixel_id}/events")
            fb_conversions_logger.info(f"HTTP Method: POST")
            fb_conversions_logger.info(f"Request Payload:")
            fb_conversions_logger.info(json.dumps(payload_for_logging, indent=2))
            fb_conversions_logger.info("=" * 100)
            
            # Send the request
            url = f"{self.api_url}/{self.pixel_id}/events"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                result = response.json()
                
                # Log concise response to main console (no JSON)
                events_received = result.get("events_received", 0)
                logger.info(f"📥 Facebook response: {response.status_code} - {events_received} event(s) received")
                
                # Log full response to dedicated file
                fb_conversions_logger.info("=" * 100)
                fb_conversions_logger.info(f"📥 INCOMING RESPONSE - {event_name} Event")
                fb_conversions_logger.info(f"HTTP Status Code: {response.status_code}")
                fb_conversions_logger.info(f"Response Headers: {dict(response.headers)}")
                fb_conversions_logger.info(f"Response Body:")
                fb_conversions_logger.info(json.dumps(result, indent=2))
                fb_conversions_logger.info("=" * 100)
                fb_conversions_logger.info("")  # Empty line for readability
                
                # Check for errors in response
                if "error" in result:
                    error_details = result["error"]
                    logger.error(f"Facebook Conversions API error: {error_details}")
                    logger.error(f"Error details - Code: {error_details.get('code')}, Message: {error_details.get('message')}, Type: {error_details.get('type')}")
                    return False
                
                # Check HTTP status
                if response.status_code != 200:
                    logger.error(f"Facebook Conversions API returned status {response.status_code}: {result}")
                    return False
                
                # Check events_received
                events_received_check = result.get("events_received", 0)
                if events_received_check > 0:
                    logger.info(f"✅ {event_name} event successfully sent")
                    return True
                else:
                    logger.warning(f"⚠️  Facebook received 0 events for {event_name}")
                    return False
                    
        except httpx.HTTPStatusError as e:
            # Get error response details
            try:
                error_response = e.response.json()
                logger.error(f"Facebook Conversions API HTTP error {e.response.status_code}: {error_response}")
            except:
                logger.error(f"Facebook Conversions API HTTP error {e.response.status_code}: {e.response.text}")
            return False
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending Facebook Conversions API event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending Facebook Conversions API event: {str(e)}", exc_info=True)
            return False
    
    async def track_complete_registration(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Track CompleteRegistration event.
        
        Sends all Meta-recommended parameters including:
        - User data: email, first/last name, external_id, client_ip, user_agent, fbp, fbc
        - Event data: event_source_url
        - Event ID: for deduplication (if provided)
        
        All PII (email, names) are automatically SHA-256 hashed before sending.
        """
        user_data = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
        )
        
        event_data = self._get_event_data(
            event_source_url=event_source_url,
        )
        
        return await self.send_event(
            event_name="CompleteRegistration",
            user_data=user_data,
            event_data=event_data,
            event_id=event_id,
        )
    
    async def track_initiate_checkout(
        self,
        email: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        event_source_url: Optional[str] = None,
    ) -> bool:
        """Track InitiateCheckout event."""
        user_data = self._get_user_data(
            email=email,
            external_id=external_id,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
        )
        
        event_data = self._get_event_data(
            event_source_url=event_source_url,
        )
        
        return await self.send_event(
            event_name="InitiateCheckout",
            user_data=user_data,
            event_data=event_data,
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
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Track Purchase event.
        
        Sends all Facebook-recommended parameters including:
        - User data: email, first/last name, external_id, client_ip, user_agent, fbp, fbc
        - Custom data: value, currency
        - Event data: event_source_url
        - Event ID: for deduplication
        
        All PII (email, names) are automatically SHA-256 hashed before sending.
        """
        user_data = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
        )
        
        event_data = self._get_event_data(
            event_source_url=event_source_url,
        )
        
        custom_data = self._get_custom_data(
            currency=currency,
            value=value,
        )
        
        return await self.send_event(
            event_name="Purchase",
            user_data=user_data,
            event_data=event_data,
            custom_data=custom_data if custom_data else None,
            event_id=event_id,
        )
    
    async def track_lead(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Track Lead event.
        
        Used for signups that require email verification - fires when user submits
        the signup form but before they verify their email.
        CompleteRegistration fires later when email is verified.
        """
        user_data = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
        )
        
        event_data = self._get_event_data(
            event_source_url=event_source_url,
        )
        
        return await self.send_event(
            event_name="Lead",
            user_data=user_data,
            event_data=event_data,
            event_id=event_id,
        )
    
    async def track_view_content(
        self,
        email: Optional[str] = None,
        external_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        event_source_url: Optional[str] = None,
    ) -> bool:
        """Track ViewContent event."""
        user_data = self._get_user_data(
            email=email,
            external_id=external_id,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
        )
        
        event_data = self._get_event_data(
            event_source_url=event_source_url,
        )
        
        return await self.send_event(
            event_name="ViewContent",
            user_data=user_data,
            event_data=event_data,
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
        fbp: Optional[str] = None,
        fbc: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Track AddToCart event for SaaS subscription page.
        
        Sends all Meta-recommended parameters including:
        - User data: email, first_name, last_name, external_id, client_ip, user_agent, fbp, fbc
        - Custom data: currency, value, content_ids, content_name, content_type, contents, num_items
        - Event data: event_source_url
        - Event ID: for deduplication (if provided)
        
        All PII (email, names) are automatically SHA-256 hashed before sending.
        """
        user_data = self._get_user_data(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbp=fbp,
            fbc=fbc,
        )
        
        event_data = self._get_event_data(
            event_source_url=event_source_url,
        )
        
        custom_data = self._get_custom_data(
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
            user_data=user_data,
            event_data=event_data,
            custom_data=custom_data if custom_data else None,
            event_id=event_id,
        )

