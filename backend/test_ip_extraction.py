"""
Test script to verify IP extraction is working correctly.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import Request
from app.utils.request_helpers import get_client_ip


class MockClient:
    def __init__(self, host):
        self.host = host


class MockHeaders:
    def __init__(self, headers_dict):
        self._headers = headers_dict
    
    def get(self, key):
        return self._headers.get(key)


class MockRequest:
    def __init__(self, headers=None, client_host=None):
        self.headers = MockHeaders(headers or {})
        self.client = MockClient(client_host) if client_host else None


def test_ip_extraction():
    """Test various IP extraction scenarios."""
    
    print("Testing IP Extraction...")
    print("=" * 80)
    
    # Test 1: X-Forwarded-For header (Cloudflare scenario)
    print("\n1. Testing X-Forwarded-For header (Cloudflare/proxy):")
    request = MockRequest(headers={"X-Forwarded-For": "203.0.113.195, 198.51.100.1"}, client_host="172.16.0.1")
    ip = get_client_ip(request)
    print(f"   Headers: X-Forwarded-For = 203.0.113.195, 198.51.100.1")
    print(f"   Direct IP: 172.16.0.1 (proxy)")
    print(f"   ✅ Extracted IP: {ip}")
    assert ip == "203.0.113.195", f"Expected 203.0.113.195, got {ip}"
    
    # Test 2: X-Real-IP header
    print("\n2. Testing X-Real-IP header:")
    request = MockRequest(headers={"X-Real-IP": "198.51.100.25"}, client_host="172.16.0.1")
    ip = get_client_ip(request)
    print(f"   Headers: X-Real-IP = 198.51.100.25")
    print(f"   Direct IP: 172.16.0.1 (proxy)")
    print(f"   ✅ Extracted IP: {ip}")
    assert ip == "198.51.100.25", f"Expected 198.51.100.25, got {ip}"
    
    # Test 3: Direct connection (no proxy)
    print("\n3. Testing direct connection (no proxy headers):")
    request = MockRequest(headers={}, client_host="203.0.113.50")
    ip = get_client_ip(request)
    print(f"   Headers: (none)")
    print(f"   Direct IP: 203.0.113.50")
    print(f"   ✅ Extracted IP: {ip}")
    assert ip == "203.0.113.50", f"Expected 203.0.113.50, got {ip}"
    
    # Test 4: No request
    print("\n4. Testing with no request:")
    ip = get_client_ip(None)
    print(f"   Request: None")
    print(f"   ✅ Extracted IP: {ip}")
    assert ip is None, f"Expected None, got {ip}"
    
    # Test 5: Priority order (X-Forwarded-For takes precedence over X-Real-IP)
    print("\n5. Testing priority order (both headers present):")
    request = MockRequest(
        headers={"X-Forwarded-For": "203.0.113.100", "X-Real-IP": "198.51.100.200"},
        client_host="172.16.0.1"
    )
    ip = get_client_ip(request)
    print(f"   Headers: X-Forwarded-For = 203.0.113.100, X-Real-IP = 198.51.100.200")
    print(f"   Direct IP: 172.16.0.1")
    print(f"   ✅ Extracted IP: {ip} (X-Forwarded-For takes priority)")
    assert ip == "203.0.113.100", f"Expected 203.0.113.100, got {ip}"
    
    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("\nConclusion:")
    print("  - Real user IPs will be extracted from Cloudflare's X-Forwarded-For header")
    print("  - Facebook Conversions API will receive accurate user IPs")
    print("  - Better event matching, geo-targeting, and attribution!")


if __name__ == "__main__":
    test_ip_extraction()

