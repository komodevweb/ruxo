"""
Wan Animate API endpoints for WaveSpeed AI integration.
Handles file uploads to Backblaze and job submission to WaveSpeed.
"""
import logging
import uuid
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.services.storage_service import get_storage_service
from app.services.wavespeed_service import WaveSpeedService
from app.services.credits_service import CreditsService
from app.models.render import RenderJob
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


class WanAnimateRequest(BaseModel):
    mode: str = "animate"  # "animate" or "replace"
    resolution: str = "480p"  # "480p" or "720p"
    prompt: Optional[str] = None
    seed: int = -1
    image_url: Optional[str] = None  # If provided, skip upload
    video_url: Optional[str] = None  # If provided, skip upload


class WanAnimateResponse(BaseModel):
    job_id: str
    status: str
    task_id: str
    message: str


@router.get("/calculate-credits")
async def calculate_credits(
    resolution: str = "480p"
):
    """
    Calculate credit cost for wan-animate.
    480p = 12 credits, 720p = 22 credits.
    """
    if resolution == "480p":
        credits = 12
    else:  # 720p
        credits = 22
    return {"credits": credits}


@router.post("/submit", response_model=WanAnimateResponse)
async def submit_wan_animate(
    request: Request,
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    mode: str = Form("animate"),
    resolution: str = Form("480p"),
    prompt: Optional[str] = Form(None),
    seed: str = Form("-1"),
    image_url: Optional[str] = Form(None),
    video_url: Optional[str] = Form(None),
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Submit a Wan 2.2 Animate job.
    
    Either upload files (image/video) OR provide URLs (image_url/video_url).
    Files will be uploaded to Backblaze B2 first, then submitted to WaveSpeed AI.
    Also accepts JSON body with image_url and video_url.
    """
    # Check if request is JSON (from frontend with URLs)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            image_url = body.get("image_url") or image_url
            video_url = body.get("video_url") or video_url
            mode = body.get("mode", mode)
            resolution = body.get("resolution", resolution)
            prompt = body.get("prompt") or prompt
            seed = str(body.get("seed", seed))
            logger.info("Received JSON request with URLs")
        except Exception as e:
            logger.warning(f"Failed to parse JSON body: {e}")
    
    logger.info(f"Wan Animate submission request from user {current_user.id}")
    logger.info(f"Parameters: mode={mode}, resolution={resolution}, seed={seed}, prompt={prompt}")
    logger.info(f"Files: image={image.filename if image else None}, video={video.filename if video else None}")
    logger.info(f"URLs: image_url={image_url}, video_url={video_url}")
    
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
        
        # Check if storage is initialized
        if not storage_service._initialized:
            logger.error("Backblaze B2 storage not initialized - cannot upload files")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File storage service is not available. Please check B2 configuration."
            )
        
        # Check if WaveSpeed is configured
        if not wavespeed_service.api_key:
            logger.error("WaveSpeed API key not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WaveSpeed AI service is not configured. Please check WAVESPEED_API_KEY."
            )
        
        # Handle image: upload or use provided URL
        if image:
            logger.info(f"Uploading image file: {image.filename}, content_type: {image.content_type}")
            image_data = await image.read()
            # Run upload in thread executor to avoid blocking event loop
            image_b2_url = await asyncio.to_thread(
                storage_service.upload_file,
                current_user.id,
                image_data,
                image.filename or "image.jpg",
                image.content_type or "image/jpeg",
                "wan-animate"
            )
            if not image_b2_url:
                logger.error("Failed to upload image to Backblaze")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload image to storage"
                )
            logger.info(f"Image uploaded to Backblaze: {image_b2_url}")
            final_image_url = image_b2_url
        elif image_url:
            logger.info(f"Using provided image URL: {image_url}")
            final_image_url = image_url
        else:
            logger.error("No image provided (neither file upload nor URL)")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'image' file or 'image_url' must be provided"
            )
        
        # Handle video: upload or use provided URL
        if video:
            logger.info(f"Uploading video file: {video.filename}, content_type: {video.content_type}")
            video_data = await video.read()
            # Run upload in thread executor to avoid blocking event loop
            video_b2_url = await asyncio.to_thread(
                storage_service.upload_file,
                current_user.id,
                video_data,
                video.filename or "video.mp4",
                video.content_type or "video/mp4",
                "wan-animate"
            )
            if not video_b2_url:
                logger.error("Failed to upload video to Backblaze")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload video to storage"
                )
            logger.info(f"Video uploaded to Backblaze: {video_b2_url}")
            final_video_url = video_b2_url
        elif video_url:
            logger.info(f"Using provided video URL: {video_url}")
            final_video_url = video_url
        else:
            logger.error("No video provided (neither file upload nor URL)")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'video' file or 'video_url' must be provided"
            )
        
        # Validate mode
        if mode not in ["animate", "replace"]:
            logger.error(f"Invalid mode: {mode}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="mode must be 'animate' or 'replace'"
            )
        
        # Validate resolution
        if resolution not in ["480p", "720p"]:
            logger.error(f"Invalid resolution: {resolution}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="resolution must be '480p' or '720p'"
            )
        
        # Credit cost based on resolution
        if resolution == "480p":
            estimated_credit_cost = 12
        else:  # 720p
            estimated_credit_cost = 22
        
        logger.info(f"Credit cost for {resolution}: {estimated_credit_cost} credits")
        
        # Check user credits
        wallet = await credits_service.get_wallet(current_user.id)
        if wallet.balance_credits < estimated_credit_cost:
            logger.warning(f"Insufficient credits: user has {wallet.balance_credits}, needs {estimated_credit_cost}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {estimated_credit_cost}, Available: {wallet.balance_credits}"
            )
        
        # Submit job to WaveSpeed AI
        logger.info("Submitting job to WaveSpeed AI...")
        wavespeed_response = await wavespeed_service.submit_wan_animate_job(
            image_url=final_image_url,
            video_url=final_video_url,
            mode=mode,
            resolution=resolution,
            prompt=prompt,
            seed=seed_int
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
            provider="wan-2.2-animate",
            input_prompt=prompt or "",
            settings={
                "mode": mode,
                "resolution": resolution,
                "seed": seed,
                "image_url": final_image_url,
                "video_url": final_video_url,
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
            reason="wan_animate_generation",
            metadata={
                "job_id": str(render_job.id),
                "task_id": task_id,
                "resolution": resolution
            }
        )
        
        logger.info(f"Render job created in database: job_id={render_job.id}, task_id={task_id}")
        
        return WanAnimateResponse(
            job_id=str(render_job.id),
            status="pending",
            task_id=task_id,
            message="Job submitted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting Wan Animate job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        )


@router.get("/status/{job_id}")
async def get_wan_animate_status(
    job_id: uuid.UUID,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get the status of a Wan Animate job.
    Polls WaveSpeed AI for the latest status and updates the database.
    """
    logger.info(f"Status check request for job {job_id} from user {current_user.id}")
    
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
                reason="wan_animate_refund",
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
        
        return {
            "job_id": str(render_job.id),
            "status": render_job.status,
            "task_id": wavespeed_task_id,
            "output_url": render_job.output_url,
            "error": render_job.error_message,
            "created_at": render_job.created_at.isoformat(),
            "updated_at": render_job.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Wan Animate job status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/jobs")
async def list_wan_animate_jobs(
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
    offset: int = 0
):
    """
    List all Wan Animate jobs for the current user.
    """
    logger.debug(f"Listing Wan Animate jobs for user {current_user.id}, limit={limit}, offset={offset}")
    
    try:
        result = await session.execute(
            select(RenderJob)
            .where(
                RenderJob.user_id == current_user.id,
                RenderJob.provider == "wan-2.2-animate"
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
                                        reason="wan_animate_refund",
                                        metadata={"job_id": str(job.id), "reason": "generation_failed"}
                                    )
                                    job.actual_credit_cost = 0
                                    logger.info(f"Refunded {refund_amount} credits for failed job {job.id}")
                                
                                session.add(job)
                                await session.commit()
                                logger.info(f"Updated job {job.id} status to {mapped_status}")
                                    
                        except Exception as e:
                            logger.warning(f"Failed to check status for job {job.id}: {e}")
        
        return {
            "jobs": [
                {
                    "job_id": str(job.id),
                    "status": job.status,
                    "mode": job.settings.get("mode"),
                    "resolution": job.settings.get("resolution"),
                    "image_url": job.settings.get("image_url"),
                    "video_url": job.settings.get("video_url"),
                    "output_url": job.output_url,
                    "error": job.error_message,
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat()
                }
                for job in jobs
            ],
            "total": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"Error listing Wan Animate jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )

