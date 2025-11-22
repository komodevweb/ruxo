import hashlib
import hmac
import secrets
import base64
from typing import Optional
from app.core.config import settings

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"ruxo_{secrets.token_urlsafe(32)}"

def hash_api_key(api_key: str) -> str:
    """Hash an API key using HMAC-SHA256."""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        api_key.encode(),
        hashlib.sha256
    ).hexdigest()

def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash."""
    computed_hash = hash_api_key(api_key)
    return hmac.compare_digest(computed_hash, stored_hash)

def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data (simplified - use proper encryption in production)."""
    # In production, use cryptography library with Fernet or AES
    # This is a placeholder
    key = base64.b64decode(settings.API_KEY_ENCRYPTION_KEY)
    # TODO: Implement proper encryption
    return data

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    # TODO: Implement proper decryption
    return encrypted_data

