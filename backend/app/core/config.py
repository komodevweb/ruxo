from typing import List, Union, Optional, ClassVar
from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ruxo API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: PostgresDsn
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str  # Optional: Only needed if using Supabase client library
    SUPABASE_JWT_SECRET: str  # Required: For JWT verification (from Supabase Settings > API > JWT Secret)
    SUPABASE_ACCESS_TOKEN: Optional[str] = None  # Optional: For Management API (programmatic OAuth configuration)
    SUPABASE_PROJECT_REF: Optional[str] = None  # Optional: Project reference (extracted from SUPABASE_URL)
    
    # Azure OAuth (for Management API configuration - optional)
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    AZURE_TENANT_URL: Optional[str] = None  # Optional tenant URL (defaults to common)
    
    # Stripe
    STRIPE_API_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    # Backblaze B2 Storage (optional - app will work without B2, but storage features will be disabled)
    B2_APPLICATION_KEY_ID: Optional[str] = None
    B2_APPLICATION_KEY: Optional[str] = None
    B2_BUCKET_NAME: Optional[str] = None
    B2_BUCKET_ID: Optional[str] = None  # Optional, will be fetched if not provided

    # WaveSpeed AI
    WAVESPEED_API_KEY: Optional[str] = None
    WAVESPEED_API_URL: str = "https://api.wavespeed.ai/api/v3"

    # Frontend
    FRONTEND_URL: str
    BACKEND_BASE_URL: str

    # Security - API Keys & Encryption
    SECRET_KEY: str  # For API key hashing, session tokens, etc. (generate with: openssl rand -hex 32)
    API_KEY_ENCRYPTION_KEY: str  # For encrypting API keys at rest (32 bytes base64)
    
    # Security - Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Security - Admin
    ADMIN_EMAILS: str = ""  # Comma-separated list of admin emails
    SUPER_ADMIN_EMAIL: str = ""  # Primary admin email
    
    # Security - API Security Headers
    SECURITY_HEADERS_ENABLED: bool = True
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"  # Comma-separated
    
    # Security - Logging & Monitoring
    SENTRY_DSN: Optional[str] = None  # For error tracking
    LOG_LEVEL: str = "INFO"
    ENABLE_AUDIT_LOGGING: bool = True
    
    # Security - Webhook Security
    WEBHOOK_TIMESTAMP_TOLERANCE: int = 300  # 5 minutes in seconds
    
    # Security - Password/Token Policies (for future use)
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_PASSWORD_COMPLEXITY: bool = False
    
    # Security - CORS Advanced
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 3600

    # Redis Configuration
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True
    REDIS_CACHE_TTL: int = 3600  # Default cache TTL in seconds (1 hour)
    
    # Facebook Conversions API
    FACEBOOK_PIXEL_ID: Optional[str] = None  # Facebook Pixel ID (e.g., "860080813089481")
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None  # Facebook Conversions API Access Token
    
    # TikTok Conversions API
    TIKTOK_PIXEL_ID: Optional[str] = None  # TikTok Pixel ID (e.g., "D4JVLBBC77U4IAHDMKB0")
    TIKTOK_ACCESS_TOKEN: Optional[str] = None  # TikTok Events API Access Token

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
