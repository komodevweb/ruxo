"""
Snap Conversions API Service

This service handles server-side tracking of Snap conversion events
using the Snap Conversions API.
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

# Create dedicated Snap Conversions API logger that writes to file
snap_conversions_logger = logging.getLogger("snap_conversions_api")
snap_conversions_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent.parent
project_root = backend_dir.parent
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)

# Create rotating file handler (max 50MB per file, keep 5 files)
snap_log_file = os.path.join(log_dir, "snap_conversions_api.log")
file_handler = RotatingFileHandler(
    snap_log_file,
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

# Add handler to snap_conversions_logger
snap_conversions_logger.addHandler(file_handler)

# Prevent propagation to avoid duplicate logs
snap_conversions_logger.propagate = False

class SnapConversionsService:
    """Service for sending events to Snap Conversions API v2.
    
    Note: Canvas JWT tokens work with v2 API but NOT v3 API.
    v2 is the working version for our token type.
    """
    
    def __init__(self):
        self.pixel_id = settings.SNAP_PIXEL_ID
        self.access_token = settings.SNAP_ACCESS_TOKEN
        # Snap Conversions API v2 endpoint
        # Authentication: Bearer token in Authorization header
        # Note: Canvas JWT tokens work with v2, but get 401 with v3
        if self.pixel_id and self.access_token:
            self.api_url = "https://tr.snapchat.com/v2/conversion"
            self.validate_url = "https://tr.snapchat.com/v2/conversion/validate"
        else:
            self.api_url = None
            self.validate_url = None
        
        if not self.pixel_id or not self.access_token:
            logger.warning("Snap Conversions API not configured. Pixel ID and Access Token required.")
    
    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA256 for Snap Conversions API."""
        if not value:
            return ""
        return hashlib.sha256(value.lower().strip().encode('utf-8')).hexdigest()
    
        
    async def send_event(
        self,
        event_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        sc_cookie1: Optional[str] = None,
        sc_click_id: Optional[str] = None,
        event_source_url: Optional[str] = None,
        event_time: Optional[int] = None,
        event_id: Optional[str] = None,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        content_ids: Optional[List[str]] = None,
        content_category: Optional[List[str]] = None,
        number_items: Optional[List[int]] = None,
        external_id: Optional[str] = None,
    ) -> bool:
        """
        Send a conversion event to Snap Conversions API v2.
        Format: POST https://tr.snapchat.com/v2/conversion
        Authentication: Bearer token in Authorization header
        
        v2 Payload structure (flat) with ALL matching parameters:
        {
          "pixel_id": "...",
          "timestamp": "1234567890123",
          "event_type": "PURCHASE",
          "event_conversion_type": "WEB",
          "hashed_email": "...",           // SHA-256 hashed
          "hashed_phone_number": "...",    // SHA-256 hashed
          "hashed_ip_address": "...",      // SHA-256 hashed (v2 specific)
          "user_agent": "...",             // NOT hashed
          "uuid_c1": "...",                // Snap cookie, NOT hashed
          "click_id": "...",               // Snap Click ID, NOT hashed
          "client_dedup_id": "...",        // User ID, NOT hashed
          "page_url": "https://example.com",
          "price": "99.99",                // String
          "currency": "USD",
          "item_ids": "product1,product2", // Comma-separated
          "transaction_id": "..."
        }
        """
        if not self.pixel_id or not self.access_token or not self.api_url:
            logger.debug("Snap Conversions API not configured, skipping event")
            return False
            
        try:
            if event_time is None:
                # v2 expects milliseconds as string
                event_time = int(time.time() * 1000)
            
            # Build v2 payload (flat structure) with ALL matching parameters
            payload = {
                "pixel_id": self.pixel_id,
                "timestamp": str(event_time),
                "event_type": event_name,
                "event_conversion_type": "WEB",
            }
            
            # User Matching Parameters (send as many as possible for best matching)
            
            # Email - hashed (CRITICAL for matching)
            if email:
                payload["hashed_email"] = self._hash_value(email)
            
            # Phone - hashed (CRITICAL for matching)
            if phone:
                payload["hashed_phone_number"] = self._hash_value(phone)
            
            # IP Address - hashed in v2 (NOT hashed in v3)
            if client_ip:
                payload["hashed_ip_address"] = self._hash_value(client_ip)
            
            # User Agent - NOT hashed (device/browser info)
            if client_user_agent:
                payload["user_agent"] = client_user_agent
            
            # Snap Cookie - NOT hashed (RECOMMENDED for better matching)
            if sc_cookie1:
                payload["uuid_c1"] = sc_cookie1
            
            # Click ID - NOT hashed (CRITICAL for ad attribution!)
            if sc_click_id:
                payload["click_id"] = sc_click_id
            
            # External ID - NOT hashed (user deduplication)
            if external_id:
                payload["client_dedup_id"] = external_id
            
            # Event URL
            if event_source_url:
                payload["page_url"] = event_source_url
            
            # Commerce Parameters
            if value is not None:
                payload["price"] = str(value)
            
            if currency:
                payload["currency"] = currency
            
            # Item IDs - comma-separated string in v2
            if content_ids:
                payload["item_ids"] = ",".join(content_ids)
            
            # Item Category - single value in v2
            if content_category and len(content_category) > 0:
                payload["item_category"] = content_category[0]
            
            # Number of Items - single value as string in v2
            if number_items:
                # Handle both list and integer
                if isinstance(number_items, list) and len(number_items) > 0:
                    payload["number_items"] = str(number_items[0])
                elif isinstance(number_items, int):
                    payload["number_items"] = str(number_items)
            
            # Transaction ID for deduplication
            if event_id:
                payload["transaction_id"] = event_id
            
            # Prepare for logging
            payload_for_logging = payload.copy()
            
            # Log concise
            logger.info(f"[OUT] Sending {event_name} event to Snap Conversions API v2")
            
            # Log detailed
            snap_conversions_logger.info("=" * 100)
            snap_conversions_logger.info(f"[OUT] OUTGOING REQUEST - {event_name} Event (v2)")
            snap_conversions_logger.info(f"URL: {self.api_url}")
            snap_conversions_logger.info(f"Method: POST")
            snap_conversions_logger.info(f"Payload:")
            snap_conversions_logger.info(json.dumps(payload_for_logging, indent=2))
            snap_conversions_logger.info("=" * 100)
            
            # Authentication: Bearer token in Authorization header (OAuth 2.0 standard)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                
                # Parse response
                try:
                    result = response.json()
                except:
                    result = {"status": "UNKNOWN", "text": response.text}
                
                # Log response
                logger.info(f"[IN] Snap v2 response: {response.status_code}")
                
                snap_conversions_logger.info("=" * 100)
                snap_conversions_logger.info(f"[IN] INCOMING RESPONSE - {event_name} Event")
                snap_conversions_logger.info(f"Status Code: {response.status_code}")
                snap_conversions_logger.info(f"Body: {json.dumps(result, indent=2)}")
                snap_conversions_logger.info("=" * 100)
                snap_conversions_logger.info("")

                # v2 returns 200 for success with status "SUCCESS"
                if response.status_code == 200:
                    logger.info(f"[SUCCESS] {event_name} event successfully sent to Snap v2")
                    return True
                else:
                    logger.error(f"[ERROR] Snap API v2 returned {response.status_code}: {result}")
                    return False

        except Exception as e:
            logger.error(f"Error sending Snap Conversions API v2 event: {str(e)}", exc_info=True)
            return False

    async def track_complete_registration(
        self,
        email: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        page_url: Optional[str] = None,
        sc_cookie1: Optional[str] = None,
        sc_clid: Optional[str] = None,
        event_id: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> bool:
        """Track SIGN_UP event."""
        return await self.send_event(
            event_name="SIGN_UP",
            email=email,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            sc_cookie1=sc_cookie1,
            sc_click_id=sc_clid,
            event_source_url=page_url,
            event_id=event_id,
            external_id=external_id,
        )

    async def track_initiate_checkout(
        self,
        email: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        page_url: Optional[str] = None,
        sc_cookie1: Optional[str] = None,
        sc_clid: Optional[str] = None,
        price: Optional[float] = None,
        currency: Optional[str] = "USD",
        item_ids: Optional[List[str]] = None,
        number_items: Optional[int] = None,
        event_id: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> bool:
        """Track START_CHECKOUT event."""
        return await self.send_event(
            event_name="START_CHECKOUT",
            email=email,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            sc_cookie1=sc_cookie1,
            sc_click_id=sc_clid,
            event_source_url=page_url,
            event_id=event_id,
            value=price,
            currency=currency,
            content_ids=item_ids,
            number_items=number_items if number_items is not None else None,
            external_id=external_id,
        )

    async def track_purchase(
        self,
        price: float,
        currency: str = "USD",
        transaction_id: Optional[str] = None,
        email: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        page_url: Optional[str] = None,
        sc_cookie1: Optional[str] = None,
        sc_clid: Optional[str] = None,
        item_ids: Optional[List[str]] = None,
        number_items: Optional[int] = None,
        external_id: Optional[str] = None,
    ) -> bool:
        """Track PURCHASE event."""
        return await self.send_event(
            event_name="PURCHASE",
            email=email,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            sc_cookie1=sc_cookie1,
            sc_click_id=sc_clid,
            event_source_url=page_url,
            event_id=transaction_id,
            value=price,
            currency=currency,
            content_ids=item_ids,
            number_items=[number_items] if number_items is not None else None,
            external_id=external_id,
        )

    async def track_add_to_cart(
        self,
        email: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        page_url: Optional[str] = None,
        sc_cookie1: Optional[str] = None,
        sc_clid: Optional[str] = None,
        price: Optional[float] = None,
        currency: Optional[str] = "USD",
        item_ids: Optional[List[str]] = None,
        number_items: Optional[int] = None,
        event_id: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> bool:
        """Track ADD_CART event."""
        return await self.send_event(
            event_name="ADD_CART",
            email=email,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            sc_cookie1=sc_cookie1,
            sc_click_id=sc_clid,
            event_source_url=page_url,
            event_id=event_id,
            value=price,
            currency=currency,
            content_ids=item_ids,
            number_items=[number_items] if number_items is not None else None,
            external_id=external_id,
        )

    async def track_view_content(
        self,
        email: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        page_url: Optional[str] = None,
        sc_cookie1: Optional[str] = None,
        sc_clid: Optional[str] = None,
        event_id: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> bool:
        """Track VIEW_CONTENT event."""
        return await self.send_event(
            event_name="VIEW_CONTENT",
            email=email,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            sc_cookie1=sc_cookie1,
            sc_click_id=sc_clid,
            event_source_url=page_url,
            event_id=event_id,
            external_id=external_id,
        )

    async def track_start_trial(
        self,
        price: float,
        currency: str = "USD",
        transaction_id: Optional[str] = None,
        email: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        page_url: Optional[str] = None,
        sc_cookie1: Optional[str] = None,
        sc_clid: Optional[str] = None,
        item_ids: Optional[List[str]] = None,
        external_id: Optional[str] = None,
    ) -> bool:
        """Track START_TRIAL event."""
        return await self.send_event(
            event_name="START_TRIAL",
            email=email,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            sc_cookie1=sc_cookie1,
            sc_click_id=sc_clid,
            event_source_url=page_url,
            event_id=transaction_id,
            value=price,
            currency=currency,
            content_ids=item_ids,
            external_id=external_id,
        )

