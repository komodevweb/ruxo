"""
Image To Video API endpoints for WaveSpeed AI integration.
Handles image-to-video job submission using Wan 2.5.
"""
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.services.storage_service import get_storage_service
from app.services.wavespeed_service import WaveSpeedService
from app.services.credits_service import CreditsService
from app.services.model_config import get_model_config, MODEL_CONFIGS
from app.models.render import RenderJob
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

# Image-to-video model configurations
IMAGE_TO_VIDEO_MODELS = {
    "wan-2.5": {
        "id": "wan-2.5",
        "name": "Wan 2.5 Image To Video",
        "display_name": "Wan 2.5 Image To Video",
        "description": "High-quality image-to-video with audio sync",
        "icon": "/images/logos/wan-logo.svg",
        "supported_resolutions": ["480p", "720p", "1080p"],
        "supported_durations": [3, 4, 5, 6, 7, 8, 9, 10],
        "supports_audio": True,
        "supports_negative_prompt": True,
        "supports_prompt_expansion": True,
        "default_resolution": "720p",
        "default_duration": 5,
        "uses_aspect_ratio": False,
    },
    "google-veo-3-fast": {
        "id": "google-veo-3-fast",
        "name": "Google Veo 3 Fast Image To Video",
        "display_name": "Google Veo 3 Fast I2V",
        "description": "High-speed cinematic image-to-video with native audio",
        "icon": "/images/logos/icons8-google-logo-48.svg",
        "supported_resolutions": ["720p", "1080p"],
        "supported_durations": [4, 6, 8],
        "supports_audio": False,  # Native audio generation, not upload
        "supports_negative_prompt": True,
        "supports_prompt_expansion": False,
        "default_resolution": "720p",
        "default_duration": 8,
        "uses_aspect_ratio": True,
        "supported_aspect_ratios": ["16:9", "9:16"],
        "default_aspect_ratio": "16:9",
        "credit_by_duration": {4: 32, 6: 50, 8: 64},  # Same price for 720p and 1080p: 4s=32, 6s=50, 8s=64 credits
    },
    "google-veo-3.1-fast": {
        "id": "google-veo-3.1-fast",
        "name": "Google Veo 3.1 Fast Image To Video",
        "display_name": "Google Veo 3.1 Fast I2V",
        "description": "Advanced high-speed image-to-video with dialogue & lip-sync",
        "icon": "/images/logos/icons8-google-logo-48.svg",
        "supported_resolutions": ["720p", "1080p"],
        "supported_durations": [4, 6, 8],
        "supports_audio": False,  # Native audio generation, not upload
        "supports_negative_prompt": True,
        "supports_prompt_expansion": False,
        "default_resolution": "720p",
        "default_duration": 8,
        "uses_aspect_ratio": True,
        "supported_aspect_ratios": ["16:9", "9:16"],
        "default_aspect_ratio": "16:9",
        "credit_by_duration": {4: 32, 6: 50, 8: 64},  # Same price for 720p and 1080p: 4s=32, 6s=50, 8s=64 credits
    },
    "openai-sora-2": {
        "id": "openai-sora-2",
        "name": "OpenAI Sora 2 Image To Video",
        "display_name": "OpenAI Sora 2 I2V",
        "description": "Realistic image-to-video with synchronized audio and improved physics",
        "icon": "/images/logos/sora-color.svg",
        "supported_resolutions": ["1080p"],  # Sora 2 outputs 1080p
        "supported_durations": [4, 8, 12],
        "supports_audio": False,  # Native audio generation, not upload
        "supports_negative_prompt": False,
        "supports_prompt_expansion": False,
        "default_resolution": "1080p",
        "default_duration": 4,
        "uses_aspect_ratio": False,
        "credit_by_duration": {4: 8, 8: 16, 12: 22},  # 4s=8, 8s=16, 12s=22 credits
    },
    "openai-sora-2-pro": {
        "id": "openai-sora-2-pro",
        "name": "OpenAI Sora 2 Image To Video Pro",
        "display_name": "OpenAI Sora 2 I2V Pro",
        "description": "Premium image-to-video with greater steerability and resolution options",
        "icon": "/images/logos/sora-color.svg",
        "supported_resolutions": ["720p", "1080p"],
        "supported_durations": [4, 8, 12],
        "supports_audio": False,  # Native audio generation, not upload
        "supports_negative_prompt": False,
        "supports_prompt_expansion": False,
        "default_resolution": "720p",
        "default_duration": 4,
        "uses_aspect_ratio": False,
        "credit_by_resolution": {
            "720p": {4: 22, 8: 44, 12: 66},  # 720p: 4s=22, 8s=44, 12s=66 credits
            "1080p": {4: 40, 8: 80, 12: 120}  # 1080p: 4s=40, 8s=80, 12s=120 credits
        },
    },
    "kling-v2.5-turbo-pro": {
        "id": "kling-v2.5-turbo-pro",
        "name": "Kling V2.5 Turbo Pro Image To Video",
        "display_name": "Kling V2.5 Turbo Pro I2V",
        "description": "High-quality image-to-video with first-last frame animation",
        "icon": "/images/logos/kling-color.svg",
        "supported_resolutions": ["1080p"],  # Kling outputs 1080p
        "supported_durations": [5, 10],
        "supports_audio": False,
        "supports_negative_prompt": True,
        "supports_prompt_expansion": False,
        "default_resolution": "1080p",
        "default_duration": 5,
        "uses_aspect_ratio": False,
        "credit_by_duration": {5: 7, 10: 20},  # Non-linear pricing: 7 credits for 5s, 20 credits for 10s
        "supports_guidance_scale": True,
        "supports_last_image": True,  # Optional end frame
    },
    "hailuo-2.3-i2v-standard": {
        "id": "hailuo-2.3-i2v-standard",
        "name": "Minimax Hailuo 2.3 I2V Standard",
        "display_name": "Hailuo 2.3 I2V Standard",
        "description": "Cinematic image-to-video with physics-aware animation",
        "icon": "/images/logos/hailuo.svg",
        "supported_resolutions": ["768p"],  # Hailuo outputs 768p
        "supported_durations": [6, 10],  # 6s and 10s only
        "supports_audio": False,
        "supports_negative_prompt": False,
        "supports_prompt_expansion": True,
        "default_resolution": "768p",
        "default_duration": 6,
        "uses_aspect_ratio": False,
        "credit_cost": 6,  # Base price for display (6s duration)
        "credit_by_duration": {6: 6, 10: 12},  # 6s = 6 credits, 10s = 12 credits
    },
    "hailuo-2.3-i2v-pro": {
        "id": "hailuo-2.3-i2v-pro",
        "name": "Minimax Hailuo 2.3 I2V Pro",
        "display_name": "Hailuo 2.3 I2V Pro",
        "description": "Professional cinematic image-to-video with native 1080p output",
        "icon": "/images/logos/hailuo.svg",
        "supported_resolutions": ["1080p"],  # Fixed 1080p output
        "supported_durations": [5],  # Fixed 5 seconds
        "supports_audio": False,
        "supports_negative_prompt": False,
        "supports_prompt_expansion": True,
        "default_resolution": "1080p",
        "default_duration": 5,
        "uses_aspect_ratio": False,
        "credit_cost": 12,  # 12 credits for 5 seconds (fixed price per job)
    }
}


class ImageToVideoRequest(BaseModel):
    prompt: str
    image_url: str
    model: str = "wan-2.5"
    resolution: str = "720p"  # 480p, 720p, 1080p
    duration: int = 5  # 3-10
    negative_prompt: Optional[str] = None
    audio_url: Optional[str] = None
    enable_prompt_expansion: bool = False
    seed: int = -1
    aspect_ratio: Optional[str] = None  # For Veo models: 16:9, 9:16
    generate_audio: Optional[bool] = None  # For Veo models: whether to generate audio
    last_image_url: Optional[str] = None  # For Kling: optional end frame
    guidance_scale: Optional[float] = None  # For Kling: 0.0-1.0


class ImageToVideoResponse(BaseModel):
    job_id: str
    status: str
    task_id: str
    message: str


def calculate_credit_cost(model_id: str, resolution: str, duration: int, generate_audio: bool = False) -> int:
    """
    Calculate credit cost for a given model, resolution, and duration.
    Returns the estimated credit cost.
    """
    model_config = IMAGE_TO_VIDEO_MODELS.get(model_id)
    if not model_config:
        return 0
    
    model = model_id
    
    if model == "google-veo-3-fast" or model == "google-veo-3.1-fast":
        # Veo 3 Fast and Veo 3.1 Fast: duration-based pricing (same for 720p and 1080p)
        # Pricing: 4s=32, 6s=50, 8s=64 credits
        credit_by_duration = model_config.get("credit_by_duration", {4: 32, 6: 50, 8: 64})
        return credit_by_duration.get(duration, 32)  # Default to 32 if duration not found
    elif model == "openai-sora-2":
        # Sora 2: non-linear pricing
        # Pricing: 4s=8, 8s=16, 12s=22 credits
        credit_by_duration = model_config.get("credit_by_duration", {4: 8, 8: 16, 12: 22})
        return credit_by_duration.get(duration, 8)  # Default to 8 if duration not found
    elif model == "openai-sora-2-pro":
        # Sora 2 Pro: non-linear pricing based on resolution and duration
        credit_by_resolution = model_config.get("credit_by_resolution", {
            "720p": {4: 22, 8: 44, 12: 66},
            "1080p": {4: 40, 8: 80, 12: 120}
        })
        resolution_pricing = credit_by_resolution.get(resolution, {})
        return resolution_pricing.get(duration, 22)  # Default to 22 if not found
    elif model == "kling-v2.5-turbo-pro":
        # Kling V2.5 Turbo Pro: non-linear pricing
        credit_by_duration = model_config.get("credit_by_duration", {5: 7, 10: 20})
        return credit_by_duration.get(duration, 7)
    elif model == "hailuo-2.3-i2v-standard":
        # Hailuo 2.3 I2V Standard: non-linear pricing
        # Pricing: 6s = 6 credits, 10s = 12 credits
        credit_by_duration = model_config.get("credit_by_duration", {6: 6, 10: 12})
        return credit_by_duration.get(duration, 6)  # Default to 6 if duration not found
    elif model == "hailuo-2.3-i2v-pro":
        # Hailuo 2.3 I2V Pro: fixed pricing
        return int(model_config.get("credit_cost", 12))
    else:
        # Wan 2.5: complex pricing based on base (1080p 10s = 32 credits)
        # Base: 1080p 10s = 32 credits
        # Each second reduction: multiply by 0.9 (10% reduction)
        # Resolution reduction: 720p = 0.8 of 1080p, 480p = 0.64 of 1080p (20% reduction each step)
        base_credit = 32
        resolution_multiplier = {
            "1080p": 1.0,
            "720p": 0.8,   # 20% reduction from 1080p
            "480p": 0.64   # 20% reduction from 720p (0.8 * 0.8 = 0.64)
        }
        # Duration multiplier: 0.9^(10 - duration)
        # For 10s: 0.9^0 = 1.0
        # For 9s: 0.9^1 = 0.9
        # For 8s: 0.9^2 = 0.81
        # etc.
        duration_multiplier = 0.9 ** (10 - duration)
        res_mult = resolution_multiplier.get(resolution, 1.0)
        return int(round(base_credit * res_mult * duration_multiplier))


@router.get("/models")
async def get_available_models():
    """
    Get all available image-to-video models with their configurations (cached in Redis).
    """
    from app.utils.cache import get_cached, set_cached, cache_key
    
    cache_key_str = cache_key("cache", "image-to-video", "models")
    
    # Try cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return cached
    
    # Cache miss - build models list
    models = list(IMAGE_TO_VIDEO_MODELS.values())
    result = {"models": models}
    
    # Cache for 24 hours (models rarely change)
    await set_cached(cache_key_str, result, ttl=86400)
    
    return result


@router.get("/calculate-credits")
async def calculate_credits(
    model_id: str,
    resolution: str,
    duration: int,
    generate_audio: bool = False
):
    """
    Calculate credit cost for a given model, resolution, and duration.
    """
    credits = calculate_credit_cost(model_id, resolution, duration, generate_audio)
    return {"credits": credits}


@router.post("/submit", response_model=ImageToVideoResponse)
async def submit_image_to_video(
    request: Request,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submit an Image To Video job using Wan 2.5.
    
    Accepts JSON body with image_url and other parameters.
    Image must be uploaded to storage first and provided as URL.
    """
    try:
        body = await request.json()
        prompt = body.get("prompt")
        image_url = body.get("image_url")
        model = body.get("model", "wan-2.5")
        resolution = body.get("resolution", "720p")
        duration = int(body.get("duration", 5))
        negative_prompt = body.get("negative_prompt")
        audio_url = body.get("audio_url")
        enable_prompt_expansion = body.get("enable_prompt_expansion", False)
        seed = int(body.get("seed", -1))
        aspect_ratio = body.get("aspect_ratio")
        generate_audio = body.get("generate_audio")
        last_image_url = body.get("last_image_url")
        guidance_scale = body.get("guidance_scale")
        
        logger.info("Received Image To Video JSON request")
    except Exception as e:
        logger.warning(f"Failed to parse JSON body: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON body: {str(e)}"
        )
    
    # Validate required fields
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt is required"
        )
    
    if not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_url is required"
        )
    
    # Get model (default to wan-2.5 if not specified)
    if model not in IMAGE_TO_VIDEO_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model. Available models: {', '.join(IMAGE_TO_VIDEO_MODELS.keys())}"
        )
    
    model_config = IMAGE_TO_VIDEO_MODELS[model]
    
    # Validate resolution (skip for models that have fixed output resolution)
    if model not in ["openai-sora-2", "kling-v2.5-turbo-pro", "hailuo-2.3-i2v-standard", "hailuo-2.3-i2v-pro"]:
        if resolution not in model_config["supported_resolutions"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resolution {resolution} not supported by {model_config['display_name']}. Supported: {', '.join(model_config['supported_resolutions'])}"
            )
    
    # Validate duration (skip validation for models with fixed duration - they're handled in model config)
    if duration not in model_config["supported_durations"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duration {duration}s not supported by {model_config['display_name']}. Supported: {', '.join(map(str, model_config['supported_durations']))}s"
        )
    
    # Validate aspect_ratio for Veo models
    if model_config.get("uses_aspect_ratio"):
        if not aspect_ratio:
            aspect_ratio = model_config.get("default_aspect_ratio", "16:9")
        if aspect_ratio not in model_config.get("supported_aspect_ratios", []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Aspect ratio {aspect_ratio} not supported by {model_config['display_name']}. Supported: {', '.join(model_config.get('supported_aspect_ratios', []))}"
            )
    
    # Set default generate_audio for Veo models
    if model_config.get("uses_aspect_ratio") and generate_audio is None:
        generate_audio = True  # Default to generating audio for Veo models
    
    # Set default guidance_scale for Kling models
    if model == "kling-v2.5-turbo-pro" and guidance_scale is None:
        guidance_scale = 0.5  # Default guidance scale for Kling
    
    # Validate guidance_scale for Kling
    if model == "kling-v2.5-turbo-pro" and guidance_scale is not None:
        if guidance_scale < 0.0 or guidance_scale > 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Guidance scale must be between 0.0 and 1.0 for {model_config['display_name']}"
            )
    
    logger.info(f"Image To Video submission request from user {current_user.id}")
    logger.info(f"Model: {model}, Parameters: resolution={resolution}, duration={duration}, seed={seed}")
    if model_config.get("uses_aspect_ratio"):
        logger.info(f"Aspect ratio: {aspect_ratio}, Generate audio: {generate_audio}")
    logger.info(f"Image URL: {image_url}")
    if audio_url:
        logger.info(f"Audio URL: {audio_url}")
    
    # Duplicate job detection removed - allowing all job submissions
    
    try:
        # Initialize services
        wavespeed_service = WaveSpeedService()
        credits_service = CreditsService(session)
        
        # Check if WaveSpeed is configured
        if not wavespeed_service.api_key:
            logger.error("WaveSpeed API key not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WaveSpeed AI service is not configured. Please check WAVESPEED_API_KEY."
            )
        
        # Calculate credit cost based on model
        if model == "google-veo-3-fast" or model == "google-veo-3.1-fast":
            # Veo 3 Fast and Veo 3.1 Fast: duration-based pricing (same for 720p and 1080p)
            # Pricing: 4s=32, 6s=50, 8s=64 credits
            credit_by_duration = model_config.get("credit_by_duration", {4: 32, 6: 50, 8: 64})
            estimated_credit_cost = credit_by_duration.get(duration, 32)  # Default to 32 if duration not found
        elif model_config.get("uses_aspect_ratio"):
            # Other Veo models: fixed pricing (fallback)
            if generate_audio:
                estimated_credit_cost = model_config.get("credit_cost_with_audio", 12)
            else:
                estimated_credit_cost = model_config.get("credit_cost_without_audio", 8)
        elif model == "openai-sora-2":
            # Sora 2: non-linear pricing
            # Pricing: 4s=8, 8s=16, 12s=22 credits
            credit_by_duration = model_config.get("credit_by_duration", {4: 8, 8: 16, 12: 22})
            estimated_credit_cost = credit_by_duration.get(duration, 8)  # Default to 8 if duration not found
        elif model == "openai-sora-2-pro":
            # Sora 2 Pro: non-linear pricing based on resolution and duration
            # Pricing: 720p: 4s=22, 8s=44, 12s=66 | 1080p: 4s=40, 8s=80, 12s=120
            credit_by_resolution = model_config.get("credit_by_resolution", {
                "720p": {4: 22, 8: 44, 12: 66},
                "1080p": {4: 40, 8: 80, 12: 120}
            })
            resolution_pricing = credit_by_resolution.get(resolution, {})
            estimated_credit_cost = resolution_pricing.get(duration, 22)  # Default to 22 if not found
        elif model == "kling-v2.5-turbo-pro":
            # Kling V2.5 Turbo Pro: non-linear pricing
            # Pricing: 7 credits for 5s, 20 credits for 10s
            credit_by_duration = model_config.get("credit_by_duration", {5: 7, 10: 20})
            estimated_credit_cost = credit_by_duration.get(duration, 7)  # Default to 7 if duration not found
        elif model == "hailuo-2.3-i2v-standard":
            # Hailuo 2.3 I2V Standard: non-linear pricing
            # Pricing: 6s = 6 credits, 10s = 12 credits
            credit_by_duration = model_config.get("credit_by_duration", {6: 6, 10: 12})
            estimated_credit_cost = credit_by_duration.get(duration, 6)  # Default to 6 if duration not found
        elif model == "hailuo-2.3-i2v-pro":
            # Hailuo 2.3 I2V Pro: fixed pricing
            # Pricing: 12 credits per job (fixed 5s, 1080p)
            estimated_credit_cost = int(model_config.get("credit_cost", 12))  # Round to nearest credit
        else:
            # Wan 2.5: complex pricing based on base (1080p 10s = 32 credits)
            # Base: 1080p 10s = 32 credits
            # Each second reduction: multiply by 0.9 (10% reduction)
            # Resolution reduction: 720p = 0.8 of 1080p, 480p = 0.64 of 1080p (20% reduction each step)
            base_credit = 32
            resolution_multiplier = {
                "1080p": 1.0,
                "720p": 0.8,   # 20% reduction from 1080p
                "480p": 0.64   # 20% reduction from 720p (0.8 * 0.8 = 0.64)
            }
            # Duration multiplier: 0.9^(10 - duration)
            duration_multiplier = 0.9 ** (10 - duration)
            res_mult = resolution_multiplier.get(resolution, 1.0)
            estimated_credit_cost = int(round(base_credit * res_mult * duration_multiplier))
        logger.info(f"Credit cost for {model_config['display_name']} {duration}s: {estimated_credit_cost} credits")
        
        # Check user credits
        wallet = await credits_service.get_wallet(current_user.id)
        if wallet.balance_credits < estimated_credit_cost:
            logger.warning(f"Insufficient credits: user has {wallet.balance_credits}, needs {estimated_credit_cost}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {estimated_credit_cost}, Available: {wallet.balance_credits}"
            )
        
        # Submit job to WaveSpeed AI based on model
        logger.info(f"Submitting job to WaveSpeed AI {model_config['display_name']}...")
        if model == "wan-2.5":
            wavespeed_response = await wavespeed_service.submit_wan_2_5_image_to_video(
                image_url=image_url,
                prompt=prompt,
                resolution=resolution,
                duration=duration,
                negative_prompt=negative_prompt,
                audio_url=audio_url,
                enable_prompt_expansion=enable_prompt_expansion,
                seed=seed
            )
        elif model == "google-veo-3-fast":
            wavespeed_response = await wavespeed_service.submit_google_veo_3_fast_image_to_video(
                image_url=image_url,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                duration=duration,
                resolution=resolution,
                generate_audio=generate_audio,
                negative_prompt=negative_prompt,
                seed=seed
            )
        elif model == "google-veo-3.1-fast":
            wavespeed_response = await wavespeed_service.submit_google_veo_3_1_fast_image_to_video(
                image_url=image_url,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                duration=duration,
                resolution=resolution,
                generate_audio=generate_audio,
                negative_prompt=negative_prompt,
                seed=seed
            )
        elif model == "openai-sora-2":
            wavespeed_response = await wavespeed_service.submit_openai_sora_2_image_to_video(
                image_url=image_url,
                prompt=prompt,
                duration=duration
            )
        elif model == "openai-sora-2-pro":
            wavespeed_response = await wavespeed_service.submit_openai_sora_2_pro_image_to_video(
                image_url=image_url,
                prompt=prompt,
                resolution=resolution,
                duration=duration
            )
        elif model == "kling-v2.5-turbo-pro":
            wavespeed_response = await wavespeed_service.submit_kling_v2_5_turbo_pro_image_to_video(
                image_url=image_url,
                prompt=prompt,
                duration=duration,
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale,
                last_image_url=last_image_url
            )
        elif model == "hailuo-2.3-i2v-standard":
            wavespeed_response = await wavespeed_service.submit_hailuo_2_3_i2v_standard_image_to_video(
                image_url=image_url,
                prompt=prompt,
                duration=duration,
                enable_prompt_expansion=enable_prompt_expansion
            )
        elif model == "hailuo-2.3-i2v-pro":
            # Hailuo 2.3 I2V Pro: fixed 5s, 1080p, only image, prompt (optional), and enable_prompt_expansion
            wavespeed_response = await wavespeed_service.submit_hailuo_2_3_i2v_pro_image_to_video(
                image_url=image_url,
                prompt=prompt if prompt else None,
                enable_prompt_expansion=enable_prompt_expansion if model_config.get("supports_prompt_expansion") else True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model {model} not yet implemented"
            )
        
        # Extract task ID from response
        task_id = wavespeed_response.get("data", {}).get("id")
        if not task_id:
            logger.error(f"WaveSpeed response missing task ID: {wavespeed_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="WaveSpeed API did not return a task ID"
            )
        
        logger.info(f"WaveSpeed job submitted successfully: task_id={task_id}")
        
        # Create render job record
        job_id = str(uuid.uuid4())
        render_job = RenderJob(
            id=job_id,
            user_id=current_user.id,
            job_type="video",
            provider=f"{model}-image-to-video",
            input_prompt=prompt,
            status="pending",
            estimated_credit_cost=estimated_credit_cost,
            actual_credit_cost=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            settings={
                "model": model,
                "model_display_name": model_config["display_name"],
                "image_url": image_url,
                "duration": duration,
                "wavespeed_task_id": task_id
            }
        )
        
        # Add model-specific settings
        if model == "openai-sora-2":
            # Sora 2: no resolution, negative_prompt, etc.
            pass
        elif model == "openai-sora-2-pro":
            # Sora 2 Pro: supports resolution
            render_job.settings["resolution"] = resolution
        elif model == "kling-v2.5-turbo-pro":
            # Kling V2.5 Turbo Pro: supports negative_prompt, guidance_scale, last_image
            if negative_prompt:
                render_job.settings["negative_prompt"] = negative_prompt
            if guidance_scale is not None:
                render_job.settings["guidance_scale"] = guidance_scale
            if last_image_url:
                render_job.settings["last_image_url"] = last_image_url
        elif model == "hailuo-2.3-i2v-standard":
            # Hailuo 2.3 I2V Standard: supports prompt_expansion
            render_job.settings["enable_prompt_expansion"] = enable_prompt_expansion
        elif model == "hailuo-2.3-i2v-pro":
            # Hailuo 2.3 I2V Pro: supports prompt_expansion, fixed 5s and 1080p
            render_job.settings["enable_prompt_expansion"] = enable_prompt_expansion if model_config.get("supports_prompt_expansion") else True
            render_job.settings["duration"] = 5  # Fixed
            render_job.settings["resolution"] = "1080p"  # Fixed
        else:
            # Other models: full settings
            render_job.settings["resolution"] = resolution
            if negative_prompt:
                render_job.settings["negative_prompt"] = negative_prompt
            if audio_url:
                render_job.settings["audio_url"] = audio_url
            render_job.settings["enable_prompt_expansion"] = enable_prompt_expansion
            render_job.settings["seed"] = seed
        
        # Add Veo-specific settings
        if model_config.get("uses_aspect_ratio"):
            render_job.settings["aspect_ratio"] = aspect_ratio
            render_job.settings["generate_audio"] = generate_audio
        
        session.add(render_job)
        await session.commit()
        await session.refresh(render_job)
        
        logger.info(f"Created render job {job_id} for user {current_user.id}")
        
        # Deduct credits when job is submitted
        await credits_service.spend_credits(
            user_id=current_user.id,
            amount=estimated_credit_cost,
            reason="image_to_video_generation",
            metadata={
                "job_id": str(job_id),
                "model": model,
                "resolution": resolution,
                "duration": duration
            }
        )
        
        return ImageToVideoResponse(
            job_id=job_id,
            status="pending",
            task_id=task_id,
            message="Job submitted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting image-to-video job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        )


@router.get("/jobs")
async def get_image_to_video_jobs(
    limit: int = 10,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user's image-to-video jobs."""
    try:
        stmt = (
            select(RenderJob)
            .where(RenderJob.user_id == current_user.id)
            .where(RenderJob.provider.like("%-image-to-video"))
            .order_by(RenderJob.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        
        # Check status for jobs that are still pending/running or completed but missing URL
        wavespeed_service = WaveSpeedService()
        if wavespeed_service.api_key:
            for job in jobs:
                if job.status in ["pending", "running"] or (job.status == "completed" and not job.output_url):
                    wavespeed_task_id = job.settings.get('wavespeed_task_id')
                    if wavespeed_task_id:
                        try:
                            logger.info(f"Checking status for job {job.id} (status: {job.status}, task: {wavespeed_task_id})")
                            wavespeed_result = await wavespeed_service.get_job_result(wavespeed_task_id)
                            task_data = wavespeed_result.get('data', {})
                            
                            # Get new status and outputs
                            new_status = task_data.get('status', job.status)
                            outputs = task_data.get('outputs', [])
                            error_message = task_data.get('error')
                            
                            # Map WaveSpeed status to our status
                            status_map = {
                                "created": "pending",
                                "processing": "running",
                                "completed": "completed",
                                "failed": "failed"
                            }
                            mapped_status = status_map.get(new_status, new_status)
                            
                            # Update job if status changed or URL found
                            should_commit = False
                            
                            if mapped_status != job.status:
                                job.status = mapped_status
                                should_commit = True
                                
                            if outputs:
                                output_url = None
                                if isinstance(outputs, list) and len(outputs) > 0:
                                    output_url = outputs[0]
                                elif isinstance(outputs, str):
                                    output_url = outputs
                                
                                if output_url and output_url != job.output_url:
                                    job.output_url = output_url
                                    should_commit = True
                                    logger.info(f"Retrieved output URL for job {job.id}: {job.output_url}")
                                    
                            if error_message and error_message != job.error_message:
                                job.error_message = error_message
                                should_commit = True
                                
                            if should_commit:
                                job.updated_at = datetime.utcnow()
                                session.add(job)
                                await session.commit()
                                logger.info(f"Updated job {job.id} status to {mapped_status}")
                                
                                # If newly completed, deduct credits if not already done
                                if mapped_status == "completed" and job.actual_credit_cost == 0:
                                    actual_cost = job.estimated_credit_cost
                                    job.actual_credit_cost = actual_cost
                                    credits_service = CreditsService(session)
                                    await credits_service.spend_credits(
                                        user_id=current_user.id,
                                        amount=actual_cost,
                                        reason="image_to_video_generation",
                                        metadata={"job_id": str(job.id), "task_id": wavespeed_task_id}
                                    )
                                    session.add(job)
                                    await session.commit()
                                    logger.info(f"Deducted {actual_cost} credits for completed job {job.id}")
                                    
                        except Exception as e:
                            logger.warning(f"Failed to check status for job {job.id}: {e}")
        
        return {
            "jobs": [
                {
                    "job_id": str(job.id),
                    "status": job.status,
                    "model": job.settings.get("model") if job.settings else None,
                    "model_display_name": job.settings.get("model_display_name", "Wan 2.5 Image To Video") if job.settings else "Wan 2.5 Image To Video",
                    "size": job.settings.get("resolution") if job.settings else None,
                    "duration": job.settings.get("duration") if job.settings else None,
                    "prompt": job.input_prompt,
                    "output_url": job.output_url,
                    "error": job.error_message,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                    "settings": job.settings  # Keep settings for backward compatibility
                }
                for job in jobs
            ],
            "total": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"Error fetching image-to-video jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}")
async def get_image_to_video_job(
    job_id: str,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific image-to-video job."""
    try:
        stmt = (
            select(RenderJob)
            .where(RenderJob.id == job_id)
            .where(RenderJob.user_id == current_user.id)
            .where(RenderJob.provider.like("%-image-to-video"))
        )
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Get WaveSpeed task ID from settings
        wavespeed_task_id = job.settings.get("wavespeed_task_id") if job.settings else None
        if not wavespeed_task_id:
            logger.warning(f"Job {job_id} does not have a WaveSpeed task ID")
        else:
            # Always check status with WaveSpeed (same as text-to-video)
            try:
                wavespeed_service = WaveSpeedService()
                if wavespeed_service.api_key:
                    logger.info(f"Polling WaveSpeed for task {wavespeed_task_id}")
                    wavespeed_result = await wavespeed_service.get_job_result(wavespeed_task_id)
                    
                    # Update render job with latest status
                    task_data = wavespeed_result.get('data', {})
                    new_status = task_data.get('status', job.status)
                    outputs = task_data.get('outputs', [])
                    error_message = task_data.get('error')
                    
                    logger.info(f"WaveSpeed status for {wavespeed_task_id}: {new_status}")
                    if outputs:
                        logger.info(f"WaveSpeed outputs found: {outputs}")
                    else:
                        logger.warning(f"No outputs found in WaveSpeed response for task {wavespeed_task_id}. Status: {new_status}")
                    
                    # Map WaveSpeed status to our status
                    status_map = {
                        "created": "pending",
                        "processing": "running",
                        "completed": "completed",
                        "failed": "failed"
                    }
                    mapped_status = status_map.get(new_status, new_status)
                    
                    # Update render job
                    job.status = mapped_status
                    
                    # Handle outputs - could be a list or a single string
                    # Always try to save output_url if we have it, even if job already has one (in case it was updated)
                    output_url_to_save = None
                    if outputs:
                        if isinstance(outputs, list) and len(outputs) > 0:
                            output_url_to_save = outputs[0]  # Use first output
                        elif isinstance(outputs, str):
                            output_url_to_save = outputs
                    
                    # Save output URL if we found one (even if job already has one, update it)
                    if output_url_to_save:
                        job.output_url = output_url_to_save
                        logger.info(f"Job {job_id} output URL saved/updated: {output_url_to_save}")
                    elif mapped_status == "completed" and not job.output_url:
                        # If status is completed but no outputs and no saved URL, try to get it from WaveSpeed again
                        logger.warning(f"Job {job_id} marked as completed but no outputs found. Status: {new_status}, checking again...")
                    
                    if error_message:
                        job.error_message = error_message
                        logger.error(f"Job {job_id} failed with error: {error_message}")
                    
                    job.updated_at = datetime.utcnow()
                    
                    session.add(job)
                    await session.commit()
                    await session.refresh(job)
                    
                    # If job is completed but still no output_url, try one more time to fetch it
                    if mapped_status == "completed" and not job.output_url:
                        logger.warning(f"Job {job_id} is completed but has no output_url. Attempting to fetch from WaveSpeed again...")
                        try:
                            # Wait a moment and check again (sometimes outputs appear slightly after status changes)
                            import asyncio
                            await asyncio.sleep(1)
                            retry_result = await wavespeed_service.get_job_result(wavespeed_task_id)
                            retry_data = retry_result.get('data', {})
                            retry_outputs = retry_data.get('outputs', [])
                            if retry_outputs:
                                if isinstance(retry_outputs, list) and len(retry_outputs) > 0:
                                    job.output_url = retry_outputs[0]
                                elif isinstance(retry_outputs, str):
                                    job.output_url = retry_outputs
                                if job.output_url:
                                    session.add(job)
                                    await session.commit()
                                    await session.refresh(job)
                                    logger.info(f"Successfully retrieved output URL on retry: {job.output_url}")
                        except Exception as retry_error:
                            logger.warning(f"Retry attempt failed for job {job_id}: {retry_error}")
            except Exception as e:
                logger.warning(f"Failed to check job status for {wavespeed_task_id}: {e}")
        
        return {
            "job_id": str(job.id),
            "task_id": job.settings.get("wavespeed_task_id") if job.settings else None,
            "status": job.status,
            "output_url": job.output_url,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "settings": job.settings,
            "model_display_name": job.settings.get("model_display_name", "Wan 2.5 Image To Video") if job.settings else "Wan 2.5 Image To Video"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image-to-video job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch job: {str(e)}"
        )

