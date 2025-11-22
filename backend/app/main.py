from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.routers import auth, billing, credits, renders, webhooks, admin, storage, wan_animate, text_to_video, image_to_video, image
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.scheduler_service import lifespan
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,  # Add lifespan context manager for scheduler
)

# Security Headers Middleware (applied first)
if settings.SECURITY_HEADERS_ENABLED:
    app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting Middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=settings.CORS_MAX_AGE,
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions globally."""
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error" if settings.ENVIRONMENT != "development" else str(exc)}
    )

# Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(billing.router, prefix=f"{settings.API_V1_STR}/billing", tags=["billing"])
app.include_router(credits.router, prefix=f"{settings.API_V1_STR}/credits", tags=["credits"])
app.include_router(renders.router, prefix=f"{settings.API_V1_STR}/renders", tags=["renders"])
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["webhooks"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(storage.router, prefix=f"{settings.API_V1_STR}/storage", tags=["storage"])
app.include_router(wan_animate.router, prefix=f"{settings.API_V1_STR}/wan-animate", tags=["wan-animate"])
app.include_router(text_to_video.router, prefix=f"{settings.API_V1_STR}/text-to-video", tags=["text-to-video"])
app.include_router(image_to_video.router, prefix=f"{settings.API_V1_STR}/image-to-video", tags=["image-to-video"])
app.include_router(image.router, prefix=f"{settings.API_V1_STR}/image", tags=["image"])

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": settings.VERSION}

@app.get("/", tags=["root"])
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT != "production" else None
    }
