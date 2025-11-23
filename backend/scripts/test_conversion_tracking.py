#!/usr/bin/env python3
"""
Test script to simulate registrations and verify Facebook Conversions API tracking.

This script helps test:
1. CompleteRegistration event (manual email/password signup)
2. ViewContent event (page views)
3. InitiateCheckout event
4. Purchase event

Usage:
    python scripts/test_conversion_tracking.py --test complete-registration
    python scripts/test_conversion_tracking.py --test view-content --url /signup
    python scripts/test_conversion_tracking.py --test initiate-checkout
    python scripts/test_conversion_tracking.py --test purchase --value 29.99
"""

import asyncio
import httpx
import sys
import argparse
from datetime import datetime
import random
import string

# Backend URL
BACKEND_URL = "http://localhost:8000/api/v1"

def generate_test_email():
    """Generate a unique test email."""
    timestamp = int(datetime.now().timestamp())
    random_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"test_{timestamp}_{random_str}@test.ruxo.ai"

async def test_complete_registration():
    """Test CompleteRegistration event by creating a test user."""
    print("🧪 Testing CompleteRegistration event...")
    print("=" * 60)
    
    test_email = generate_test_email()
    test_password = "TestPassword123!"
    test_display_name = "Test User"
    
    print(f"📧 Test Email: {test_email}")
    print(f"👤 Display Name: {test_display_name}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Sign up
            print("1️⃣ Creating user account...")
            signup_response = await client.post(
                f"{BACKEND_URL}/auth/signup",
                json={
                    "email": test_email,
                    "password": test_password,
                    "display_name": test_display_name
                }
            )
            
            if signup_response.status_code == 200:
                data = signup_response.json()
                if data.get("token"):
                    print("✅ User created successfully!")
                    print(f"   Token: {data['token'][:50]}...")
                    print()
                    print("📊 Check backend logs for:")
                    print("   - 'Triggered CompleteRegistration event'")
                    print("   - 'Successfully sent CompleteRegistration event to Facebook'")
                    print()
                    print("💡 To view logs:")
                    print("   sudo journalctl -u ruxo-backend -f | grep -i 'complete\|registration'")
                    return True
                elif data.get("requires_verification"):
                    print("✅ User created (email verification required)")
                    print("   CompleteRegistration should still be tracked")
                    print()
                    print("📊 Check backend logs for CompleteRegistration event")
                    return True
            else:
                error = signup_response.text
                print(f"❌ Signup failed: {signup_response.status_code}")
                print(f"   Error: {error}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

async def test_view_content(url: str = "/signup"):
    """Test ViewContent event."""
    print(f"🧪 Testing ViewContent event for: {url}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"1️⃣ Sending ViewContent tracking request...")
            response = await client.post(
                f"{BACKEND_URL}/billing/track-view-content",
                params={"url": f"https://ruxo.ai{url}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    print("✅ ViewContent event tracked successfully!")
                    print()
                    print("📊 Check backend logs for:")
                    print("   - 'ViewContent tracking request'")
                    print("   - 'Triggered ViewContent event tracking'")
                    print("   - 'Successfully sent ViewContent event to Facebook'")
                    print()
                    print("💡 To view logs:")
                    print("   sudo journalctl -u ruxo-backend -f | grep -i viewcontent")
                    return True
                else:
                    print(f"❌ Tracking failed: {data}")
                    return False
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

async def test_initiate_checkout():
    """Test InitiateCheckout event."""
    print("🧪 Testing InitiateCheckout event...")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("1️⃣ Sending InitiateCheckout tracking request...")
            response = await client.post(
                f"{BACKEND_URL}/billing/track-initiate-checkout"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    print("✅ InitiateCheckout event tracked successfully!")
                    print()
                    print("📊 Check backend logs for:")
                    print("   - 'Successfully sent InitiateCheckout event to Facebook'")
                    print()
                    print("💡 To view logs:")
                    print("   sudo journalctl -u ruxo-backend -f | grep -i initiate")
                    return True
                else:
                    print(f"❌ Tracking failed: {data}")
                    return False
            else:
                print(f"❌ Request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

async def test_purchase(value: float = 29.99):
    """Test Purchase event (requires authentication)."""
    print(f"🧪 Testing Purchase event (value: ${value})...")
    print("=" * 60)
    print("⚠️  Note: Purchase event requires authentication")
    print("   This test requires a valid JWT token")
    print()
    
    token = input("Enter JWT token (or press Enter to skip): ").strip()
    if not token:
        print("⏭️  Skipping Purchase test (no token provided)")
        return False
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("1️⃣ Sending Purchase tracking request...")
            response = await client.post(
                f"{BACKEND_URL}/billing/test-purchase",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    print("✅ Purchase event tracked successfully!")
                    print(f"   Value: ${data.get('value', value)}")
                    print(f"   Event ID: {data.get('event_id', 'N/A')}")
                    print()
                    print("📊 Check backend logs for:")
                    print("   - 'Successfully sent Purchase event to Facebook'")
                    return True
                else:
                    print(f"❌ Tracking failed: {data}")
                    return False
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

async def main():
    parser = argparse.ArgumentParser(description="Test Facebook Conversions API tracking")
    parser.add_argument(
        "--test",
        choices=["complete-registration", "view-content", "initiate-checkout", "purchase", "all"],
        required=True,
        help="Which test to run"
    )
    parser.add_argument("--url", default="/signup", help="URL for ViewContent test")
    parser.add_argument("--value", type=float, default=29.99, help="Purchase value for Purchase test")
    
    args = parser.parse_args()
    
    print()
    print("🚀 Facebook Conversions API Tracking Test")
    print("=" * 60)
    print()
    
    if args.test == "complete-registration" or args.test == "all":
        await test_complete_registration()
        print()
    
    if args.test == "view-content" or args.test == "all":
        await test_view_content(args.url)
        print()
    
    if args.test == "initiate-checkout" or args.test == "all":
        await test_initiate_checkout()
        print()
    
    if args.test == "purchase" or args.test == "all":
        await test_purchase(args.value)
        print()
    
    print("=" * 60)
    print("✅ Testing complete!")
    print()
    print("📋 Next steps:")
    print("   1. Check backend logs for tracking events")
    print("   2. Verify events in Facebook Events Manager")
    print("   3. Check for any errors in logs")

if __name__ == "__main__":
    asyncio.run(main())

