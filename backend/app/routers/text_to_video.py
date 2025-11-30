"""
Text To Video API endpoints for WaveSpeed AI integration.
Handles text-to-video job submission using Wan 2.5.
"""
import logging
import uuid
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
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
from sqlalchemy import or_
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)


class TextToVideoRequest(BaseModel):
    prompt: str
    model: str = "google-veo-3.1"  # Model identifier
    size: str = "1280*720"  # 832*480, 480*832, 1280*720, 720*1280, 1920*1080, 1080*1920
    duration: int = 5  # 5 or 10
    negative_prompt: Optional[str] = None
    audio_url: Optional[str] = None
    enable_prompt_expansion: bool = False
    seed: int = -1


class TextToVideoResponse(BaseModel):
    job_id: str
    status: str
    task_id: str
    message: str


@router.get("/models")
async def get_available_models():
    """
    Get all available text-to-video models with their configurations (cached in Redis).
    """
    from app.utils.cache import get_cached, set_cached, cache_key
    
    cache_key_str = cache_key("cache", "text-to-video", "models", "v2")
    
    # Try cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return cached
    
    # Cache miss - build models list
    models = []
    for model_name, config in MODEL_CONFIGS.items():
        models.append({
            "id": model_name,
            "name": config.display_name,
            "description": config.description,
            "icon": config.icon,
            "supported_resolutions": config.supported_resolutions,
            "supported_durations": config.supported_durations,
            "supports_audio": config.supports_audio,
            "supports_negative_prompt": config.supports_negative_prompt,
            "supports_prompt_expansion": config.supports_prompt_expansion,
            "default_resolution": config.default_resolution,
            "default_duration": config.default_duration,
        })
    
    result = {"models": models}
    
    # Cache for 24 hours (models rarely change)
    await set_cached(cache_key_str, result, ttl=86400)
    
    return result


@router.get("/calculate-credits")
async def calculate_credits(
    model_id: str,
    resolution: str,
    duration: int
):
    """
    Calculate credit cost for a given model, resolution, and duration (cached for 1 hour).
    """
    from app.utils.cache import get_cached, set_cached, cache_key
    
    cache_key_str = cache_key("cache", "text-to-video", "credits", model_id, resolution, str(duration))
    
    # Try cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return cached
    
    model_config = get_model_config(model_id)
    if not model_config:
        return {"credits": 0}
    
    credits = model_config.get_credit_cost(resolution, duration)
    result = {"credits": credits}
    
    # Cache for 1 hour (credit costs rarely change)
    await set_cached(cache_key_str, result, ttl=3600)
    
    return result


@router.post("/submit", response_model=TextToVideoResponse)
async def submit_text_to_video(
    request: Request,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submit a Text To Video job.
    
    Accepts either JSON (application/json) or Form data (multipart/form-data).
    Either upload audio file OR provide audio_url.
    Files will be uploaded to Backblaze B2 first, then submitted to WaveSpeed AI.
    """
    content_type = request.headers.get("content-type", "")
    
    # Handle JSON requests
    if "application/json" in content_type:
        try:
            body = await request.json()
            prompt = body.get("prompt")
            model = body.get("model", "wan-2.5")
            size = body.get("size", "1280*720")
            duration = body.get("duration", 5)
            negative_prompt = body.get("negative_prompt")
            audio_url = body.get("audio_url")
            enable_prompt_expansion = body.get("enable_prompt_expansion", False)
            seed = body.get("seed", -1)
            audio = None  # No file upload in JSON mode
            logger.info("Received JSON request")
        except Exception as e:
            logger.warning(f"Failed to parse JSON body: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON body: {str(e)}"
            )
    else:
        # Handle Form data requests
        form_data = await request.form()
        prompt = form_data.get("prompt")
        model = form_data.get("model", "wan-2.5")
        size = form_data.get("size", "1280*720")
        duration = int(form_data.get("duration", 5)) if form_data.get("duration") else 5
        negative_prompt = form_data.get("negative_prompt")
        audio_url = form_data.get("audio_url")
        enable_prompt_expansion = form_data.get("enable_prompt_expansion", "false").lower() == "true"
        seed = int(form_data.get("seed", -1)) if form_data.get("seed") else -1
        # Get audio file if present
        audio_file = form_data.get("audio")
        audio = audio_file if isinstance(audio_file, UploadFile) else None
        logger.info("Received Form request")
    
    # Validate required fields
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt is required"
        )
    
    logger.info(f"Text To Video submission request from user {current_user.id}")
    logger.info(f"Model: {model}, Parameters: size={size}, duration={duration}, seed={seed}, prompt_expansion={enable_prompt_expansion}")
    
    # Duplicate job detection removed - allowing all job submissions
    
    # Get model configuration
    model_config = get_model_config(model)
    if not model_config:
        logger.error(f"Invalid model: {model}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model. Available models: {', '.join(MODEL_CONFIGS.keys())}"
        )
    
    # Validate size against model capabilities
    if not model_config.is_resolution_supported(size):
        logger.error(f"Resolution {size} not supported by model {model}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resolution {size} not supported by {model_config.display_name}. Supported: {', '.join(model_config.supported_resolutions)}"
        )
    
    # For Google Veo 3.1, round duration to nearest valid value (4, 6, or 8) before validation
    if model_config.name == "google-veo-3.1" and duration not in [4, 6, 8]:
        original_duration = duration
        if duration < 5:
            duration = 4
        elif duration < 7:
            duration = 6
        else:
            duration = 8
        logger.info(f"Google Veo 3.1: Rounded duration from {original_duration}s to {duration}s")
    
    # Validate duration against model capabilities
    if not model_config.is_duration_supported(duration):
        logger.error(f"Duration {duration} not supported by model {model}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duration {duration}s not supported by {model_config.display_name}. Supported: {', '.join(map(str, model_config.supported_durations))}s"
        )
    
    # Validate negative prompt support
    if negative_prompt and not model_config.supports_negative_prompt:
        logger.warning(f"Model {model} does not support negative prompts, ignoring")
        negative_prompt = None
    
    # Validate prompt expansion support
    if enable_prompt_expansion and not model_config.supports_prompt_expansion:
        logger.warning(f"Model {model} does not support prompt expansion, ignoring")
        enable_prompt_expansion = False
    
    # Validate audio support
    if (audio or audio_url) and not model_config.supports_audio:
        logger.warning(f"Model {model} does not support audio, ignoring audio parameter")
        audio = None
        audio_url = None
    
    # Convert seed to int
    try:
        seed_int = int(seed)
    except (ValueError, TypeError):
        logger.warning(f"Invalid seed value: {seed}, using -1")
        seed_int = -1
    
    try:
        # Initialize services
        storage_service = get_storage_service()
        wavespeed_service = WaveSpeedService()
        credits_service = CreditsService(session)
        
        # Check if WaveSpeed is configured
        if not wavespeed_service.api_key:
            logger.error("WaveSpeed API key not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WaveSpeed AI service is not configured. Please check WAVESPEED_API_KEY."
            )
        
        # Handle audio: upload or use provided URL
        final_audio_url = None
        if audio:
            # Check if storage is initialized
            if not storage_service._initialized:
                logger.error("Backblaze B2 storage not initialized - cannot upload audio file")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="File storage service is not available. Please check B2 configuration."
                )
            
            logger.info(f"Uploading audio file: {audio.filename}, content_type: {audio.content_type}")
            audio_data = await audio.read()
            # Run upload in thread executor to avoid blocking event loop
            audio_b2_url = await asyncio.to_thread(
                storage_service.upload_file,
                current_user.id,
                audio_data,
                audio.filename or "audio.mp3",
                audio.content_type or "audio/mpeg",
                "text-to-video"
            )
            if not audio_b2_url:
                logger.error("Failed to upload audio to Backblaze")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload audio to storage"
                )
            logger.info(f"Audio uploaded to Backblaze: {audio_b2_url}")
            final_audio_url = audio_b2_url
        elif audio_url:
            logger.info(f"Using provided audio URL: {audio_url}")
            final_audio_url = audio_url
        
        # Calculate credit cost using model configuration
        estimated_credit_cost = model_config.get_credit_cost(size, duration)
        logger.info(f"Credit cost for {model_config.display_name} {size} {duration}s: {estimated_credit_cost} credits")
        
        # Check user credits
        wallet = await credits_service.get_wallet(current_user.id)
        if wallet.balance_credits < estimated_credit_cost:
            logger.warning(f"Insufficient credits: user has {wallet.balance_credits}, needs {estimated_credit_cost}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {estimated_credit_cost}, Available: {wallet.balance_credits}"
            )
        
        # Submit job to WaveSpeed AI using model-specific endpoint
        logger.info(f"Submitting job to WaveSpeed AI using model: {model_config.display_name}...")
        
        # Handle models that use aspect_ratio instead of size
        aspect_ratio = None
        camera_fixed = None
        resolution_param = None
        generate_audio = None
        
        if model_config.uses_aspect_ratio:
            # Convert size to aspect_ratio
            width, height = map(int, size.split('*'))
            ratio = width / height
            # Map common resolutions to aspect ratios
            if abs(ratio - 21/9) < 0.1:
                aspect_ratio = "21:9"
            elif abs(ratio - 16/9) < 0.1:
                aspect_ratio = "16:9"
            elif abs(ratio - 4/3) < 0.1:
                aspect_ratio = "4:3"
            elif abs(ratio - 1.0) < 0.1:
                aspect_ratio = "1:1"
            elif abs(ratio - 3/4) < 0.1:
                aspect_ratio = "3:4"
            elif abs(ratio - 9/16) < 0.1:
                aspect_ratio = "9:16"
            else:
                # Default to 16:9 if no match
                aspect_ratio = "16:9"
            
            # Handle Veo 3 which uses resolution parameter
            if model_config.name == "google-veo-3":
                # Convert size to resolution (720p or 1080p)
                if width <= 1280 or height <= 1280:
                    resolution_param = "720p"
                else:
                    resolution_param = "1080p"
                generate_audio = True  # Default for Veo 3
            # Handle Veo 3.1 which uses resolution and aspect_ratio (not size)
            elif model_config.name == "google-veo-3.1":
                # Convert size to resolution (720p or 1080p)
                if width <= 1280 or height <= 1280:
                    resolution_param = "720p"
                else:
                    resolution_param = "1080p"
                generate_audio = True  # Default for Veo 3.1
                # Duration is already validated/rounded earlier in the function
            elif model_config.name == "seedance-v1-pro":
                camera_fixed = False  # Only for Seedance v1 Pro
            elif model_config.name == "seedance":
                camera_fixed = False  # Seedance v1 Lite also uses camera_fixed
            elif model_config.name == "kling-v2.5-turbo-pro":
                # Kling v2.5 Turbo Pro uses aspect_ratio (already set above)
                # No additional parameters needed
                pass
            elif model_config.name == "kling-v2.5-turbo-pro":
                # Kling v2.5 Turbo Pro uses aspect_ratio (already set above)
                # No additional parameters needed
                pass
        
        # Only send audio_url if model supports audio uploads (Veo models generate audio automatically)
        audio_url_to_send = None
        if model_config.supports_audio and final_audio_url:
            audio_url_to_send = final_audio_url
        
        # Hailuo 2.3 Pro only supports prompt and enable_prompt_expansion
        if model_config.name == "minimax-hailuo-2.3-pro":
            wavespeed_response = await wavespeed_service.submit_text_to_video(
                model_endpoint=model_config.api_endpoint,
                prompt=prompt,
                size=None,
                duration=None,
                negative_prompt=None,
                audio_url=None,
                enable_prompt_expansion=enable_prompt_expansion if model_config.supports_prompt_expansion else True,
                seed=None,
                aspect_ratio=None,
                camera_fixed=None,
                resolution=None,
                generate_audio=None,
                guidance_scale=None
            )
        # Kling v2.5 Turbo Pro uses aspect_ratio, doesn't support seed, audio_url, or enable_prompt_expansion
        elif model_config.name == "kling-v2.5-turbo-pro":
            wavespeed_response = await wavespeed_service.submit_text_to_video(
                model_endpoint=model_config.api_endpoint,
                prompt=prompt,
                size=None,
                duration=duration,
                negative_prompt=negative_prompt if model_config.supports_negative_prompt else None,
                audio_url=None,
                enable_prompt_expansion=None,
                seed=None,
                aspect_ratio=aspect_ratio,
                camera_fixed=None,
                resolution=None,
                generate_audio=None,
                guidance_scale=0.5  # Default 0.5 for Kling
            )
        # Google Veo 3.1 uses resolution, aspect_ratio, and generate_audio (not size, not enable_prompt_expansion)
        elif model_config.name == "google-veo-3.1":
            wavespeed_response = await wavespeed_service.submit_text_to_video(
                model_endpoint=model_config.api_endpoint,
                prompt=prompt,
                size=None,  # Veo 3.1 doesn't use size
                duration=duration,  # Already validated to be 4, 6, or 8
                negative_prompt=negative_prompt if model_config.supports_negative_prompt else None,
                audio_url=None,  # Veo 3.1 generates audio automatically, doesn't accept audio uploads
                enable_prompt_expansion=None,  # Not supported by Veo 3.1
                seed=seed_int,
                aspect_ratio=aspect_ratio,  # 16:9 or 9:16
                camera_fixed=None,
                resolution=resolution_param,  # 720p or 1080p
                generate_audio=generate_audio,  # True by default
                guidance_scale=None
            )
        # Google Veo 3 uses resolution, aspect_ratio, and generate_audio
        elif model_config.name == "google-veo-3":
            wavespeed_response = await wavespeed_service.submit_text_to_video(
                model_endpoint=model_config.api_endpoint,
                prompt=prompt,
                size=None,  # Veo 3 doesn't use size
                duration=duration,
                negative_prompt=negative_prompt if model_config.supports_negative_prompt else None,
                audio_url=None,  # Veo 3 generates audio automatically
                enable_prompt_expansion=None,  # Not supported by Veo 3
                seed=seed_int,
                aspect_ratio=aspect_ratio,  # 16:9 or 9:16
                camera_fixed=None,
                resolution=resolution_param,  # 720p or 1080p
                generate_audio=generate_audio,  # True by default
                guidance_scale=None
            )
        else:
            wavespeed_response = await wavespeed_service.submit_text_to_video(
                model_endpoint=model_config.api_endpoint,
                prompt=prompt,
                size=size if not model_config.uses_aspect_ratio else None,
                duration=duration,
                negative_prompt=negative_prompt if model_config.supports_negative_prompt else None,
                audio_url=audio_url_to_send,
                enable_prompt_expansion=enable_prompt_expansion if model_config.supports_prompt_expansion else False,
                seed=seed_int,
                aspect_ratio=aspect_ratio,
                camera_fixed=camera_fixed,
                resolution=resolution_param,
                generate_audio=generate_audio,
                guidance_scale=0.5 if model_config.name == "kling-v2.5-turbo-pro" else None  # Default 0.5 for Kling
            )
        
        # Extract task ID from response
        task_data = wavespeed_response.get('data', {})
        task_id = task_data.get('id')
        if not task_id:
            logger.error(f"No task ID in WaveSpeed response: {wavespeed_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="WaveSpeed API did not return a task ID"
            )
        
        logger.info(f"WaveSpeed job submitted successfully: task_id={task_id}")
        
        # Create render job record in database
        render_job = RenderJob(
            user_id=current_user.id,
            job_type="video",
            provider=f"{model}-text-to-video",
            input_prompt=prompt,
            settings={
                "model": model,
                "model_display_name": model_config.display_name,
                "size": size,
                "duration": duration,
                "negative_prompt": negative_prompt,
                "audio_url": final_audio_url,
                "enable_prompt_expansion": enable_prompt_expansion,
                "seed": seed,
                "wavespeed_task_id": task_id
            },
            status="pending",
            estimated_credit_cost=estimated_credit_cost,
            actual_credit_cost=estimated_credit_cost, # Set actual cost immediately
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(render_job)
        await session.commit()
        await session.refresh(render_job)
        
        # Deduct credits when job is submitted
        await credits_service.spend_credits(
            user_id=current_user.id,
            amount=estimated_credit_cost,
            reason="text_to_video_generation",
            metadata={
                "job_id": str(render_job.id),
                "task_id": task_id,
                "model": model
            }
        )
        
        logger.info(f"Render job created in database: job_id={render_job.id}, task_id={task_id}")
        
        return TextToVideoResponse(
            job_id=str(render_job.id),
            status="pending",
            task_id=task_id,
            message="Job submitted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting Text To Video job: {e}", exc_info=True)
        error_message = str(e)
        # Check if it's a WaveSpeed API error
        if "WaveSpeed API" in error_message:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=error_message
        )


@router.get("/status/{job_id}")
async def get_text_to_video_status(
    job_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get the status of a Text To Video job (cached for 10 seconds for fast polling).
    Polls WaveSpeed AI for the latest status and updates the database.
    """
    from app.utils.cache import get_cached, set_cached, cache_key
    
    logger.info(f"Status check request for job {job_id} from user {current_user.id}")
    
    cache_key_str = cache_key("cache", "job", str(job_id), "status")
    
    # Try cache first (short TTL for active jobs)
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return cached
    
    try:
        # Get render job from database
        result = await session.execute(
            select(RenderJob).where(
                RenderJob.id == job_id,
                RenderJob.user_id == current_user.id
            )
        )
        render_job = result.scalar_one_or_none()
        
        if not render_job:
            logger.warning(f"Job {job_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        logger.info(f"Found job {job_id}: status={render_job.status}, provider={render_job.provider}")
        
        # Get WaveSpeed task ID from settings
        wavespeed_task_id = render_job.settings.get('wavespeed_task_id')
        if not wavespeed_task_id:
            logger.error(f"No WaveSpeed task ID found for job {job_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job does not have a WaveSpeed task ID"
            )
        
        # Check status with WaveSpeed AI
        wavespeed_service = WaveSpeedService()
        if not wavespeed_service.api_key:
            logger.error("WaveSpeed API key not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WaveSpeed AI service is not configured"
            )
        
        logger.info(f"Polling WaveSpeed for task {wavespeed_task_id}")
        wavespeed_result = await wavespeed_service.get_job_result(wavespeed_task_id)
        
        # Update render job with latest status
        task_data = wavespeed_result.get('data', {})
        new_status = task_data.get('status', render_job.status)
        outputs = task_data.get('outputs', [])
        error_message = task_data.get('error')
        
        logger.info(f"WaveSpeed status for {wavespeed_task_id}: {new_status}")
        logger.info(f"WaveSpeed full response data: {task_data}")
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
        render_job.status = mapped_status
        
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
            render_job.output_url = output_url_to_save
            logger.info(f"Job {job_id} output URL saved/updated: {output_url_to_save}")
        elif mapped_status == "completed" and not render_job.output_url:
            # If status is completed but no outputs and no saved URL, try to get it from WaveSpeed again
            logger.warning(f"Job {job_id} marked as completed but no outputs found. Status: {new_status}, checking again...")
            # Don't fail - just log and continue. The URL might be available in a future check.
        
        if error_message:
            render_job.error_message = error_message
            logger.error(f"Job {job_id} failed with error: {error_message}")
        
        render_job.updated_at = datetime.utcnow()
        
        # If failed, refund credits
        if mapped_status == "failed" and render_job.actual_credit_cost > 0:
            refund_amount = render_job.actual_credit_cost
            credits_service = CreditsService(session)
            await credits_service.add_credits(
                user_id=current_user.id,
                amount=refund_amount,
                reason="text_to_video_refund",
                metadata={"job_id": str(job_id), "reason": "generation_failed"}
            )
            render_job.actual_credit_cost = 0
            logger.info(f"Refunded {refund_amount} credits for failed job {job_id}")
        
        session.add(render_job)
        await session.commit()
        await session.refresh(render_job)
        
        # If job is completed but still no output_url, try one more time to fetch it
        if mapped_status == "completed" and not render_job.output_url:
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
                        render_job.output_url = retry_outputs[0]
                    elif isinstance(retry_outputs, str):
                        render_job.output_url = retry_outputs
                    if render_job.output_url:
                        session.add(render_job)
                        await session.commit()
                        await session.refresh(render_job)
                        logger.info(f"Successfully retrieved output URL on retry: {render_job.output_url}")
            except Exception as retry_error:
                logger.warning(f"Retry attempt failed for job {job_id}: {retry_error}")
        
        result = {
            "job_id": str(render_job.id),
            "status": render_job.status,
            "task_id": wavespeed_task_id,
            "output_url": render_job.output_url,
            "error": render_job.error_message,
            "created_at": render_job.created_at.isoformat(),
            "updated_at": render_job.updated_at.isoformat()
        }
        
        # Cache result - short TTL for active jobs, longer for completed
        ttl = 10 if render_job.status in ["pending", "running"] else 60
        await set_cached(cache_key_str, result, ttl=ttl)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Text To Video job status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/jobs")
async def list_text_to_video_jobs(
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
    offset: int = 0
):
    """List user's text-to-video jobs (cached for 30 seconds)."""
    from app.utils.cache import get_cached, set_cached, cache_key
    
    cache_key_str = cache_key("cache", "user", str(current_user.id), "text-to-video", "jobs", str(limit), str(offset))
    
    # Try cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return cached
    
    logger.debug(f"Listing Text To Video jobs for user {current_user.id}, limit={limit}, offset={offset}")
    
    try:
        result = await session.execute(
            select(RenderJob)
            .where(
                RenderJob.user_id == current_user.id,
                RenderJob.provider.like("%-text-to-video")
            )
            .order_by(RenderJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        jobs = result.scalars().all()
        
        logger.debug(f"Found {len(jobs)} jobs for user {current_user.id}")
        
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
                                
                                # If failed, refund credits
                                if mapped_status == "failed" and job.actual_credit_cost > 0:
                                    refund_amount = job.actual_credit_cost
                                    credits_service = CreditsService(session)
                                    await credits_service.add_credits(
                                        user_id=current_user.id,
                                        amount=refund_amount,
                                        reason="text_to_video_refund",
                                        metadata={"job_id": str(job.id), "reason": "generation_failed"}
                                    )
                                    job.actual_credit_cost = 0
                                    logger.info(f"Refunded {refund_amount} credits for failed job {job.id}")
                                
                                session.add(job)
                                await session.commit()
                                logger.info(f"Updated job {job.id} status to {mapped_status}")
                                    
                        except Exception as e:
                            logger.warning(f"Failed to check status for job {job.id}: {e}")
        
        response = {
            "jobs": [
                {
                    "job_id": str(job.id),
                    "status": job.status,
                    "model": job.settings.get("model"),
                    "model_display_name": job.settings.get("model_display_name"),
                    "size": job.settings.get("size"),
                    "duration": job.settings.get("duration"),
                    "prompt": job.input_prompt,
                    "output_url": job.output_url,
                    "error": job.error_message,
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat()
                }
                for job in jobs
            ],
            "total": len(jobs)
        }
        
        # Cache for 2 seconds to allow frequent polling but prevent hammering
        await set_cached(cache_key_str, response, ttl=2)
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing Text To Video jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get("/all-jobs")
async def list_all_video_jobs(
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
    offset: int = 0
):
    """
    List all video jobs (both text-to-video and image-to-video) for the current user.
    This is a shared endpoint for the unified gallery (cached for 15 seconds).
    """
    from app.utils.cache import get_cached, set_cached, cache_key
    
    cache_key_str = cache_key("cache", "user", str(current_user.id), "all-video-jobs", str(limit), str(offset))
    
    # Try cache first
    cached = await get_cached(cache_key_str)
    if cached is not None:
        return cached
    
    logger.debug(f"Listing all video jobs for user {current_user.id}, limit={limit}, offset={offset}")
    
    try:
        result = await session.execute(
            select(RenderJob)
            .where(
                RenderJob.user_id == current_user.id,
                or_(
                    RenderJob.provider.like("%-text-to-video"),
                    RenderJob.provider.like("%-image-to-video")
                )
            )
            .order_by(RenderJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        jobs = result.scalars().all()
        
        logger.debug(f"Found {len(jobs)} video jobs for user {current_user.id}")
        
        # Access all attributes BEFORE any commits to prevent lazy loading issues
        # Store all job data in a list of dicts
        jobs_list = list(jobs)
        jobs_data_pre = []
        for job in jobs_list:
            # Access all attributes immediately to load them into memory
            jobs_data_pre.append({
                "job": job,
                "job_id": str(job.id),
                "job_status": job.status,
                "job_settings": job.settings if job.settings else {},
                "job_prompt": job.input_prompt,
                "job_output_url": job.output_url,
                "job_error": job.error_message,
                "job_created_at": job.created_at,
                "job_updated_at": job.updated_at,
                "job_provider": job.provider
            })
        
        # Check status for completed jobs that don't have output_url
        wavespeed_service = WaveSpeedService()
        if wavespeed_service.api_key:
            for job_data in jobs_data_pre:
                job = job_data["job"]
                if job_data["job_status"] in ["pending", "running"]:
                    try:
                        task_id = job_data["job_settings"].get("wavespeed_task_id")
                        if task_id:
                            result_data = await wavespeed_service.get_job_result(task_id)
                            wave_status = result_data.get("data", {}).get("status", job_data["job_status"])
                            output_urls = result_data.get("data", {}).get("outputs", [])
                            
                            # Update job status if changed
                            if wave_status != job_data["job_status"]:
                                job.status = wave_status
                                job_data["job_status"] = wave_status
                                if wave_status == "completed" and output_urls:
                                    output_url = output_urls[0] if isinstance(output_urls, list) else output_urls
                                    job.output_url = output_url
                                    job_data["job_output_url"] = output_url
                                await session.commit()
                                # Refresh the job to ensure updated_at is current
                                await session.refresh(job)
                                job_data["job_updated_at"] = job.updated_at
                    except Exception as e:
                        logger.warning(f"Failed to check status for job {job_data['job_id']}: {e}")
        
        # Build response from pre-loaded data
        jobs_data = []
        for job_data in jobs_data_pre:
            
            jobs_data.append({
                "job_id": job_data["job_id"],
                "status": job_data["job_status"],
                "model": job_data["job_settings"].get("model"),
                "model_display_name": job_data["job_settings"].get("model_display_name"),
                "size": job_data["job_settings"].get("size") or job_data["job_settings"].get("resolution"),
                "duration": job_data["job_settings"].get("duration"),
                "prompt": job_data["job_prompt"],
                "output_url": job_data["job_output_url"],
                "error": job_data["job_error"],
                "created_at": job_data["job_created_at"].isoformat() if job_data["job_created_at"] else None,
                "updated_at": job_data["job_updated_at"].isoformat() if job_data["job_updated_at"] else None,
                "job_type": "text-to-video" if "-text-to-video" in job_data["job_provider"] else "image-to-video"
            })
        
        response = {
            "jobs": jobs_data,
            "total": len(jobs_data)
        }
        
        # Cache for 2 seconds (all-jobs is polled frequently)
        await set_cached(cache_key_str, response, ttl=2)
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing all video jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )
