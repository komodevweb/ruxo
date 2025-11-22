#!/usr/bin/env python3
"""
Generate secure keys for Ruxo backend environment variables.

Usage:
    python scripts/generate_secrets.py
"""

import secrets
import base64
import sys

def generate_secret_key() -> str:
    """Generate a 32-byte hex secret key."""
    return secrets.token_hex(32)

def generate_encryption_key() -> str:
    """Generate a base64-encoded 32-byte encryption key."""
    key_bytes = secrets.token_bytes(32)
    return base64.b64encode(key_bytes).decode('utf-8')

def main():
    print("=" * 60)
    print("Ruxo Backend - Secret Key Generator")
    print("=" * 60)
    print()
    
    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()
    session_secret = generate_secret_key()
    
    print("Generated secure keys:")
    print()
    print(f"SECRET_KEY={secret_key}")
    print()
    print(f"API_KEY_ENCRYPTION_KEY={encryption_key}")
    print()
    print(f"SESSION_SECRET={session_secret}")
    print()
    print("=" * 60)
    print()
    print("Copy these values to your .env file.")
    print("WARNING: Keep these keys secure and never commit them to version control!")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

