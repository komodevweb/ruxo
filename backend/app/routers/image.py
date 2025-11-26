"""
Image Generation API endpoints for WaveSpeed AI integration.
Handles text-to-image and image-to-image job submission.
"""
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.services.wavespeed_service import WaveSpeedService
from app.services.credits_service import CreditsService
from app.models.render import RenderJob
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Image generation model configurations
IMAGE_MODELS = {
    "google-nano-banana": {
        "id": "google-nano-banana",
        "display_name": "Google Nano Banana",
        "icon": "/images/logos/icons8-google-logo-48.svg",
        "endpoint": "/google/nano-banana/text-to-image",
        "supports_aspect_ratio": True,
        "supported_aspect_ratios": ["1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        "default_aspect_ratio": "1:1",
        "supports_resolution": False,
        "supported_resolutions": [],
        "default_resolution": None,
        "supports_output_format": True,
        "supported_output_formats": ["jpeg", "png"],
        "default_output_format": "jpeg",
        "credit_cost": 1.5  # $0.038 per image = 1.5 credits
    },
    "google-nano-banana-pro": {
        "id": "google-nano-banana-pro",
        "display_name": "Google Nano Banana Pro",
        "icon": "/images/logos/icons8-google-logo-48.svg",
        "endpoint": "/google/nano-banana-pro/text-to-image",
        "supports_aspect_ratio": True,
        "supported_aspect_ratios": ["1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        "default_aspect_ratio": "1:1",
        "supports_resolution": True,
        "supported_resolutions": ["1k", "2k", "4k"],
        "default_resolution": "1k",
        "supports_output_format": True,
        "supported_output_formats": ["jpeg", "png"],
        "default_output_format": "jpeg",
        "credit_by_resolution": {
            "1k": 1.5,  # 1.5 credits
            "2k": 1.5,  # 1.5 credits
            "4k": 1.5   # 1.5 credits
        }
    },
    "alibaba-wan-2.5": {
        "id": "alibaba-wan-2.5",
        "display_name": "Alibaba Wan 2.5",
        "icon": "/images/logos/wan-logo.svg",
        "endpoint": "/alibaba/wan-2.5/text-to-image",
        "supports_aspect_ratio": True,
        "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
        "default_aspect_ratio": "1:1",
        "supports_resolution": True,
        "supported_resolutions": ["480p", "720p", "1080p"],
        "default_resolution": "720p",
        "supports_output_format": False,
        "supported_output_formats": [],
        "default_output_format": None,
        "supports_negative_prompt": True,
        "supports_prompt_expansion": True,
        "supports_seed": True,
        "credit_cost": 1,  # $0.03 per image = ~1 credit (using 2.5x scaling: $0.03 * 2.5 = 0.075, rounded to 1)
        # Mapping function to convert resolution + aspect_ratio to pixel dimensions
        "resolution_to_size": {
            "480p": {
                "1:1": "768*768",
                "4:3": "768*576",  # Approximate, closest to 768*768
                "3:4": "576*768",
                "16:9": "854*480",
                "9:16": "480*854"
            },
            "720p": {
                "1:1": "1024*1024",
                "4:3": "1024*768",
                "3:4": "768*1024",
                "16:9": "1280*720",
                "9:16": "720*1280"
            },
            "1080p": {
                "1:1": "1024*1024",  # Closest available
                "4:3": "1440*1024",
                "3:4": "1024*1440",
                "16:9": "1920*1080",  # Not in API, use closest: 1440*1024
                "9:16": "1080*1920"  # Not in API, use closest: 1024*1440
            }
        }
    },
    "flux-1.1-pro-ultra": {
        "id": "flux-1.1-pro-ultra",
        "display_name": "Flux 1.1 Pro Ultra",
        "icon": "/images/logos/flux.svg",
        "endpoint": "/wavespeed-ai/flux-1.1-pro-ultra",
        "supports_aspect_ratio": False,
        "supported_aspect_ratios": [],
        "default_aspect_ratio": None,
        "supports_resolution": True,
        "supported_resolutions": ["1024*1024", "1280*1280", "1536*1536", "2048*2048"],
        "default_resolution": "1024*1024",
        "supports_output_format": False,
        "supported_output_formats": [],
        "default_output_format": None,
        "supports_negative_prompt": True,
        "supports_prompt_expansion": False,
        "supports_seed": True,
        "credit_cost": 1  # $0.06 per image = ~1 credit (using 2.5x scaling: $0.06 * 2.5 = 0.15, rounded to 1)
    },
    "stability-ai-stable-diffusion-3.5-large-turbo": {
        "id": "stability-ai-stable-diffusion-3.5-large-turbo",
        "display_name": "Stable Diffusion 3.5 Large Turbo",
        "icon": "/images/logos/stable-diffusion.svg",
        "endpoint": "/stability-ai/stable-diffusion-3.5-large-turbo",
        "supports_aspect_ratio": True,
        "supported_aspect_ratios": ["1:1", "3:4", "4:3", "16:9", "9:16"],
        "default_aspect_ratio": "1:1",
        "supports_resolution": False,
        "supported_resolutions": [],
        "default_resolution": None,
        "supports_output_format": False,
        "supported_output_formats": [],
        "default_output_format": None,
        "supports_negative_prompt": False,
        "supports_prompt_expansion": False,
        "supports_seed": True,
        "supports_image_to_image": True,
        "credit_cost": 1  # Pricing not specified, defaulting to 1 credit
    },
    "google-nano-banana-pro-edit": {
        "id": "google-nano-banana-pro-edit",
        "display_name": "Google Nano Banana Pro Edit",
        "icon": "/images/logos/icons8-google-logo-48.svg",
        "endpoint": "/google/nano-banana-pro/edit",
        "supports_aspect_ratio": True,
        "supported_aspect_ratios": ["1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        "default_aspect_ratio": "1:1",
        "supports_resolution": True,
        "supported_resolutions": ["1k", "2k", "4k"],
        "default_resolution": "1k",
        "supports_output_format": True,
        "supported_output_formats": ["jpeg", "png"],
        "default_output_format": "png",
        "supports_negative_prompt": False,
        "supports_prompt_expansion": False,
        "supports_seed": False,
        "supports_image_to_image": True,
        "credit_by_resolution": {
            "1k": 1,  # $0.14 = ~1 credit (using 2.5x scaling: $0.14 * 2.5 = 0.35, rounded to 1)
            "2k": 1,  # $0.14 = ~1 credit
            "4k": 1   # $0.24 = ~1 credit (using 2.5x scaling: $0.24 * 2.5 = 0.6, rounded to 1)
        }
    },
    "google-nano-banana-edit": {
        "id": "google-nano-banana-edit",
        "display_name": "Google Nano Banana Edit",
        "icon": "/images/logos/icons8-google-logo-48.svg",
        "endpoint": "/google/nano-banana/edit",
        "supports_aspect_ratio": True,
        "supported_aspect_ratios": ["1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        "default_aspect_ratio": "1:1",
        "supports_resolution": False,
        "supported_resolutions": [],
        "default_resolution": None,
        "supports_output_format": True,
        "supported_output_formats": ["jpeg", "png"],
        "default_output_format": "png",
        "supports_negative_prompt": False,
        "supports_prompt_expansion": False,
        "supports_seed": False,
        "supports_image_to_image": True,
        "credit_cost": 1  # Pricing not specified, defaulting to 1 credit
    },
    "flux-kontext-max": {
        "id": "flux-kontext-max",
        "display_name": "Flux Kontext Max",
        "icon": "/images/logos/flux.svg",
        "endpoint": "/wavespeed-ai/flux-kontext-max",
        "supports_aspect_ratio": True,
        "supported_aspect_ratios": ["21:9", "16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16", "9:21"],
        "default_aspect_ratio": "1:1",
        "supports_resolution": False,
        "supported_resolutions": [],
        "default_resolution": None,
        "supports_output_format": False,
        "supported_output_formats": [],
        "default_output_format": None,
        "supports_negative_prompt": False,
        "supports_prompt_expansion": False,
        "supports_seed": True,
        "supports_guidance_scale": True,
        "default_guidance_scale": 3.5,
        "supports_image_to_image": True,
        "credit_cost": 1  # Pricing not specified, defaulting to 1 credit
    },
    "alibaba-wan-2.5-image-edit": {
        "id": "alibaba-wan-2.5-image-edit",
        "display_name": "Alibaba Wan 2.5 Image Edit",
        "icon": "/images/logos/wan-logo.svg",
        "endpoint": "/alibaba/wan-2.5/image-edit",
        "supports_aspect_ratio": True,
        "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
        "default_aspect_ratio": "1:1",
        "supports_resolution": True,
        "supported_resolutions": ["480p", "720p", "1080p"],
        "default_resolution": "720p",
        "supports_output_format": False,
        "supported_output_formats": [],
        "default_output_format": None,
        "supports_negative_prompt": True,
        "supports_prompt_expansion": True,
        "supports_seed": True,
        "supports_image_to_image": True,
        "credit_cost": 1,  # Pricing not specified, defaulting to 1 credit
        # Mapping function to convert resolution + aspect_ratio to pixel dimensions
        "resolution_to_size": {
            "480p": {
                "1:1": "768*768",
                "4:3": "768*576",
                "3:4": "576*768",
                "16:9": "854*480",
                "9:16": "480*854"
            },
            "720p": {
                "1:1": "1024*1024",
                "4:3": "1024*768",
                "3:4": "768*1024",
                "16:9": "1280*720",
                "9:16": "720*1280"
            },
            "1080p": {
                "1:1": "1024*1024",
                "4:3": "1440*1024",
                "3:4": "1024*1440",
                "16:9": "1920*1080",
                "9:16": "1080*1920"
            }
        }
    }
}


class ImageGenerationResponse(BaseModel):
    job_id: str
    status: str
    task_id: str
    message: str


def calculate_credit_cost(model_id: str, resolution: Optional[str] = None) -> float:
    """
    Calculate credit cost for a given model and resolution.
    Returns the estimated credit cost.
    """
    model_config = IMAGE_MODELS.get(model_id)
    if not model_config:
        return 0
    
    # Check if model has fixed credit cost (like nano-banana)
    if "credit_cost" in model_config:
        return float(model_config["credit_cost"])
    
    # Check if model has resolution-based pricing (like nano-banana-pro)
    if resolution and "credit_by_resolution" in model_config:
        credit_by_resolution = model_config.get("credit_by_resolution", {})
        return float(credit_by_resolution.get(resolution, 1))  # Default to 1 credit
    
    return 1.0  # Default to 1 credit


@router.get("/models")
async def get_available_models():
    """
    Get available image generation models (cached in Redis).
    """
    from app.utils.cache import get_cached, set_cached
    
    cache_key = "cache:image:models"
    
    # Try to get from cache
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    
    # Cache miss - build models list
    models = []
    for model_id, config in IMAGE_MODELS.items():
        models.append({
            "id": config["id"],
            "display_name": config["display_name"],
            "icon": config.get("icon"),
            "supports_aspect_ratio": config.get("supports_aspect_ratio", False),
            "supported_aspect_ratios": config.get("supported_aspect_ratios", []),
            "default_aspect_ratio": config.get("default_aspect_ratio"),
            "supports_resolution": config.get("supports_resolution", False),
            "supported_resolutions": config.get("supported_resolutions", []),
            "default_resolution": config.get("default_resolution"),
            "supports_output_format": config.get("supports_output_format", False),
            "supported_output_formats": config.get("supported_output_formats", []),
            "default_output_format": config.get("default_output_format"),
            "supports_negative_prompt": config.get("supports_negative_prompt", False),
            "supports_prompt_expansion": config.get("supports_prompt_expansion", False),
            "supports_seed": config.get("supports_seed", False),
            "supports_image_to_image": config.get("supports_image_to_image", False)
        })
    
    result = {"models": models}
    
    # Cache for 24 hours (models rarely change)
    await set_cached(cache_key, result, ttl=86400)
    
    return result


@router.get("/calculate-credits")
async def calculate_credits(
    model_id: str,
    resolution: Optional[str] = None
):
    """
    Calculate credit cost for image generation.
    Returns the actual amount that will be charged (rounded up).
    Cached in Redis for 24 hours since credit costs don't change frequently.
    """
    from app.utils.cache import get_cached, set_cached, cache_key
    
    # Generate cache key based on model and resolution
    resolution_part = resolution or "default"
    cache_key_str = cache_key("cache", "image", "credits", model_id, resolution_part)
    
    # Try to get from cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return cached
    
    # Cache miss - calculate credit cost
    estimated_credit_cost = calculate_credit_cost(model_id, resolution)
    # Round up to nearest integer for actual credit deduction (matches submit endpoint logic)
    # If already an integer, use it; otherwise round down and add 1
    estimated_credit_cost_int = int(estimated_credit_cost) if estimated_credit_cost == int(estimated_credit_cost) else int(estimated_credit_cost) + 1
    
    result = {"credits": estimated_credit_cost_int}
    
    # Cache for 24 hours (credit costs are based on model config and rarely change)
    await set_cached(cache_key_str, result, ttl=86400)
    
    return result


@router.post("/submit", response_model=ImageGenerationResponse)
async def submit_image_generation(
    request: Request,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submit an Image Generation job.
    
    Accepts JSON body with prompt and other parameters.
    """
    try:
        body = await request.json()
        prompt = body.get("prompt")
        model = body.get("model", "google-nano-banana-pro")
        aspect_ratio = body.get("aspect_ratio")
        resolution = body.get("resolution")
        output_format = body.get("output_format", "jpeg")
        enable_sync_mode = body.get("enable_sync_mode", False)
        enable_base64_output = body.get("enable_base64_output", False)
        negative_prompt = body.get("negative_prompt")
        enable_prompt_expansion = body.get("enable_prompt_expansion", False)
        seed = body.get("seed", -1)
        image_url = body.get("image_url")  # For image-to-image models
        
        logger.info("Received Image Generation JSON request")
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
    
    # Get model config
    model_config = IMAGE_MODELS.get(model)
    if not model_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported model: {model}"
        )
    
    # Validate parameters based on model config
    if model_config.get("supports_aspect_ratio"):
        if not aspect_ratio:
            # Use default aspect ratio if not provided
            aspect_ratio = model_config.get("default_aspect_ratio")
        if aspect_ratio and aspect_ratio not in model_config.get("supported_aspect_ratios", []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported aspect_ratio: {aspect_ratio}. Supported: {model_config.get('supported_aspect_ratios')}"
            )
    
    if model_config.get("supports_resolution"):
        if not resolution:
            # Use default resolution if not provided
            resolution = model_config.get("default_resolution")
        if resolution and resolution not in model_config.get("supported_resolutions", []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported resolution: {resolution}. Supported: {model_config.get('supported_resolutions')}"
            )
    elif resolution:
        # Model doesn't support resolution, but it was provided
        logger.warning(f"Model {model} doesn't support resolution parameter, ignoring it")
        resolution = None
    
    if model_config.get("supports_output_format"):
        if output_format not in model_config.get("supported_output_formats", []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported output_format: {output_format}. Supported: {model_config.get('supported_output_formats')}"
            )
    
    # Validate negative_prompt if model supports it
    if model_config.get("supports_negative_prompt") and negative_prompt:
        if not isinstance(negative_prompt, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="negative_prompt must be a string"
            )
    
    # Validate image_url if model supports image-to-image
    if model_config.get("supports_image_to_image"):
        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="image_url is required for image-to-image models"
            )
    
    # Validate enable_prompt_expansion if model supports it
    if model_config.get("supports_prompt_expansion") and enable_prompt_expansion:
        if not isinstance(enable_prompt_expansion, bool):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="enable_prompt_expansion must be a boolean"
            )
    
    # Validate seed if model supports it
    if model_config.get("supports_seed") and seed is not None:
        try:
            seed_int = int(seed)
            if seed_int < -1 or seed_int > 2147483647:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="seed must be between -1 and 2147483647"
                )
            seed = seed_int
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="seed must be an integer"
            )
    
    # Calculate credit cost
    # For models without resolution (like nano-banana), pass None
    resolution_for_cost = resolution if model_config.get("supports_resolution") else None
    estimated_credit_cost = calculate_credit_cost(model, resolution_for_cost)
    # Round up to nearest integer for actual credit deduction (1.5 -> 2)
    estimated_credit_cost_int = int(estimated_credit_cost) if estimated_credit_cost == int(estimated_credit_cost) else int(estimated_credit_cost) + 1
    logger.info(f"Credit cost for {model_config['display_name']} {f'{resolution} ' if resolution else ''}: {estimated_credit_cost} credits (charging {estimated_credit_cost_int})")
    
    # Check user credits
    credits_service = CreditsService(session)
    wallet = await credits_service.get_wallet(current_user.id)
    if wallet.balance_credits < estimated_credit_cost_int:
        logger.warning(f"Insufficient credits: user has {wallet.balance_credits}, needs {estimated_credit_cost_int}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {estimated_credit_cost_int}, Available: {wallet.balance_credits}"
        )
    
    # Duplicate job detection removed - allowing all job submissions
    
    # Submit job to WaveSpeed AI
    logger.info(f"Submitting job to WaveSpeed AI {model_config['display_name']}...")
    wavespeed_service = WaveSpeedService()
    
    try:
        if model == "google-nano-banana":
            wavespeed_response = await wavespeed_service.submit_google_nano_banana_text_to_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                output_format=output_format,
                enable_sync_mode=enable_sync_mode,
                enable_base64_output=enable_base64_output
            )
        elif model == "google-nano-banana-pro":
            wavespeed_response = await wavespeed_service.submit_google_nano_banana_pro_text_to_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                output_format=output_format,
                enable_sync_mode=enable_sync_mode,
                enable_base64_output=enable_base64_output
            )
        elif model == "alibaba-wan-2.5":
            # Convert resolution + aspect_ratio to pixel dimensions
            resolution_to_size = model_config.get("resolution_to_size", {})
            selected_res = resolution or model_config.get("default_resolution", "720p")
            selected_ratio = aspect_ratio or model_config.get("default_aspect_ratio", "1:1")
            
            # Get the pixel size from the mapping
            size = None
            if resolution_to_size and selected_res in resolution_to_size:
                size = resolution_to_size[selected_res].get(selected_ratio)
            
            # Fallback to default if mapping not found
            if not size:
                size = "1024*1024"  # Default fallback
            
            wavespeed_response = await wavespeed_service.submit_alibaba_wan_2_5_text_to_image(
                prompt=prompt,
                size=size,
                enable_prompt_expansion=enable_prompt_expansion if model_config.get("supports_prompt_expansion") else False,
                negative_prompt=negative_prompt if model_config.get("supports_negative_prompt") else None,
                seed=seed if model_config.get("supports_seed") else -1
            )
        elif model == "flux-1.1-pro-ultra":
            wavespeed_response = await wavespeed_service.submit_flux_1_1_pro_ultra_text_to_image(
                prompt=prompt,
                size=resolution or "1024*1024",
                negative_prompt=negative_prompt if model_config.get("supports_negative_prompt") else None,
                seed=seed if model_config.get("supports_seed") else -1
            )
        elif model == "stability-ai-stable-diffusion-3.5-large-turbo":
            wavespeed_response = await wavespeed_service.submit_stability_ai_stable_diffusion_3_5_large_turbo_text_to_image(
                prompt=prompt,
                image_url=image_url if model_config.get("supports_image_to_image") else None,
                aspect_ratio=aspect_ratio or "1:1",
                seed=seed if model_config.get("supports_seed") else -1,
                enable_base64_output=enable_base64_output
            )
        elif model == "google-nano-banana-pro-edit":
            # Google Nano Banana Pro Edit uses images array
            if not image_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="image_url is required for Google Nano Banana Pro Edit"
                )
            wavespeed_response = await wavespeed_service.submit_google_nano_banana_pro_edit(
                prompt=prompt,
                images=[image_url],  # Convert single URL to array
                aspect_ratio=aspect_ratio,
                resolution=resolution or "1k",
                output_format=output_format or "png",
                enable_sync_mode=enable_sync_mode,
                enable_base64_output=enable_base64_output
            )
        elif model == "google-nano-banana-edit":
            # Google Nano Banana Edit uses images array
            if not image_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="image_url is required for Google Nano Banana Edit"
                )
            wavespeed_response = await wavespeed_service.submit_google_nano_banana_edit(
                prompt=prompt,
                images=[image_url],  # Convert single URL to array
                aspect_ratio=aspect_ratio,
                output_format=output_format or "png",
                enable_sync_mode=enable_sync_mode,
                enable_base64_output=enable_base64_output
            )
        elif model == "flux-kontext-max":
            if not image_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="image_url is required for Flux Kontext Max"
                )
            # Get guidance_scale from request body or use default
            guidance_scale = body.get("guidance_scale", model_config.get("default_guidance_scale", 3.5))
            # Validate guidance_scale range (1.0 ~ 20.0)
            if guidance_scale < 1.0 or guidance_scale > 20.0:
                guidance_scale = 3.5  # Default if out of range
            
            wavespeed_response = await wavespeed_service.submit_flux_kontext_max(
                prompt=prompt,
                image_url=image_url,
                aspect_ratio=aspect_ratio if model_config.get("supports_aspect_ratio") else None,
                guidance_scale=guidance_scale,
                seed=seed if model_config.get("supports_seed") else -1,
                enable_sync_mode=enable_sync_mode
            )
        elif model == "alibaba-wan-2.5-image-edit":
            if not image_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="image_url is required for Alibaba Wan 2.5 Image Edit"
                )
            # Convert resolution and aspect_ratio to size format
            size = "1024*1024"  # Default
            if model_config.get("resolution_to_size") and resolution and aspect_ratio:
                size_mapping = model_config["resolution_to_size"].get(resolution, {})
                size = size_mapping.get(aspect_ratio, "1024*1024")
            wavespeed_response = await wavespeed_service.submit_alibaba_wan_2_5_image_edit(
                prompt=prompt,
                image_url=image_url,
                size=size,
                enable_prompt_expansion=enable_prompt_expansion if model_config.get("supports_prompt_expansion") else False,
                negative_prompt=negative_prompt if model_config.get("supports_negative_prompt") else None,
                seed=seed if model_config.get("supports_seed") else -1
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported model: {model}"
            )
    except Exception as e:
        logger.error(f"Error submitting to WaveSpeed AI: {e}", exc_info=True)
        error_message = str(e)
        if "WaveSpeed API error" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job to WaveSpeed AI: {error_message}"
        )
    
    # Extract task ID from response
    wavespeed_data = wavespeed_response.get("data", {})
    wavespeed_task_id = wavespeed_data.get("id", "")
    wavespeed_status = wavespeed_data.get("status", "created")
    
    if not wavespeed_task_id:
        logger.error(f"No task ID in WaveSpeed response: {wavespeed_response}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task ID from WaveSpeed AI"
        )
    
    # Get output URL if sync mode is enabled and job is completed
    output_url = None
    if enable_sync_mode and wavespeed_status == "completed":
        outputs = wavespeed_data.get("outputs", [])
        if outputs and len(outputs) > 0:
            output_url = outputs[0] if isinstance(outputs, list) else outputs
    
    # Create render job record
    job_id = uuid.uuid4()
    # Determine provider name based on model type (reuse the same logic from duplicate check)
    if model_config.get("supports_image_to_image"):
        provider = f"{model}-image-edit" if "edit" in model else f"{model}-image-to-image"
    else:
        provider = f"{model}-text-to-image"
    
    render_job = RenderJob(
        id=job_id,
        user_id=current_user.id,
        job_type="image",
        provider=provider,
        status="pending" if not output_url else "completed",
        input_prompt=prompt,
        output_url=output_url,
        estimated_credit_cost=estimated_credit_cost,
        actual_credit_cost=0,
        settings={
            "model": model,
            "model_display_name": model_config["display_name"],
            "wavespeed_task_id": wavespeed_task_id,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "output_format": output_format,
            "enable_sync_mode": enable_sync_mode,
            "enable_base64_output": enable_base64_output,
            "negative_prompt": negative_prompt,
            "enable_prompt_expansion": enable_prompt_expansion,
            "seed": seed,
            "image_url": image_url
        }
    )
    
    session.add(render_job)
    await session.commit()
    await session.refresh(render_job)
    
    # Deduct credits
    try:
        await credits_service.spend_credits(
            user_id=current_user.id,
            amount=estimated_credit_cost_int,
            reason="image_generation",
            metadata={
                "job_id": str(job_id),
                "model": model,
                "resolution": resolution
            }
        )
        logger.info(f"Deducted {estimated_credit_cost_int} credits from user {current_user.id}")
    except Exception as e:
        logger.error(f"Error deducting credits: {e}", exc_info=True)
        # Don't fail the job if credit deduction fails - we'll handle it separately
    
    logger.info(f"Image generation job created: {job_id}, task_id={wavespeed_task_id}")
    
    return {
        "job_id": str(job_id),
        "status": render_job.status,
        "task_id": wavespeed_task_id,
        "message": "Job submitted successfully"
    }


@router.get("/jobs")
async def get_image_generation_jobs(
    limit: int = 50,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user's image generation jobs."""
    try:
        stmt = (
            select(RenderJob)
            .where(RenderJob.user_id == current_user.id)
            .where(
                (RenderJob.provider.like("%-text-to-image")) |
                (RenderJob.provider.like("%-image-edit")) |
                (RenderJob.provider.like("%-image-to-image"))
            )
            .order_by(RenderJob.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        
        # Check status for completed jobs that don't have output_url
        wavespeed_service = WaveSpeedService()
        if wavespeed_service.api_key:
            for job in jobs:
                if (job.status == "completed" or job.status == "running" or job.status == "pending") and not job.output_url:
                    try:
                        wavespeed_task_id = job.settings.get("wavespeed_task_id") if job.settings else None
                        if wavespeed_task_id:
                            wavespeed_result = await wavespeed_service.get_job_result(wavespeed_task_id)
                            task_data = wavespeed_result.get('data', {})
                            outputs = task_data.get('outputs', [])
                            
                            if outputs:
                                if isinstance(outputs, list) and len(outputs) > 0:
                                    job.output_url = outputs[0]
                                elif isinstance(outputs, str):
                                    job.output_url = outputs
                                
                                if job.output_url:
                                    job.status = "completed"
                                    session.add(job)
                                    await session.commit()
                                    await session.refresh(job)  # Refresh to ensure all attributes are loaded
                                    logger.info(f"Retrieved missing output URL for job {job.id}: {job.output_url}")
                            
                            # Update status
                            wavespeed_status = task_data.get('status', '')
                            if wavespeed_status == "failed":
                                job.status = "failed"
                                job.error_message = task_data.get('error', 'Unknown error')
                                session.add(job)
                                await session.commit()
                                await session.refresh(job)  # Refresh to ensure all attributes are loaded
                            elif wavespeed_status == "completed" and not job.output_url:
                                # Retry getting output
                                retry_count = 0
                                while retry_count < 3 and not job.output_url:
                                    await asyncio.sleep(2)
                                    wavespeed_result = await wavespeed_service.get_job_result(wavespeed_task_id)
                                    task_data = wavespeed_result.get('data', {})
                                    outputs = task_data.get('outputs', [])
                                    if outputs:
                                        if isinstance(outputs, list) and len(outputs) > 0:
                                            job.output_url = outputs[0]
                                        elif isinstance(outputs, str):
                                            job.output_url = outputs
                                    retry_count += 1
                                
                                if job.output_url:
                                    job.status = "completed"
                                    session.add(job)
                                    await session.commit()
                                    await session.refresh(job)  # Refresh to ensure all attributes are loaded
                    except Exception as e:
                        logger.warning(f"Failed to check status for job {job.id}: {e}")
        
        # Ensure all attributes are loaded before accessing them
        jobs_list = []
        for job in jobs:
            await session.refresh(job)  # Refresh each job to ensure all attributes are loaded
            
            # Access all attributes explicitly to ensure they're loaded
            job_id = str(job.id)
            job_status = job.status
            job_settings = job.settings
            job_prompt = job.input_prompt
            job_output_url = job.output_url
            job_error = job.error_message
            job_created_at = job.created_at
            job_updated_at = job.updated_at
            
            jobs_list.append({
                "job_id": job_id,
                "status": job_status,
                "model": job_settings.get("model") if job_settings else None,
                "model_display_name": job_settings.get("model_display_name", "Google Nano Banana Pro") if job_settings else "Google Nano Banana Pro",
                "aspect_ratio": job_settings.get("aspect_ratio") if job_settings else None,
                "resolution": job_settings.get("resolution") if job_settings else None,
                "output_format": job_settings.get("output_format") if job_settings else None,
                "prompt": job_prompt,
                "output_url": job_output_url,
                "error": job_error,
                "created_at": job_created_at.isoformat() if job_created_at else None,
                "updated_at": job_updated_at.isoformat() if job_updated_at else None,
                "settings": job_settings
            })
        
        return {
            "jobs": jobs_list,
            "total": len(jobs_list)
        }
        
    except Exception as e:
        logger.error(f"Error fetching image generation jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}")
async def get_image_generation_job(
    job_id: str,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific image generation job by ID."""
    try:
        job_uuid = uuid.UUID(job_id)
        stmt = (
            select(RenderJob)
            .where(RenderJob.id == job_uuid)
            .where(RenderJob.user_id == current_user.id)
            .where(
                (RenderJob.provider.like("%-text-to-image")) |
                (RenderJob.provider.like("%-image-edit")) |
                (RenderJob.provider.like("%-image-to-image"))
            )
        )
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check status from WaveSpeed if job is still pending/running
        wavespeed_service = WaveSpeedService()
        if wavespeed_service.api_key:
            wavespeed_task_id = job.settings.get("wavespeed_task_id") if job.settings else None
            if wavespeed_task_id and (job.status == "pending" or job.status == "running" or not job.output_url):
                try:
                    wavespeed_result = await wavespeed_service.get_job_result(wavespeed_task_id)
                    task_data = wavespeed_result.get('data', {})
                    outputs = task_data.get('outputs', [])
                    
                    if outputs:
                        if isinstance(outputs, list) and len(outputs) > 0:
                            job.output_url = outputs[0]
                        elif isinstance(outputs, str):
                            job.output_url = outputs
                    
                    # Update status
                    wavespeed_status = task_data.get('status', '')
                    if wavespeed_status == "completed":
                        job.status = "completed"
                    elif wavespeed_status == "failed":
                        job.status = "failed"
                        job.error_message = task_data.get('error', 'Unknown error')
                    elif wavespeed_status == "processing":
                        job.status = "running"
                    
                    if job.output_url:
                        session.add(job)
                        await session.commit()
                        await session.refresh(job)  # Refresh to ensure all attributes are loaded
                        logger.info(f"Updated job {job.id} with output URL: {job.output_url}")
                except Exception as e:
                    logger.warning(f"Failed to check status for job {job.id}: {e}")
        
        # Ensure all attributes are loaded before accessing them
        await session.refresh(job)
        
        # Access all attributes explicitly to ensure they're loaded
        job_id = str(job.id)
        job_status = job.status
        job_settings = job.settings
        job_prompt = job.input_prompt
        job_output_url = job.output_url
        job_error = job.error_message
        job_created_at = job.created_at
        job_updated_at = job.updated_at
        
        return {
            "job_id": job_id,
            "status": job_status,
            "model": job_settings.get("model") if job_settings else None,
            "model_display_name": job_settings.get("model_display_name", "Google Nano Banana Pro") if job_settings else "Google Nano Banana Pro",
            "aspect_ratio": job_settings.get("aspect_ratio") if job_settings else None,
            "resolution": job_settings.get("resolution") if job_settings else None,
            "output_format": job_settings.get("output_format") if job_settings else None,
            "prompt": job_prompt,
            "output_url": job_output_url,
            "error": job_error,
            "created_at": job_created_at.isoformat() if job_created_at else None,
            "updated_at": job_updated_at.isoformat() if job_updated_at else None,
            "settings": job_settings
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image generation job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch job: {str(e)}"
        )

