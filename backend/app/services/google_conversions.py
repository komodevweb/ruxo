"""
Google Ads Conversions API Service

This service handles server-side tracking of Google Ads conversion events
using the Google Ads API (uploadClickConversions).
"""
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import httpx
from app.core.config import settings
from logging.handlers import RotatingFileHandler
import os
import json

logger = logging.getLogger(__name__)

# Create dedicated Google Ads Conversions API logger that writes to file
google_conversions_logger = logging.getLogger("google_conversions_api")
google_conversions_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
# Determine project root relative to this file (backend/app/services/google_conversions.py)
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent.parent
project_root = backend_dir.parent
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)

# Create rotating file handler (max 50MB per file, keep 5 files)
google_log_file = os.path.join(log_dir, "google_conversions_api.log")
file_handler = RotatingFileHandler(
    google_log_file,
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

# Add handler to google_conversions_logger
google_conversions_logger.addHandler(file_handler)

# Prevent propagation to avoid duplicate logs
google_conversions_logger.propagate = False

class GoogleAdsConversionsService:
    """Service for sending events to Google Ads API."""
    
    def __init__(self):
        self.developer_token = settings.GOOGLE_ADS_DEVELOPER_TOKEN
        self.customer_id = settings.GOOGLE_ADS_CUSTOMER_ID
        self.client_id = settings.GOOGLE_ADS_CLIENT_ID
        self.client_secret = settings.GOOGLE_ADS_CLIENT_SECRET
        self.refresh_token = settings.GOOGLE_ADS_REFRESH_TOKEN
        
        # Access token management
        self._access_token = None
        self._token_expiry = 0
        
        # Version 17 is current as of late 2024/2025
        self.api_version = "v17" 
        
        if self.customer_id:
            self.customer_id = self.customer_id.replace("-", "")
            
        self.base_url = f"https://googleads.googleapis.com/{self.api_version}/customers/{self.customer_id}" if self.customer_id else ""
        
        if not all([self.developer_token, self.customer_id, self.client_id, self.client_secret, self.refresh_token]):
            logger.warning("Google Ads Conversions API not configured. All credentials required.")
            
        # Map standard events to configured conversion actions
        self.event_mapping = {
            "Purchase": settings.GOOGLE_ADS_CONVERSION_ACTION_PURCHASE,
            "CompleteRegistration": settings.GOOGLE_ADS_CONVERSION_ACTION_SIGNUP,
            "AddToCart": settings.GOOGLE_ADS_CONVERSION_ACTION_ADD_TO_CART,
            "InitiateCheckout": settings.GOOGLE_ADS_CONVERSION_ACTION_INITIATE_CHECKOUT,
            "ViewContent": settings.GOOGLE_ADS_CONVERSION_ACTION_VIEW_CONTENT,
            "StartTrial": settings.GOOGLE_ADS_CONVERSION_ACTION_START_TRIAL,
        }

    async def _get_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
            
        if not self.refresh_token or not self.client_id or not self.client_secret:
            return None
            
        try:
            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(token_url, data=payload)
                if response.status_code != 200:
                    logger.error(f"Failed to refresh Google Ads token: {response.text}")
                    return None
                    
                data = response.json()
                self._access_token = data["access_token"]
                # Token usually valid for 1 hour (3600s), subtract buffer
                self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
                
                return self._access_token
        except Exception as e:
            logger.error(f"Error refreshing Google Ads token: {str(e)}")
            return None

    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA256 for Google Ads API (must be hex)."""
        if not value:
            return ""
        # Normalize: lowercase, remove leading/trailing whitespace
        # For phone: E.164 format expected before hashing, but we'll just do basic cleanup
        return hashlib.sha256(value.lower().strip().encode('utf-8')).hexdigest()
    
    def _get_user_identifiers(self, email: Optional[str] = None, phone: Optional[str] = None) -> List[Dict[str, Any]]:
        """Build userIdentifiers list for Google Ads API."""
        identifiers = []
        
        if email:
            identifiers.append({"hashedEmail": self._hash_value(email)})
        if phone:
            identifiers.append({"hashedPhoneNumber": self._hash_value(phone)})
            
        # Google Ads also supports address info but we typically don't have it fully structured
        # or it's less critical than email/phone for matching.
        
        return identifiers
    
    async def send_event(
        self,
        event_name: str,
        gclid: Optional[str],
        user_identifiers: List[Dict[str, Any]],
        conversion_value: Optional[float] = None,
        currency_code: str = "USD",
        conversion_time: Optional[str] = None,
        order_id: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
    ) -> bool:
        """
        Send a conversion event to Google Ads API.
        
        Args:
            event_name: Internal event name (e.g., "Purchase")
            gclid: Google Click ID
            user_identifiers: List of hashed user identifiers
            conversion_value: Value of the conversion
            currency_code: Currency code
            conversion_time: Time of conversion (defaults to now)
            order_id: Unique order ID (for deduplication)
            gbraid: GBRAID for iOS (optional)
            wbraid: WBRAID for iOS (optional)
        """
        if not all([self.developer_token, self.customer_id]):
            logger.debug("Google Ads API not configured, skipping event")
            return False
            
        # Get mapped conversion action
        conversion_action = self.event_mapping.get(event_name)
        if not conversion_action:
            logger.debug(f"No Google Ads conversion action mapped for event {event_name}, skipping")
            return False
            
        # Check if we have full resource name or just ID
        if "customers/" not in conversion_action:
             # Assume it's just the ID, construct full resource name
             conversion_action = f"customers/{self.customer_id}/conversionActions/{conversion_action}"
             
        access_token = await self._get_access_token()
        if not access_token:
            logger.error("Could not get Google Ads access token")
            return False
            
        try:
            # Format conversion time: "yyyy-mm-dd hh:mm:ss+|-hh:mm"
            if not conversion_time:
                # Use current time in required format
                now = datetime.now(timezone.utc)
                # Python isoformat includes 'T' and microseconds, Google expects "2018-03-05 09:15:00-05:00"
                # We'll use a simpler format usually accepted or construct it manually
                conversion_time = now.strftime("%Y-%m-%d %H:%M:%S+00:00")
            
            # Build conversion object
            conversion = {
                "conversionAction": conversion_action,
                "conversionDateTime": conversion_time,
            }
            
            if gclid:
                conversion["gclid"] = gclid
            if gbraid:
                conversion["gbraid"] = gbraid
            if wbraid:
                conversion["wbraid"] = wbraid
                
            # If no click ID is present, Google Ads uploadClickConversions might fail unless 
            # it's an Enhanced Conversion for Web (which uses user identifiers primarily).
            # However, uploadClickConversions *requires* a click ID (gclid, gbraid, wbraid) 
            # OR we should use a different method. But typically server-side conversions need a click ID.
            # If we only have email, we rely on "Enhanced Conversions" matching which technically 
            # is often sent via the same endpoint but might need gclid as well or special handling.
            # For now, we proceed. If gclid is missing and we have user identifiers, it might work 
            # if the conversion action is set up for it, but standard offline conversions need gclid.
            
            if conversion_value is not None:
                conversion["conversionValue"] = conversion_value
                conversion["currencyCode"] = currency_code
                
            if user_identifiers:
                conversion["userIdentifiers"] = user_identifiers
                
            if order_id:
                conversion["orderId"] = order_id
                
            # Build request payload
            payload = {
                "conversions": [conversion],
                "partialFailure": True,
                "validateOnly": False
            }
            
            # Log payload
            payload_for_logging = payload.copy()
            
            # Log concise summary
            logger.info(f"[OUT] Sending {event_name} event to Google Ads API")
            
            # Log full details
            google_conversions_logger.info("=" * 100)
            google_conversions_logger.info(f"[OUT] OUTGOING REQUEST - {event_name} Event")
            google_conversions_logger.info(f"URL: {self.base_url}:uploadClickConversions")
            google_conversions_logger.info(f"Request Payload:")
            google_conversions_logger.info(json.dumps(payload_for_logging, indent=2))
            google_conversions_logger.info("=" * 100)
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "developer-token": self.developer_token,
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}:uploadClickConversions"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                result = response.json()
                
                # Log concise response
                logger.info(f"[IN] Google Ads response: {response.status_code}")
                
                # Log full response
                google_conversions_logger.info("=" * 100)
                google_conversions_logger.info(f"[IN] INCOMING RESPONSE - {event_name} Event")
                google_conversions_logger.info(f"HTTP Status Code: {response.status_code}")
                google_conversions_logger.info(f"Response Body:")
                google_conversions_logger.info(json.dumps(result, indent=2))
                google_conversions_logger.info("=" * 100)
                google_conversions_logger.info("")
                
                if response.status_code != 200:
                    logger.error(f"Google Ads API returned status {response.status_code}: {result}")
                    return False
                    
                # Check partial failure
                if "partialFailureError" in result:
                    error = result["partialFailureError"]
                    logger.error(f"Google Ads Partial Failure: {error.get('message')}")
                    return False
                    
                # Check results
                results = result.get("results", [])
                if results:
                    logger.info(f"[SUCCESS] {event_name} event successfully sent to Google Ads")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error sending Google Ads event: {str(e)}", exc_info=True)
            return False

    async def track_conversion(
        self,
        event_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        value: Optional[float] = None,
        currency: str = "USD",
        order_id: Optional[str] = None,
    ) -> bool:
        """Generic method to track a conversion."""
        user_identifiers = self._get_user_identifiers(email, phone)
        
        return await self.send_event(
            event_name=event_name,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid,
            user_identifiers=user_identifiers,
            conversion_value=value,
            currency_code=currency,
            order_id=order_id
        )

    # Specific methods matching other services interfaces
    
    async def track_complete_registration(
        self,
        email: Optional[str] = None,
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        # Ignore other params not used by Google
        **kwargs
    ) -> bool:
        return await self.track_conversion(
            event_name="CompleteRegistration",
            email=email,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid
        )
        
    async def track_initiate_checkout(
        self,
        email: Optional[str] = None,
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        value: Optional[float] = None,
        currency: str = "USD",
        **kwargs
    ) -> bool:
        return await self.track_conversion(
            event_name="InitiateCheckout",
            email=email,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid,
            value=value,
            currency=currency
        )
        
    async def track_purchase(
        self,
        value: float,
        currency: str = "USD",
        email: Optional[str] = None,
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        order_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        return await self.track_conversion(
            event_name="Purchase",
            email=email,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid,
            value=value,
            currency=currency,
            order_id=order_id
        )
        
    async def track_add_to_cart(
        self,
        email: Optional[str] = None,
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        value: Optional[float] = None,
        currency: str = "USD",
        **kwargs
    ) -> bool:
        return await self.track_conversion(
            event_name="AddToCart",
            email=email,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid,
            value=value,
            currency=currency
        )
        
    async def track_view_content(
        self,
        email: Optional[str] = None,
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        **kwargs
    ) -> bool:
        return await self.track_conversion(
            event_name="ViewContent",
            email=email,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid
        )
        
    async def track_start_trial(
        self,
        value: float,
        currency: str = "USD",
        email: Optional[str] = None,
        gclid: Optional[str] = None,
        gbraid: Optional[str] = None,
        wbraid: Optional[str] = None,
        order_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        return await self.track_conversion(
            event_name="StartTrial",
            email=email,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid,
            value=value,
            currency=currency,
            order_id=order_id
        )

