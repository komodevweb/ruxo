#!/usr/bin/env python3
"""
Configure Azure OAuth provider in Supabase using Management API.

This script uses the Supabase Management API to programmatically configure
Azure OAuth provider. Alternative to manual configuration via Supabase Dashboard.

Usage:
    python scripts/configure_azure_oauth.py

Requirements:
    - SUPABASE_ACCESS_TOKEN in .env (get from https://supabase.com/dashboard/account/tokens)
    - SUPABASE_PROJECT_REF in .env (your project reference)
    - AZURE_CLIENT_ID in .env (from Azure Portal)
    - AZURE_CLIENT_SECRET in .env (from Azure Portal)
    - Optional: AZURE_TENANT_URL in .env (for specific tenant configurations)

Reference: https://supabase.com/docs/guides/auth/social-login/auth-azure
"""

import os
import sys
import json
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install it with: pip install httpx")
    sys.exit(1)

def load_env():
    """Load environment variables from .env file."""
    env_file = backend_dir / ".env"
    if not env_file.exists():
        print(f"ERROR: .env file not found at {env_file}")
        print("Please create .env file from env.example and fill in the values.")
        sys.exit(1)
    
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value
    
    return env_vars

def configure_azure_oauth():
    """Configure Azure OAuth provider via Supabase Management API."""
    print("=" * 80)
    print("Supabase Azure OAuth Configuration via Management API")
    print("=" * 80)
    print()
    
    # Load environment variables
    env = load_env()
    
    # Required variables
    access_token = env.get("SUPABASE_ACCESS_TOKEN")
    project_ref = env.get("SUPABASE_PROJECT_REF")
    azure_client_id = env.get("AZURE_CLIENT_ID")
    azure_client_secret = env.get("AZURE_CLIENT_SECRET")
    azure_tenant_url = env.get("AZURE_TENANT_URL", "").strip()
    
    # Validate required variables
    missing = []
    if not access_token:
        missing.append("SUPABASE_ACCESS_TOKEN")
    if not project_ref:
        missing.append("SUPABASE_PROJECT_REF")
    if not azure_client_id:
        missing.append("AZURE_CLIENT_ID")
    if not azure_client_secret:
        missing.append("AZURE_CLIENT_SECRET")
    
    if missing:
        print("ERROR: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print()
        print("Please add these to your .env file:")
        print("  - SUPABASE_ACCESS_TOKEN: Get from https://supabase.com/dashboard/account/tokens")
        print("  - SUPABASE_PROJECT_REF: Your project reference (e.g., 'cutgibszjdnxsrlclbos')")
        print("  - AZURE_CLIENT_ID: From Azure Portal > App Registration > Application (client) ID")
        print("  - AZURE_CLIENT_SECRET: From Azure Portal > Certificates & secrets > Value")
        sys.exit(1)
    
    # Prepare request payload
    payload = {
        "external_azure_enabled": True,
        "external_azure_client_id": azure_client_id,
        "external_azure_secret": azure_client_secret,
    }
    
    # Add tenant URL if provided
    if azure_tenant_url:
        payload["external_azure_url"] = azure_tenant_url
        print(f"Using Azure Tenant URL: {azure_tenant_url}")
    else:
        print("Using default Azure Tenant URL: https://login.microsoftonline.com/common")
    
    print()
    print(f"Project Reference: {project_ref}")
    print(f"Azure Client ID: {azure_client_id[:20]}... (truncated)")
    print()
    print("Configuring Azure OAuth provider...")
    
    # Make API request
    url = f"https://api.supabase.com/v1/projects/{project_ref}/config/auth"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.patch(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                print("=" * 80)
                print("✅ SUCCESS: Azure OAuth provider configured successfully!")
                print("=" * 80)
                print()
                print("Next steps:")
                print("1. Verify configuration in Supabase Dashboard:")
                print("   - Go to Authentication > Providers > Azure")
                print("   - Ensure Azure provider is enabled")
                print()
                print("2. Verify Azure redirect URI:")
                print(f"   - Go to Azure Portal > App Registration > Authentication")
                print(f"   - Ensure redirect URI is: https://{project_ref}.supabase.co/auth/v1/callback")
                print()
                return 0
            else:
                print("=" * 80)
                print(f"❌ ERROR: Configuration failed (Status: {response.status_code})")
                print("=" * 80)
                print()
                print("Response:")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(response.text)
                print()
                print("Troubleshooting:")
                print("1. Verify SUPABASE_ACCESS_TOKEN is valid")
                print("2. Verify SUPABASE_PROJECT_REF is correct")
                print("3. Verify AZURE_CLIENT_ID and AZURE_CLIENT_SECRET are correct")
                print("4. Check Supabase Management API documentation")
                return 1
                
    except httpx.RequestError as e:
        print("=" * 80)
        print(f"❌ ERROR: Network error - {str(e)}")
        print("=" * 80)
        return 1
    except Exception as e:
        print("=" * 80)
        print(f"❌ ERROR: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(configure_azure_oauth())

