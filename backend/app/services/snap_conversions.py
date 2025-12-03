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
    """Service for sending events to Snap Conversions API v3."""
    
    def __init__(self):
        self.pixel_id = settings.SNAP_PIXEL_ID
        self.access_token = settings.SNAP_ACCESS_TOKEN
        # v3 API format: https://tr.snapchat.com/v3/{pixel_id}/events?access_token={token}
        if self.pixel_id and self.access_token:
            self.api_url = f"https://tr.snapchat.com/v3/{self.pixel_id}/events?access_token={self.access_token}"
        else:
            self.api_url = None
        
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
        Send a conversion event to Snap Conversions API v3.
        Format: POST https://tr.snapchat.com/v3/{pixel_id}/events?access_token={token}
        
        Payload structure:
        {
          "data": [{
            "event_name": "PURCHASE",
            "action_source": "website",
            "event_source_url": "https://example.com",
            "event_time": 1234567890,
            "user_data": {
              "em": ["hashed_email"],
              "ph": ["hashed_phone"],
              "user_agent": "...",
              "client_ip_address": "...",
              "sc_click_id": "...",
              "sc_cookie1": "..."
            },
            "custom_data": {
              "event_id": "...",
              "value": "...",
              "currency": "...",
              "content_ids": ["..."]
            }
          }]
        }
        """
        if not self.pixel_id or not self.access_token or not self.api_url:
            logger.debug("Snap Conversions API not configured, skipping event")
            return False
            
        try:
            if event_time is None:
                # Snap v3 expects milliseconds (not seconds!)
                event_time = int(time.time() * 1000)
            
            # Build user_data object
            user_data_obj = {}
            
            if email:
                user_data_obj["em"] = [self._hash_value(email)]
            if phone:
                user_data_obj["ph"] = [self._hash_value(phone)]
            if client_user_agent:
                user_data_obj["user_agent"] = client_user_agent
            if client_ip:
                user_data_obj["client_ip_address"] = client_ip
            if sc_cookie1:
                user_data_obj["cookie1"] = sc_cookie1  # v3 uses "cookie1" not "sc_cookie1"
            if sc_click_id:
                user_data_obj["click_id"] = sc_click_id  # v3 uses "click_id" not "sc_click_id"
            if external_id:
                user_data_obj["external_id"] = [external_id]  # User ID in array format
            
            # Build custom_data object
            custom_data_obj = {}
            
            if value is not None:
                custom_data_obj["value"] = float(value)  # v3 expects number, not string
            if currency:
                custom_data_obj["currency"] = currency
            if content_ids:
                custom_data_obj["content_ids"] = content_ids
            if content_category:
                custom_data_obj["content_category"] = content_category
            if number_items:
                custom_data_obj["number_items"] = number_items
            
            # Build event object
            event_data = {
                "event_name": event_name,
                "action_source": "WEB",  # v3 uses "WEB" not "website"
                "event_time": event_time,  # Milliseconds
            }
            
            # Add event_id to event object (not custom_data for v3)
            if event_id:
                event_data["event_id"] = event_id
            
            if event_source_url:
                event_data["event_source_url"] = event_source_url
            
            # Add user_data if not empty
            if user_data_obj:
                event_data["user_data"] = user_data_obj
            
            # Add custom_data if not empty
            if custom_data_obj:
                event_data["custom_data"] = custom_data_obj

            # v3 API expects { "data": [array of events] }
            payload = {
                "data": [event_data]
            }

            # Prepare for logging
            payload_for_logging = payload.copy()
            
            # Log concise
            logger.info(f"[OUT] Sending {event_name} event to Snap Conversions API v3")
            
            # Log detailed
            snap_conversions_logger.info("=" * 100)
            snap_conversions_logger.info(f"[OUT] OUTGOING REQUEST - {event_name} Event (v3)")
            snap_conversions_logger.info(f"URL: {self.api_url}")
            snap_conversions_logger.info(f"Method: POST")
            snap_conversions_logger.info(f"Payload:")
            snap_conversions_logger.info(json.dumps(payload_for_logging, indent=2))
            snap_conversions_logger.info("=" * 100)
            
            headers = {
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                
                # v3 may return different response format
                try:
                    result = response.json()
                except:
                    result = {"status": "UNKNOWN", "text": response.text}
                
                # Log response
                logger.info(f"[IN] Snap response: {response.status_code}")
                
                snap_conversions_logger.info("=" * 100)
                snap_conversions_logger.info(f"[IN] INCOMING RESPONSE - {event_name} Event")
                snap_conversions_logger.info(f"Status Code: {response.status_code}")
                snap_conversions_logger.info(f"Body: {json.dumps(result, indent=2)}")
                snap_conversions_logger.info("=" * 100)
                snap_conversions_logger.info("")

                # v3 returns 200 for success
                if response.status_code == 200:
                    logger.info(f"[SUCCESS] {event_name} event successfully sent to Snap v3")
                    return True
                else:
                    logger.error(f"[ERROR] Snap API v3 returned {response.status_code}: {result}")
                    return False

        except Exception as e:
            logger.error(f"Error sending Snap Conversions API v3 event: {str(e)}", exc_info=True)
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

