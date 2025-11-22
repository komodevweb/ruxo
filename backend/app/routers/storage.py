"""
File upload endpoints for Backblaze B2 storage.
Handles uploads for wan-animate, image-to-video, image-to-image, and text-to-video.
"""
import logging
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
from app.core.security import get_current_user
from app.models.user import UserProfile
from app.services.storage_service import get_storage_service
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload/wan-animate")
async def upload_wan_animate_file(
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Upload a file for wan-animate (image or video).
    Returns CloudFront URL for the uploaded file.
    """
    try:
        # Read file data
        file_data = await file.read()
        
        # Determine content type
        content_type = file.content_type or "application/octet-stream"
        
        # Determine folder based on file type
        if content_type.startswith("image/"):
            folder = "wan-animate"
            file_name = file.filename or "image.jpg"
            file_type = "image"
        elif content_type.startswith("video/"):
            folder = "wan-animate"
            file_name = file.filename or "video.mp4"
            file_type = "video"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image or video"
            )
        
        # Upload to Backblaze - run in thread executor to avoid blocking event loop
        storage_service = get_storage_service()
        logger.info(f"Starting upload for user {current_user.id}: {file_type} file '{file_name}' ({len(file_data)} bytes) to {folder}")
        
        cloudfront_url = await asyncio.to_thread(
            storage_service.upload_file,
            current_user.id,
            file_data,
            file_name,
            content_type,
            folder
        )
        
        if not cloudfront_url:
            logger.error(f"Upload failed for user {current_user.id}: {file_type} file '{file_name}' to {folder}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload {file_type} file to storage"
            )
        
        logger.info(f"Successfully uploaded {file_type} file for user {current_user.id} to {folder}/{current_user.id}/{file_name}: {cloudfront_url}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "url": cloudfront_url,
                "type": file_type
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/upload/image-to-video")
async def upload_image_to_video_file(
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Upload a file for image-to-video (image or video).
    Returns CloudFront URL for the uploaded file.
    """
    try:
        # Read file data
        file_data = await file.read()
        
        # Determine content type
        content_type = file.content_type or "application/octet-stream"
        
        # Determine folder and file name
        if content_type.startswith("image/"):
            folder = "image-to-video"
            file_name = file.filename or "image.jpg"
        elif content_type.startswith("video/"):
            folder = "image-to-video"
            file_name = file.filename or "video.mp4"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image or video"
            )
        
        # Upload to Backblaze - run in thread executor to avoid blocking event loop
        storage_service = get_storage_service()
        cloudfront_url = await asyncio.to_thread(
            storage_service.upload_file,
            current_user.id,
            file_data,
            file_name,
            content_type,
            folder
        )
        
        if not cloudfront_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        logger.info(f"Uploaded file for user {current_user.id} to {folder}: {cloudfront_url}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "url": cloudfront_url,
                "type": "image" if content_type.startswith("image/") else "video"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/upload/text-to-video")
async def upload_text_to_video_file(
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Upload an audio file for text-to-video.
    Returns CloudFront URL for the uploaded file.
    """
    try:
        # Read file data
        file_data = await file.read()
        
        # Determine content type
        content_type = file.content_type or "application/octet-stream"
        
        # Validate audio file
        if not content_type.startswith("audio/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an audio file (WAV or MP3)"
            )
        
        # Check file size (15 MB limit)
        if len(file_data) > 15 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file must be 15 MB or less"
            )
        
        folder = "text-to-video"
        file_name = file.filename or "audio.mp3"
        
        # Upload to Backblaze - run in thread executor to avoid blocking event loop
        storage_service = get_storage_service()
        cloudfront_url = await asyncio.to_thread(
            storage_service.upload_file,
            current_user.id,
            file_data,
            file_name,
            content_type,
            folder
        )
        
        if not cloudfront_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        logger.info(f"Uploaded audio file for user {current_user.id} to {folder}: {cloudfront_url}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "url": cloudfront_url,
                "type": "audio"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/upload/image-to-image")
async def upload_image_to_image_file(
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Upload an image file for image-to-image.
    Returns CloudFront URL for the uploaded file.
    """
    try:
        # Read file data
        file_data = await file.read()
        
        # Determine content type
        content_type = file.content_type or "image/jpeg"
        
        # Only images allowed for image-to-image
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        file_name = file.filename or "image.jpg"
        
        # Upload to Backblaze - run in thread executor to avoid blocking event loop
        storage_service = get_storage_service()
        cloudfront_url = await asyncio.to_thread(
            storage_service.upload_file,
            current_user.id,
            file_data,
            file_name,
            content_type,
            "image-to-image"
        )
        
        if not cloudfront_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        logger.info(f"Uploaded file for user {current_user.id} to image-to-image: {cloudfront_url}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "url": cloudfront_url,
                "type": "image"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/files")
async def list_user_files(
    folder: Optional[str] = None,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List files for the current user, optionally filtered by folder.
    Valid folder values: wan-animate, image-to-video, image-to-image
    """
    try:
        storage_service = get_storage_service()
        files = storage_service.list_user_files(
            user_id=current_user.id,
            folder=folder
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"files": files}
        )
        
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


@router.delete("/files/{file_path:path}")
async def delete_user_file(
    file_path: str,
    current_user: UserProfile = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a file for the current user.
    file_path should be relative to user folder (e.g., "wan-animate/filename.jpg")
    """
    try:
        # Security check: ensure file path belongs to current user
        if not file_path.startswith(f"{current_user.id}/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete files that don't belong to you"
            )
        
        storage_service = get_storage_service()
        success = storage_service.delete_file(
            user_id=current_user.id,
            file_path=file_path
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "File deleted successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )

